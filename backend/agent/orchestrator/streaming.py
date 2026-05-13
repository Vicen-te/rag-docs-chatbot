"""SSE event helpers for streaming chat responses."""
from __future__ import annotations

import json


def format_sse_event(event: str, data: dict | str) -> str:
    if not isinstance(data, str):
        data = json.dumps(data)
    return f"event: {event}\ndata: {data}\n\n"


def sse_token(token: str) -> str:
    return format_sse_event("token", token)


def sse_done(payload: dict) -> str:
    return format_sse_event("done", payload)


def sse_error(message: str) -> str:
    return format_sse_event("error", {"error": message})
