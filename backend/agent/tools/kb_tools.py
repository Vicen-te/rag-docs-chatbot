"""KB-related tools the agent can invoke."""
from __future__ import annotations

from agent.kb.search import hybrid_search


def kb_search(query: str, top_k: int = 5, mode: str = "hybrid") -> list[dict]:
    """Search the knowledge base; return a list of chunk dicts."""
    hits = hybrid_search(query=query, mode=mode, top_k=top_k)
    return [
        {
            "chunk_id": h.chunk_id,
            "document_id": h.document_id,
            "content": h.content,
            "score": h.score,
            "parent_id": h.parent_id,
            "chunk_type": h.chunk_type,
        }
        for h in hits
    ]


KB_SEARCH_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "kb_search",
        "description": (
            "Search the knowledge base for relevant passages. "
            "Returns a list of chunk objects with content and similarity score."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The search query."},
                "top_k": {
                    "type": "integer",
                    "description": "Maximum number of hits.",
                    "default": 5,
                },
                "mode": {
                    "type": "string",
                    "enum": ["semantic", "lexical", "hybrid"],
                    "default": "hybrid",
                },
            },
            "required": ["query"],
        },
    },
}
