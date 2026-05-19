"""Compute Ragas metrics on a previous eval_run output directory.

Reads `per_question.jsonl`, builds Ragas `SingleTurnSample`s from the
question / answer / retrieved_chunks captured during eval_run, scores
them with the configured judge LLM and embeddings, writes
`ragas.jsonl` and appends a "Ragas metrics" section to `summary.md`.

The judge is selected by `settings.RAGAS_JUDGE_PROVIDER`:

* ``"ollama"`` -- uses OLLAMA_MODEL via the OpenAI-compatible client
  pointed at OLLAMA_BASE_URL. Free, local, but a weak structured-
  output judge (frequent parser failures -> NaN metrics).
* ``"openai"`` -- uses OPENAI_API_KEY against the OpenAI API. Fast
  and reliable; requires a paid key.
* ``"anthropic"`` -- uses ANTHROPIC_API_KEY against the Anthropic
  API (default model claude-haiku-4-5). Fast and reliable;
  embeddings stay local since Anthropic has no embedding API.
"""
from __future__ import annotations

import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from langchain_anthropic import ChatAnthropic
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from ragas import EvaluationDataset, RunConfig, SingleTurnSample, evaluate
from ragas.embeddings import LangchainEmbeddingsWrapper
from ragas.llms import LangchainLLMWrapper
from ragas.metrics import (
    LLMContextPrecisionWithoutReference,
    answer_relevancy,
    faithfulness,
)


def _build_judge():
    if settings.RAGAS_JUDGE_PROVIDER == "openai":
        if not settings.OPENAI_API_KEY:
            raise CommandError(
                "RAGAS_JUDGE_PROVIDER=openai but OPENAI_API_KEY is empty"
            )
        model = settings.RAGAS_JUDGE_MODEL or "gpt-4o-mini"
        llm = ChatOpenAI(
            model=model,
            api_key=settings.OPENAI_API_KEY,
            temperature=0,
        )
        emb = OpenAIEmbeddings(
            model="text-embedding-3-small",
            api_key=settings.OPENAI_API_KEY,
        )
        return llm, emb, model

    if settings.RAGAS_JUDGE_PROVIDER == "anthropic":
        if not settings.ANTHROPIC_API_KEY:
            raise CommandError(
                "RAGAS_JUDGE_PROVIDER=anthropic but ANTHROPIC_API_KEY is empty"
            )
        model = settings.RAGAS_JUDGE_MODEL or "claude-haiku-4-5"
        llm = ChatAnthropic(
            model=model,
            api_key=settings.ANTHROPIC_API_KEY,
            temperature=0,
        )
        # Anthropic has no embedding API; embeddings stay local.
        emb = HuggingFaceEmbeddings(model_name=settings.EMBEDDING_MODEL)
        return llm, emb, model

    model = settings.RAGAS_JUDGE_MODEL or settings.OLLAMA_MODEL
    llm = ChatOpenAI(
        model=model,
        api_key=settings.OLLAMA_API_KEY or "ollama",
        base_url=settings.OLLAMA_BASE_URL,
        temperature=0,
    )
    emb = HuggingFaceEmbeddings(model_name=settings.EMBEDDING_MODEL)
    return llm, emb, model


class Command(BaseCommand):
    help = "Compute Ragas metrics on a previous eval_run output."

    def add_arguments(self, parser):
        parser.add_argument("run_dir", type=str)
        parser.add_argument(
            "--timeout", type=int, default=0,
            help=(
                "Per-job timeout (s). Default: 600 for the ollama judge "
                "(slow, serialised), 180 for cloud judges."
            ),
        )
        parser.add_argument(
            "--workers", type=int, default=0,
            help=(
                "Concurrent Ragas jobs. Default: 1 for ollama (it "
                "processes one request at a time, so concurrency only "
                "makes queued jobs time out), 8 for cloud judges."
            ),
        )

    def handle(self, *args, **opts):
        run_dir = Path(opts["run_dir"])
        per_q = run_dir / "per_question.jsonl"
        if not per_q.exists():
            raise CommandError(f"missing {per_q}")

        records: list[dict] = []
        with per_q.open(encoding="utf-8") as fh:
            for ln in fh:
                ln = ln.strip()
                if not ln:
                    continue
                records.append(json.loads(ln))

        samples: list[SingleTurnSample] = []
        sample_ids: list[str] = []
        skipped: list[tuple[str, str]] = []
        for r in records:
            # Negative questions are abstention tests, not RAG answers;
            # faithfulness / relevancy / context metrics are undefined
            # for an "I don't know" and have no reference, so exclude
            # them from the Ragas set.
            if r.get("category") == "negative":
                skipped.append((r["id"], "negative (not a RAG answer)"))
                continue
            answer = r.get("answer") or ""
            if not answer or answer.startswith("<error"):
                skipped.append((r["id"], "no answer"))
                continue
            ctx = r.get("retrieved_chunks") or []
            if not ctx:
                skipped.append((r["id"], "no retrieved context"))
                continue
            samples.append(SingleTurnSample(
                user_input=r["question"],
                response=answer,
                retrieved_contexts=ctx,
            ))
            sample_ids.append(r["id"])

        if not samples:
            raise CommandError(
                "no evaluable records (need answer + retrieved_chunks). "
                "Did you re-run eval_run after adding retrieved_chunks support?"
            )

        llm_raw, emb_raw, judge_model = _build_judge()
        llm = LangchainLLMWrapper(llm_raw)
        emb = LangchainEmbeddingsWrapper(emb_raw)

        # The dataset has no gold answers, so the reference-based
        # context_precision / context_recall mis-attribute (Ragas would
        # score retrieval against a fabricated reference). Precision is
        # the reference-free variant, which anchors on the generated
        # answer instead; recall is measured deterministically by
        # eval_run (was the correct chunk retrieved), not by Ragas.
        metrics = [
            faithfulness,
            answer_relevancy,
            LLMContextPrecisionWithoutReference(),
        ]

        is_cloud = settings.RAGAS_JUDGE_PROVIDER in ("openai", "anthropic")
        timeout = opts["timeout"] or (180 if is_cloud else 600)
        workers = opts["workers"] or (8 if is_cloud else 1)
        run_config = RunConfig(timeout=timeout, max_workers=workers)

        ds = EvaluationDataset(samples=samples)
        self.stdout.write(
            f"scoring {len(samples)} samples with {settings.RAGAS_JUDGE_PROVIDER} "
            f"({judge_model}); timeout={timeout}s workers={workers}..."
        )
        result = evaluate(
            dataset=ds,
            metrics=metrics,
            llm=llm,
            embeddings=emb,
            run_config=run_config,
            raise_exceptions=False,
            show_progress=True,
        )

        df = result.to_pandas()
        ragas_path = run_dir / "ragas.jsonl"
        metric_names = [m.name for m in metrics]
        with ragas_path.open("w", encoding="utf-8") as out:
            for i, qid in enumerate(sample_ids):
                rec: dict = {"id": qid}
                for name in metric_names:
                    if name in df.columns:
                        val = df[name].iloc[i]
                        try:
                            rec[name] = float(val)
                        except (TypeError, ValueError):
                            rec[name] = None
                    else:
                        rec[name] = None
                out.write(json.dumps(rec, ensure_ascii=False) + "\n")

        lines: list[str] = ["", "## Ragas metrics", ""]
        lines.append(f"- judge: {settings.RAGAS_JUDGE_PROVIDER} ({judge_model})")
        lines.append(f"- samples scored: {len(samples)}")
        if skipped:
            lines.append(f"- skipped: {len(skipped)} ({', '.join(qid for qid, _ in skipped)})")
        lines.append("")
        lines.append("| metric | mean |")
        lines.append("|---|---|")
        for name in metric_names:
            if name not in df.columns:
                continue
            col = df[name].dropna()
            mean = float(col.mean()) if not col.empty else float("nan")
            lines.append(f"| {name} | {mean:.3f} |")
        lines.append("")
        lines.append(
            "Note: context precision is the reference-free Ragas metric "
            "(`llm_context_precision_without_reference`). The dataset has "
            "no gold answers, so the reference-based context_precision / "
            "context_recall would mis-attribute and are not computed. "
            "Retrieval recall is measured deterministically by eval_run "
            "(was the correct chunk retrieved), not by Ragas."
        )
        lines.append("")

        summary_path = run_dir / "summary.md"
        existing = (
            summary_path.read_text(encoding="utf-8")
            if summary_path.exists() else ""
        )
        # Drop a previous "## Ragas metrics" section so re-running is
        # idempotent instead of stacking sections.
        marker = "\n## Ragas metrics"
        idx = existing.find(marker)
        if idx != -1:
            existing = existing[:idx].rstrip() + "\n"
        summary_path.write_text(
            existing.rstrip() + "\n" + "\n".join(lines), encoding="utf-8",
        )

        self.stdout.write(self.style.SUCCESS(f"\nwrote {ragas_path}"))
        self.stdout.write(str(summary_path))
