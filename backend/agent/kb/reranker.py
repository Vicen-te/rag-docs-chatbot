"""Cross-encoder reranker over an initial candidate list."""
from __future__ import annotations

from dataclasses import replace
from threading import Lock

from django.conf import settings
from sentence_transformers import CrossEncoder

from agent.kb.search import SearchHit

_model: CrossEncoder | None = None
_lock = Lock()


def _get_model() -> CrossEncoder:
    global _model
    if _model is None:
        with _lock:
            if _model is None:
                _model = CrossEncoder(settings.KB_RERANKER_MODEL)
    return _model


def rerank(
    query: str,
    hits: list[SearchHit],
    top_k: int | None = None,
) -> list[SearchHit]:
    """Rescore hits with a cross-encoder, returning a new ordered list."""
    if not hits:
        return []
    pairs = [(query, h.content) for h in hits]
    scores = _get_model().predict(pairs)
    ranked = sorted(zip(hits, scores), key=lambda kv: float(kv[1]), reverse=True)
    out = [replace(h, score=float(s)) for h, s in ranked]
    return out[:top_k] if top_k else out
