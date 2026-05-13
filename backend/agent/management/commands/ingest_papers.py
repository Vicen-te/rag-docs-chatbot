"""Walk a directory and ingest every supported file into the KB."""
from __future__ import annotations

from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import IntegrityError

from agent.kb.ingestion import ingest_document

SUPPORTED_SUFFIXES = {".pdf", ".docx", ".html", ".htm", ".txt", ".md"}


class Command(BaseCommand):
    help = "Ingest every supported file under a directory."

    def add_arguments(self, parser):
        parser.add_argument("path", type=str, help="Root directory to walk.")
        parser.add_argument(
            "--quiet-duplicates",
            action="store_true",
            help="Do not log files that were already ingested.",
        )

    def handle(self, *args, **options):
        root = Path(options["path"]).resolve()
        if not root.exists():
            self.stderr.write(self.style.ERROR(f"path does not exist: {root}"))
            return

        files = sorted(
            p for p in root.rglob("*")
            if p.is_file() and p.suffix.lower() in SUPPORTED_SUFFIXES
        )
        if not files:
            self.stderr.write(
                self.style.WARNING(f"no supported files under {root}")
            )
            return

        ingested = 0
        duplicates = 0
        failed = 0
        for f in files:
            try:
                doc = ingest_document(f)
                ingested += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"ingested {f.name} ({doc.num_chunks} chunks)"
                    )
                )
            except IntegrityError:
                duplicates += 1
                if not options["quiet_duplicates"]:
                    self.stdout.write(
                        self.style.WARNING(f"duplicate (skipped): {f.name}")
                    )
            except Exception as exc:
                failed += 1
                self.stderr.write(
                    self.style.ERROR(f"failed {f.name}: {exc}")
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"done. ingested={ingested} duplicates={duplicates} failed={failed}"
            )
        )
