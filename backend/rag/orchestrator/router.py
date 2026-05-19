"""Pre-graph classification and fast routing."""
from __future__ import annotations

CONVERSATIONAL_KEYWORDS = (
    "hi", "hello", "hey", "thanks", "thank you", "bye", "goodbye",
    "who are you", "what can you do",
)

GREETING_FAST_REPLIES = {
    "hi": "Hello! How can I help you today?",
    "hello": "Hello! How can I help you today?",
    "hey": "Hi there. What can I do for you?",
    "thanks": "You're welcome.",
    "thank you": "You're welcome.",
}


def classify_task_type(message: str) -> str:
    """Cheap heuristic classifier. Returns 'conversational' or 'rag'."""
    low = message.lower().strip()
    if any(k in low for k in CONVERSATIONAL_KEYWORDS) and len(low.split()) < 8:
        return "conversational"
    return "rag"


def try_fast_route(message: str) -> str | None:
    """Return a canned reply for trivial greetings; None otherwise."""
    return GREETING_FAST_REPLIES.get(message.lower().strip())
