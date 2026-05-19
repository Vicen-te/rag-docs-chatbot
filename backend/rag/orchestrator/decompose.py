"""Split a multi-part question into focused retrieval sub-queries.

Multi-hop questions blend several topics; a single query embedding
averages them and buries the weaker topic's documents. Retrieving
each sub-question separately surfaces every needed document.
"""
from __future__ import annotations

import json

from rag.orchestrator import prompts
from rag.orchestrator.llm_client import chat_completion

_MAX_SUBQUERIES = 3


def _extract_json_array(text: str) -> str:
    start = text.find("[")
    end = text.rfind("]")
    if start != -1 and end > start:
        return text[start : end + 1]
    return text


def decompose_query(question: str) -> list[str]:
    """Return 1..3 self-contained sub-questions. Falls back to the
    original question on any failure -- never raises."""
    messages = [
        {"role": "system", "content": prompts.DECOMPOSE},
        {"role": "user", "content": question},
    ]
    try:
        resp = chat_completion(messages=messages, temperature=0.0)
        content = resp["choices"][0]["message"]["content"]
        parsed = json.loads(_extract_json_array(content))
        subs = [s.strip() for s in parsed if isinstance(s, str) and s.strip()]
    except Exception:
        subs = []
    if not subs:
        return [question]
    return subs[:_MAX_SUBQUERIES]
