"""Embeddings helper backed by sentence-transformers.

Singleton model loaded once per process. Vectors are L2-normalised
so a dot product equals cosine similarity.
"""
from __future__ import annotations

from threading import Lock
from typing import Iterable

from django.conf import settings
from sentence_transformers import SentenceTransformer

# BGE expects an instruction in front of the query for asymmetric
# retrieval; passages go in unmodified.
_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "

_model: SentenceTransformer | None = None
_lock = Lock()


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        with _lock:
            if _model is None:
                _model = SentenceTransformer(settings.EMBEDDING_MODEL)
    return _model


def preload_model() -> None:
    """Force the model to load now rather than on the first call."""
    _get_model()


def embed_query(text: str) -> list[float]:
    """Embed a single search query as a unit vector."""
    vec = _get_model().encode(_QUERY_PREFIX + text, normalize_embeddings=True)
    return vec.tolist()


def embed_texts(texts: Iterable[str]) -> list[list[float]]:
    """Embed a batch of passages."""
    matrix = _get_model().encode(
        list(texts), normalize_embeddings=True, batch_size=32
    )
    return [row.tolist() for row in matrix]
