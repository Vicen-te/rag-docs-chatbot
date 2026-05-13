"""Retrieval over KB chunks: semantic, lexical, hybrid (RRF)."""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Literal

from django.conf import settings
from django.db import connection, transaction

from agent.memory.embeddings import embed_query

Mode = Literal["semantic", "lexical", "hybrid"]


@dataclass
class SearchHit:
    chunk_id: str
    document_id: str
    content: str
    score: float
    parent_id: str | None
    chunk_type: str


def hybrid_search(
    query: str,
    mode: Mode = "hybrid",
    top_k: int = 10,
) -> list[SearchHit]:
    if mode == "semantic":
        return _semantic_search(query, top_k)
    if mode == "lexical":
        return _lexical_search(query, top_k)
    sem = _semantic_search(query, top_k * 2)
    lex = _lexical_search(query, top_k * 2)
    return _reciprocal_rank_fusion([sem, lex], top_k)


def _semantic_search(query: str, top_k: int) -> list[SearchHit]:
    qvec = embed_query(query)
    # Savepoint so a missing pgvector extension does not poison the
    # surrounding transaction.
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id::text, document_id::text, content,
                       (embedding <=> %s::vector) AS distance,
                       parent_chunk_id::text, chunk_type
                FROM agent_kbchunk
                WHERE chunk_type = 'child' AND embedding IS NOT NULL
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,
                [qvec, qvec, top_k],
            )
            rows = cursor.fetchall()
    return [
        SearchHit(
            chunk_id=r[0],
            document_id=r[1],
            content=r[2],
            score=1.0 - float(r[3]),
            parent_id=r[4],
            chunk_type=r[5],
        )
        for r in rows
    ]


def _lexical_search(query: str, top_k: int) -> list[SearchHit]:
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id::text, document_id::text, content,
                       similarity(content, %s) AS score,
                       parent_chunk_id::text, chunk_type
                FROM agent_kbchunk
                WHERE chunk_type = 'child' AND content %% %s
                ORDER BY score DESC
                LIMIT %s
                """,
                [query, query, top_k],
            )
            rows = cursor.fetchall()
    return [
        SearchHit(
            chunk_id=r[0],
            document_id=r[1],
            content=r[2],
            score=float(r[3]),
            parent_id=r[4],
            chunk_type=r[5],
        )
        for r in rows
    ]


def _reciprocal_rank_fusion(
    rankings: list[list[SearchHit]],
    top_k: int,
) -> list[SearchHit]:
    scores: dict[str, float] = {}
    hits_by_id: dict[str, SearchHit] = {}
    weights = [settings.KB_SEMANTIC_WEIGHT, settings.KB_LEXICAL_WEIGHT]
    for ranking, weight in zip(rankings, weights):
        for rank, hit in enumerate(ranking):
            scores[hit.chunk_id] = (
                scores.get(hit.chunk_id, 0.0)
                + weight / (settings.KB_RRF_K + rank + 1)
            )
            hits_by_id.setdefault(hit.chunk_id, hit)
    ordered = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:top_k]
    return [replace(hits_by_id[cid], score=score) for cid, score in ordered]
