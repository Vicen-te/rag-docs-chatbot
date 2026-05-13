"""Memory-related tools the agent can invoke."""
from __future__ import annotations

from agent.memory.service import recall_semantic, store_semantic


def store_semantic_memory(user, category: str, key: str, value: str) -> dict:
    mem = store_semantic(user, category, key, value)
    return {
        "id": str(mem.id),
        "category": mem.category,
        "key": mem.key,
        "value": mem.value,
    }


def recall_semantic_memory(
    user,
    category: str | None = None,
    key: str | None = None,
) -> list[dict]:
    facts = recall_semantic(user, category=category, key=key)
    return [
        {
            "category": f.category,
            "key": f.key,
            "value": f.value,
            "confidence": f.confidence,
        }
        for f in facts
    ]


STORE_SEMANTIC_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "store_semantic_memory",
        "description": (
            "Store a durable fact about the user. UPSERT semantics: "
            "the same (category, key) overwrites the previous value."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "enum": ["preference", "fact", "skill", "goal", "context"],
                },
                "key": {"type": "string"},
                "value": {"type": "string"},
            },
            "required": ["category", "key", "value"],
        },
    },
}

RECALL_SEMANTIC_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "recall_semantic_memory",
        "description": "Retrieve stored facts about the user. Filter by category or key.",
        "parameters": {
            "type": "object",
            "properties": {
                "category": {"type": "string"},
                "key": {"type": "string"},
            },
        },
    },
}
