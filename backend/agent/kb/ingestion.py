"""Document ingestion: parse, split parent/child, dedup by content hash."""
from __future__ import annotations

import hashlib
from pathlib import Path

from bs4 import BeautifulSoup
from django.conf import settings
from django.db import transaction
from docx import Document as DocxDocument
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader

from agent.memory.embeddings import embed_texts
from agent.models import KBChunk, KBDocument


def compute_file_hash(path: Path) -> str:
    sha = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(65536), b""):
            sha.update(block)
    return sha.hexdigest()


def parse_file(path: Path) -> tuple[str, str]:
    """Return (text, mime_type) for PDF / DOCX / HTML / TXT / MD."""
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        reader = PdfReader(str(path))
        text = "\n\n".join(page.extract_text() or "" for page in reader.pages)
        return text, "application/pdf"
    if suffix == ".docx":
        doc = DocxDocument(str(path))
        text = "\n\n".join(p.text for p in doc.paragraphs)
        return (
            text,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    if suffix in {".html", ".htm"}:
        html = path.read_text(encoding="utf-8", errors="ignore")
        soup = BeautifulSoup(html, "html.parser")
        return soup.get_text("\n"), "text/html"
    if suffix in {".txt", ".md"}:
        return path.read_text(encoding="utf-8", errors="ignore"), "text/plain"
    raise ValueError(f"Unsupported file type: {suffix}")


def chunk_text(text: str) -> list[tuple[str, list[str]]]:
    """Split text into parents, each with their child sub-chunks."""
    parent_splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.KB_PARENT_CHUNK_SIZE,
        chunk_overlap=settings.KB_CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " "],
    )
    child_splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.KB_CHILD_CHUNK_SIZE,
        chunk_overlap=settings.KB_CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " "],
    )
    parents = parent_splitter.split_text(text)
    return [(p, child_splitter.split_text(p)) for p in parents]


@transaction.atomic
def ingest_document(path: Path | str, title: str | None = None) -> KBDocument:
    """Hash, parse, chunk, embed children, persist.

    Raises django.db.IntegrityError if the file is already present
    (deduplicated by SHA-256 of its bytes).
    """
    path = Path(path)
    content_hash = compute_file_hash(path)
    text, mime_type = parse_file(path)
    chunked = chunk_text(text)

    doc = KBDocument.objects.create(
        title=title or path.stem,
        source_path=str(path),
        content_hash=content_hash,
        mime_type=mime_type,
        num_chunks=sum(1 + len(children) for _, children in chunked),
    )

    chunk_index = 0
    children_to_embed: list[KBChunk] = []
    for parent_text, child_texts in chunked:
        parent = KBChunk.objects.create(
            document=doc,
            parent_chunk=None,
            chunk_type=KBChunk.ChunkType.PARENT,
            chunk_index=chunk_index,
            content=parent_text,
            token_count=len(parent_text.split()),
        )
        chunk_index += 1
        for child_text in child_texts:
            children_to_embed.append(
                KBChunk(
                    document=doc,
                    parent_chunk=parent,
                    chunk_type=KBChunk.ChunkType.CHILD,
                    chunk_index=chunk_index,
                    content=child_text,
                    token_count=len(child_text.split()),
                )
            )
            chunk_index += 1

    if children_to_embed:
        vectors = embed_texts([c.content for c in children_to_embed])
        for child, vec in zip(children_to_embed, vectors):
            child.embedding = vec
        KBChunk.objects.bulk_create(children_to_embed)

    return doc
