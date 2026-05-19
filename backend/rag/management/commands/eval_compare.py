"""Compare two eval_run output directories.

Reads `per_question.jsonl` from each side, joins on question id, and
emits an aggregate diff (overall and per category) plus a per-question
table. Writes the markdown to stdout and optionally to a file via
`--out`. Designed to drop straight into the README.
"""
from __future__ import annotations

import json
import statistics
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError


def _load_records(run_dir: Path) -> dict[str, dict]:
    path = run_dir / "per_question.jsonl"
    if not path.exists():
        raise CommandError(f"missing per_question.jsonl in {run_dir}")
    out: dict[str, dict] = {}
    with path.open(encoding="utf-8") as fh:
        for ln in fh:
            ln = ln.strip()
            if not ln:
                continue
            rec = json.loads(ln)
            out[rec["id"]] = rec
    if not out:
        raise CommandError(f"empty per_question.jsonl in {run_dir}")
    return out


def _mean(values: list[float]) -> float:
    return statistics.fmean(values) if values else 0.0


def _label(run_dir: Path, records: dict[str, dict]) -> str:
    any_rec = next(iter(records.values()))
    mode = any_rec.get("retrieval_mode", "?")
    return f"{run_dir.name} ({mode})"


def _delta_cell(a: float, b: float) -> str:
    diff = b - a
    sign = "+" if diff >= 0 else ""
    return f"{a:.0%} -> {b:.0%} ({sign}{diff*100:.1f}pp)"


def _bool_delta_cell(a: bool | None, b: bool | None) -> str:
    def fmt(v):
        if v is None:
            return "-"
        return "Y" if v else "N"
    return f"{fmt(a)} -> {fmt(b)}"


class Command(BaseCommand):
    help = "Diff two eval_run result directories side by side."

    def add_arguments(self, parser):
        parser.add_argument("run_a", type=str, help="First run directory")
        parser.add_argument("run_b", type=str, help="Second run directory")
        parser.add_argument(
            "--out", type=str, default="",
            help="Write the markdown to this file as well as stdout.",
        )

    def handle(self, *args, **opts):
        dir_a = Path(opts["run_a"])
        dir_b = Path(opts["run_b"])
        recs_a = _load_records(dir_a)
        recs_b = _load_records(dir_b)

        shared = sorted(set(recs_a).intersection(recs_b))
        if not shared:
            raise CommandError("the two runs share no question ids")

        only_a = sorted(set(recs_a) - set(recs_b))
        only_b = sorted(set(recs_b) - set(recs_a))

        label_a = _label(dir_a, recs_a)
        label_b = _label(dir_b, recs_b)

        out: list[str] = []
        out.append(f"# Compare: {label_a} vs {label_b}")
        out.append("")
        out.append(f"- questions compared: {len(shared)}")
        if only_a:
            out.append(f"- only in A: {', '.join(only_a)}")
        if only_b:
            out.append(f"- only in B: {', '.join(only_b)}")
        out.append("")

        out.append("## Overall")
        out.append("")
        out.append("| metric | A | B | delta |")
        out.append("|---|---|---|---|")
        for metric in (
            "retrieval_hit",
            "retrieval_recall",
            "keyword_hit",
            "citation_present",
        ):
            a_vals = [
                float(recs_a[i][metric]) for i in shared
                if recs_a[i].get(metric) is not None
            ]
            b_vals = [
                float(recs_b[i][metric]) for i in shared
                if recs_b[i].get(metric) is not None
            ]
            if not a_vals and not b_vals:
                continue
            ma = _mean(a_vals)
            mb = _mean(b_vals)
            diff = mb - ma
            sign = "+" if diff >= 0 else ""
            out.append(
                f"| {metric} | {ma:.2%} | {mb:.2%} | "
                f"{sign}{diff*100:.1f}pp |"
            )
        out.append("")

        out.append("## By category")
        out.append("")
        out.append("| category | n | hit@k A->B | recall A->B | kw hit A->B |")
        out.append("|---|---|---|---|---|")
        cats: dict[str, list[str]] = {}
        for qid in shared:
            cats.setdefault(recs_a[qid]["category"], []).append(qid)
        for cat in [
            "single_hop", "multi_hop", "detail_tech", "synthesis", "negative",
        ]:
            ids = cats.get(cat, [])
            if not ids:
                continue
            hit_a = _mean([float(recs_a[i]["retrieval_hit"]) for i in ids])
            hit_b = _mean([float(recs_b[i]["retrieval_hit"]) for i in ids])
            rec_a = _mean([float(recs_a[i]["retrieval_recall"]) for i in ids])
            rec_b = _mean([float(recs_b[i]["retrieval_recall"]) for i in ids])
            kw_a_vals = [
                float(recs_a[i]["keyword_hit"]) for i in ids
                if recs_a[i].get("keyword_hit") is not None
            ]
            kw_b_vals = [
                float(recs_b[i]["keyword_hit"]) for i in ids
                if recs_b[i].get("keyword_hit") is not None
            ]
            kw_cell = (
                _delta_cell(_mean(kw_a_vals), _mean(kw_b_vals))
                if kw_a_vals or kw_b_vals else "-"
            )
            out.append(
                f"| {cat} | {len(ids)} | "
                f"{_delta_cell(hit_a, hit_b)} | "
                f"{_delta_cell(rec_a, rec_b)} | "
                f"{kw_cell} |"
            )
        out.append("")

        out.append("## Per question")
        out.append("")
        out.append("| id | cat | hit A->B | recall A->B | kw A->B |")
        out.append("|---|---|---|---|---|")
        for qid in shared:
            ra = recs_a[qid]
            rb = recs_b[qid]
            out.append(
                f"| {qid} | {ra['category']} | "
                f"{_bool_delta_cell(ra['retrieval_hit'], rb['retrieval_hit'])} | "
                f"{ra['retrieval_recall']:.0%} -> {rb['retrieval_recall']:.0%} | "
                f"{_bool_delta_cell(ra.get('keyword_hit'), rb.get('keyword_hit'))} |"
            )
        out.append("")

        text = "\n".join(out)
        self.stdout.write(text)
        if opts["out"]:
            Path(opts["out"]).write_text(text, encoding="utf-8")
            self.stdout.write(self.style.SUCCESS(f"\nwrote: {opts['out']}"))
