"""Retrieval over KB chunks: semantic, lexical, hybrid (RRF)."""
from __future__ import annotations

import os
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
    document_name: str
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
                SELECT c.id::text, c.document_id::text,
                       d.source_path, d.title, c.content,
                       (c.embedding <=> %s::vector) AS distance,
                       c.parent_chunk_id::text, c.chunk_type
                FROM agent_kbchunk c
                JOIN agent_kbdocument d ON d.id = c.document_id
                WHERE c.chunk_type = 'child' AND c.embedding IS NOT NULL
                ORDER BY c.embedding <=> %s::vector
                LIMIT %s
                """,
                [qvec, qvec, top_k],
            )
            rows = cursor.fetchall()
    return [
        SearchHit(
            chunk_id=r[0],
            document_id=r[1],
            document_name=os.path.basename(r[2]) or r[3] or r[1],
            content=r[4],
            score=1.0 - float(r[5]),
            parent_id=r[6],
            chunk_type=r[7],
        )
        for r in rows
    ]


def _lexical_search(query: str, top_k: int) -> list[SearchHit]:
    # pg_trgm `content % query` ranks by similarity(), which is
    # symmetric and normalised over the union of both strings'
    # trigrams: a short query against a ~512-token child chunk
    # scores far below the default 0.3 threshold, so this lexical
    # channel returns almost nothing and hybrid retrieval is
    # dense-dominated on prose corpora.
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT c.id::text, c.document_id::text,
                       d.source_path, d.title, c.content,
                       similarity(c.content, %s) AS score,
                       c.parent_chunk_id::text, c.chunk_type
                FROM agent_kbchunk c
                JOIN agent_kbdocument d ON d.id = c.document_id
                WHERE c.chunk_type = 'child' AND c.content %% %s
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
            document_name=os.path.basename(r[2]) or r[3] or r[1],
            content=r[4],
            score=float(r[5]),
            parent_id=r[6],
            chunk_type=r[7],
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
