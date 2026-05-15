"""Compute Ragas metrics on a previous eval_run output directory.

Reads `per_question.jsonl`, builds Ragas `SingleTurnSample`s from the
question / answer / retrieved_chunks captured during eval_run, scores
them with the configured judge LLM and embeddings, writes
`ragas.jsonl` and appends a "Ragas metrics" section to `summary.md`.

The judge is selected by `settings.RAGAS_JUDGE_PROVIDER`:

* ``"ollama"`` -- uses OLLAMA_MODEL via the OpenAI-compatible client
  pointed at OLLAMA_BASE_URL. Free, local, but the same model also
  generated the answer (biased self-evaluation).
* ``"openai"`` -- uses OPENAI_API_KEY against the OpenAI API. More
  impartial and much faster; requires a paid key.
"""
from __future__ import annotations

import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


def _build_judge():
    from langchain_huggingface import HuggingFaceEmbeddings
    from langchain_openai import ChatOpenAI, OpenAIEmbeddings

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

    def handle(self, *args, **opts):
        from ragas import EvaluationDataset, SingleTurnSample, evaluate
        from ragas.embeddings import LangchainEmbeddingsWrapper
        from ragas.llms import LangchainLLMWrapper
        from ragas.metrics import (
            answer_relevancy,
            context_precision,
            context_recall,
            faithfulness,
        )

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
            answer = r.get("answer") or ""
            if not answer or answer.startswith("<error"):
                skipped.append((r["id"], "no answer"))
                continue
            ctx = r.get("retrieved_chunks") or []
            if not ctx:
                skipped.append((r["id"], "no retrieved context"))
                continue
            must_include = r.get("must_include") or []
            reference = r.get("reference") or (
                "; ".join(must_include) if must_include else None
            )
            samples.append(SingleTurnSample(
                user_input=r["question"],
                response=answer,
                retrieved_contexts=ctx,
                reference=reference,
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

        has_ref = any(s.reference for s in samples)
        metrics = [faithfulness, answer_relevancy, context_precision]
        if has_ref:
            metrics.append(context_recall)

        ds = EvaluationDataset(samples=samples)
        self.stdout.write(
            f"scoring {len(samples)} samples with {settings.RAGAS_JUDGE_PROVIDER} "
            f"({judge_model})..."
        )
        result = evaluate(
            dataset=ds,
            metrics=metrics,
            llm=llm,
            embeddings=emb,
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
        if not has_ref:
            lines.append("")
            lines.append(
                "Note: `context_recall` requires a `reference` field in the "
                "dataset. The runner falls back to joining `must_include` "
                "tokens when present; questions without either are scored "
                "without context_recall."
            )
        lines.append("")

        summary_path = run_dir / "summary.md"
        existing = summary_path.read_text(encoding="utf-8") if summary_path.exists() else ""
        summary_path.write_text(existing + "\n".join(lines), encoding="utf-8")

        self.stdout.write(self.style.SUCCESS(f"\nwrote {ragas_path}"))
        self.stdout.write(str(summary_path))
