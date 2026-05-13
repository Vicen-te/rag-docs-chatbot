"""Single source of truth for tool callables and their LLM schemas."""
from __future__ import annotations

from agent.tools.kb_tools import KB_SEARCH_TOOL_SCHEMA, kb_search
from agent.tools.memory_tools import (
    RECALL_SEMANTIC_TOOL_SCHEMA,
    STORE_SEMANTIC_TOOL_SCHEMA,
    recall_semantic_memory,
    store_semantic_memory,
)

TOOL_FUNCTIONS = {
    "kb_search": kb_search,
    "store_semantic_memory": store_semantic_memory,
    "recall_semantic_memory": recall_semantic_memory,
}

TOOL_SCHEMAS = [
    KB_SEARCH_TOOL_SCHEMA,
    STORE_SEMANTIC_TOOL_SCHEMA,
    RECALL_SEMANTIC_TOOL_SCHEMA,
]
