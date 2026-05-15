"""Run the eval dataset against retrieval and the full agent pipeline.

Reads `eval/dataset.jsonl`, runs each question through `hybrid_search`
and `run_agent`, scores per-question metrics, and writes a markdown
summary plus a JSONL of raw per-question records under
`eval/results/<timestamp>/`.

The harness exercises the same code paths the API uses; it does not
make HTTP calls. This keeps the loop fast and skips JWT plumbing.
"""
from __future__ import annotations

import json
import os
import re
import statistics
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from agent.kb.search import hybrid_search
from agent.models import KBDocument
from agent.orchestrator.graph import run_agent

ABSTAIN_PATTERNS = [
    r"\bi (?:do not|don't|cannot|can't) (?:know|find|answer)\b",
    r"\b(?:i am|i'm) not (?:sure|certain)\b",
    r"\bno (?:information|relevant|data) (?:on|about|regarding)\b",
    r"\bnot (?:in|covered by|mentioned in|present in) the (?:provided|given|corpus|context|documents?)\b",
    r"\bthe (?:provided |given )?(?:context|documents?|corpus) (?:does not|doesn't|do not) (?:contain|mention|cover|discuss)\b",
    r"\b(?:unable|cannot) to (?:answer|find|locate)\b",
    r"\binsufficient (?:context|information|evidence)\b",
    r"\bno s[eé]\b",
    r"\bno (?:hay|tengo) informaci[oó]n\b",
    r"\bno (?:lo )?encuentro\b",
]
ABSTAIN_RE = re.compile("|".join(ABSTAIN_PATTERNS), re.IGNORECASE)

CITATION_RE = re.compile(r"\[doc:[0-9a-fA-F-]{6,}\]")


def _basename(source_path: str) -> str:
    if not source_path:
        return ""
    return os.path.basename(source_path)


def _load_document_map() -> dict[str, str]:
    """Map document_id (str) -> source filename (basename of source_path)."""
    out: dict[str, str] = {}
    for doc in KBDocument.objects.all().only("id", "source_path", "title"):
        name = _basename(doc.source_path) or f"{doc.title}.pdf"
        out[str(doc.id)] = name
    return out


def _check_must_include(answer: str, tokens: list[str]) -> bool:
    if not tokens:
        return True
    lo = answer.lower()
    return all(tok.lower() in lo for tok in tokens)


def _ensure_eval_user(username: str):
    User = get_user_model()
    user, _ = User.objects.get_or_create(
        username=username,
        defaults={"email": f"{username}@example.invalid"},
    )
    return user


def _percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    k = max(0, min(len(s) - 1, int(round((p / 100.0) * (len(s) - 1)))))
    return s[k]


def _mean(values: list[float]) -> float:
    return statistics.fmean(values) if values else 0.0


def _fmt_eta(seconds: float) -> str:
    if seconds < 0:
        seconds = 0
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h:d}h{m:02d}m{s:02d}s"
    return f"{m:02d}m{s:02d}s"


class Command(BaseCommand):
    help = "Run the eval dataset against the agent pipeline."

    def add_arguments(self, parser):
        default_dataset = Path(settings.BASE_DIR).parent / "eval" / "dataset.jsonl"
        default_out = Path(settings.BASE_DIR).parent / "eval" / "results"
        parser.add_argument("--dataset", type=str, default=str(default_dataset))
        parser.add_argument("--output-dir", type=str, default=str(default_out))
        parser.add_argument(
            "--top-k", type=int, default=settings.AGENT_TOP_K,
            help="top_k passed to hybrid_search for retrieval scoring.",
        )
        parser.add_argument(
            "--no-chat", action="store_true",
            help="Skip the chat pipeline; score retrieval only.",
        )
        parser.add_argument(
            "--limit", type=int, default=0,
            help="Only run the first N questions (0 = all).",
        )
        parser.add_argument(
            "--user", type=str, default="eval-bot",
            help="Username used for the agent pipeline.",
        )
        parser.add_argument(
            "--retrieval",
            type=str,
            choices=["hybrid", "semantic", "none"],
            default="hybrid",
            help=(
                "Retrieval mode for both the metrics call and the agent: "
                "'hybrid' (pgvector + pg_trgm via RRF), 'semantic' "
                "(embeddings only), 'none' (no retrieval -- the LLM "
                "answers from its own knowledge as a control)."
            ),
        )

    def handle(self, *args, **opts):
        dataset_path = Path(opts["dataset"])
        if not dataset_path.exists():
            raise CommandError(f"dataset not found: {dataset_path}")

        rows: list[dict] = []
        with dataset_path.open(encoding="utf-8") as fh:
            for ln in fh:
                ln = ln.strip()
                if not ln or ln.startswith("#"):
                    continue
                rows.append(json.loads(ln))
        if opts["limit"]:
            rows = rows[: opts["limit"]]
        if not rows:
            raise CommandError("dataset is empty")

        doc_map = _load_document_map()
        if not doc_map:
            self.stdout.write(self.style.WARNING(
                "no KBDocuments found -- retrieval scores will be zero. "
                "Did you run ingest_papers?"
            ))

        user = _ensure_eval_user(opts["user"])
        top_k = opts["top_k"]
        run_chat = not opts["no_chat"]
        retrieval_mode = opts["retrieval"]

        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        out_dir = Path(opts["output_dir"]) / ts
        out_dir.mkdir(parents=True, exist_ok=True)

        per_q_path = out_dir / "per_question.jsonl"
        summary_path = out_dir / "summary.md"

        records: list[dict] = []
        run_start = time.perf_counter()
        with per_q_path.open("w", encoding="utf-8") as out:
            for i, row in enumerate(rows, 1):
                q_start = time.perf_counter()
                rec = self._evaluate_one(
                    row, doc_map, user, top_k, run_chat, retrieval_mode,
                )
                took = time.perf_counter() - q_start
                records.append(rec)
                out.write(json.dumps(rec, ensure_ascii=False) + "\n")
                avg = (time.perf_counter() - run_start) / i
                eta = avg * (len(rows) - i)
                now = datetime.now().strftime("%H:%M:%S")
                self.stdout.write(
                    f"[{i}/{len(rows)} {now}] {rec['id']:8s} "
                    f"cat={rec['category']:11s} "
                    f"hit={int(rec['retrieval_hit'])} "
                    f"recall={rec['retrieval_recall']:.2f} "
                    f"kw={int(rec['keyword_hit']) if rec['keyword_hit'] is not None else '-'} "
                    f"abst={int(rec['abstained'])} "
                    f"took={took:5.1f}s eta={_fmt_eta(eta)}"
                )

        summary = self._build_summary(records, top_k, run_chat, retrieval_mode)
        summary_path.write_text(summary, encoding="utf-8")
        self.stdout.write(self.style.SUCCESS(f"\nresults: {out_dir}"))
        self.stdout.write(str(summary_path))

    def _evaluate_one(
        self,
        row: dict,
        doc_map: dict[str, str],
        user,
        top_k: int,
        run_chat: bool,
        retrieval_mode: str,
    ) -> dict:
        question = row["question"]
        expected_sources = set(row.get("expected_sources") or [])
        must_include = row.get("must_include") or []
        expected_abstain = bool(row.get("expected_abstain", False))

        t0 = time.perf_counter()
        if retrieval_mode == "none":
            hits = []
        else:
            hits = hybrid_search(question, mode=retrieval_mode, top_k=top_k)
        retrieve_ms = (time.perf_counter() - t0) * 1000.0

        retrieved_sources = []
        for h in hits:
            name = doc_map.get(h.document_id, "")
            if name and name not in retrieved_sources:
                retrieved_sources.append(name)

        if retrieval_mode == "none":
            retrieval_hit = False
            retrieval_recall = 0.0
        elif expected_sources:
            inter = expected_sources.intersection(retrieved_sources)
            retrieval_hit = bool(inter)
            retrieval_recall = len(inter) / len(expected_sources)
        else:
            retrieval_hit = True
            retrieval_recall = 1.0

        answer = ""
        chat_ms = 0.0
        retrieved_chunks: list[str] = []
        if run_chat:
            t1 = time.perf_counter()
            try:
                state = run_agent(
                    user, uuid.uuid4(), question, retrieval_mode=retrieval_mode,
                )
                answer = state.get("final", "") or ""
                retrieved_chunks = [
                    c["content"] for c in (state.get("context") or [])
                    if c.get("content")
                ]
            except Exception as exc:
                answer = f"<error: {exc}>"
            chat_ms = (time.perf_counter() - t1) * 1000.0

        if run_chat:
            keyword_hit = _check_must_include(answer, must_include) if must_include else None
            abstained = bool(ABSTAIN_RE.search(answer))
            citation_present = bool(CITATION_RE.search(answer))
        else:
            keyword_hit = None
            abstained = False
            citation_present = False

        abstain_correct = (abstained == expected_abstain) if run_chat else None

        return {
            "id": row["id"],
            "category": row["category"],
            "question": question,
            "retrieval_mode": retrieval_mode,
            "expected_sources": sorted(expected_sources),
            "retrieved_sources": retrieved_sources,
            "retrieval_hit": retrieval_hit,
            "retrieval_recall": retrieval_recall,
            "keyword_hit": keyword_hit,
            "citation_present": citation_present,
            "abstained": abstained,
            "abstain_correct": abstain_correct,
            "expected_abstain": expected_abstain,
            "answer": answer,
            "retrieved_chunks": retrieved_chunks,
            "must_include": must_include,
            "latency_retrieve_ms": round(retrieve_ms, 1),
            "latency_chat_ms": round(chat_ms, 1),
        }

    def _build_summary(
        self,
        records: list[dict],
        top_k: int,
        run_chat: bool,
        retrieval_mode: str,
    ) -> str:
        categories: dict[str, list[dict]] = {}
        for r in records:
            categories.setdefault(r["category"], []).append(r)

        lines: list[str] = []
        lines.append("# Eval results")
        lines.append("")
        lines.append(f"- generated: {datetime.now(timezone.utc).isoformat()}")
        lines.append(f"- questions: {len(records)}")
        lines.append(f"- top_k: {top_k}")
        lines.append(f"- chat: {'on' if run_chat else 'off'}")
        lines.append(f"- retrieval: {retrieval_mode}")
        lines.append(f"- model: {settings.OLLAMA_MODEL}")
        lines.append(f"- reranker: {'on' if settings.AGENT_USE_RERANKER else 'off'}")
        lines.append("")

        non_neg = [r for r in records if r["category"] != "negative"]
        neg = [r for r in records if r["category"] == "negative"]

        lines.append("## Overall")
        lines.append("")
        lines.append("| metric | value |")
        lines.append("|---|---|")
        lines.append(f"| retrieval hit@{top_k} (non-negative) | {_mean([r['retrieval_hit'] for r in non_neg]):.2%} |")
        lines.append(f"| retrieval recall (non-negative) | {_mean([r['retrieval_recall'] for r in non_neg]):.2%} |")
        if run_chat:
            kw_rows = [r for r in non_neg if r["keyword_hit"] is not None]
            lines.append(f"| answer keyword hit | {_mean([r['keyword_hit'] for r in kw_rows]):.2%} (n={len(kw_rows)}) |")
            lines.append(f"| answer cites a doc | {_mean([r['citation_present'] for r in non_neg]):.2%} |")
            if neg:
                lines.append(f"| negatives abstained correctly | {_mean([r['abstain_correct'] for r in neg]):.2%} ({sum(r['abstain_correct'] for r in neg)}/{len(neg)}) |")
            r_lat = [r["latency_retrieve_ms"] for r in records]
            c_lat = [r["latency_chat_ms"] for r in records if r["latency_chat_ms"] > 0]
            lines.append(f"| retrieval p50 / p95 (ms) | {_percentile(r_lat, 50):.0f} / {_percentile(r_lat, 95):.0f} |")
            if c_lat:
                lines.append(f"| chat p50 / p95 (ms) | {_percentile(c_lat, 50):.0f} / {_percentile(c_lat, 95):.0f} |")
        lines.append("")

        lines.append("## By category")
        lines.append("")
        header = "| category | n | hit@k | recall | "
        sep = "|---|---|---|---|"
        if run_chat:
            header += "kw hit | cites | abstain ok |"
            sep += "---|---|---|"
        else:
            header += ""
        lines.append(header)
        lines.append(sep)
        for cat in ["single_hop", "multi_hop", "detail_tech", "synthesis", "negative"]:
            rs = categories.get(cat, [])
            if not rs:
                continue
            hit = _mean([r["retrieval_hit"] for r in rs])
            rec = _mean([r["retrieval_recall"] for r in rs])
            row = f"| {cat} | {len(rs)} | {hit:.0%} | {rec:.0%} | "
            if run_chat:
                kw_rows = [r for r in rs if r["keyword_hit"] is not None]
                kw = _mean([r["keyword_hit"] for r in kw_rows]) if kw_rows else None
                cites = _mean([r["citation_present"] for r in rs])
                if cat == "negative":
                    abst = _mean([r["abstain_correct"] for r in rs])
                    row += f"- | {cites:.0%} | {abst:.0%} |"
                else:
                    kw_txt = f"{kw:.0%}" if kw is not None else "-"
                    row += f"{kw_txt} | {cites:.0%} | - |"
            lines.append(row)
        lines.append("")

        lines.append("## Per question")
        lines.append("")
        lines.append("| id | cat | hit | recall | kw | cite | abstain |")
        lines.append("|---|---|---|---|---|---|---|")
        for r in records:
            kw = "-" if r["keyword_hit"] is None else ("Y" if r["keyword_hit"] else "N")
            cite = "Y" if r["citation_present"] else "N"
            if r["category"] == "negative":
                abst = "Y" if r["abstain_correct"] else "N"
            else:
                abst = "-"
            lines.append(
                f"| {r['id']} | {r['category']} | "
                f"{'Y' if r['retrieval_hit'] else 'N'} | "
                f"{r['retrieval_recall']:.0%} | {kw} | {cite} | {abst} |"
            )
        lines.append("")
        return "\n".join(lines)
