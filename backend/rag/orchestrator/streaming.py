"""SSE event helpers for streaming chat responses."""
from __future__ import annotations

import json


STEP_LABELS: dict[str, tuple[str, str]] = {
    "intake": ("thinking", "Preparing context"),
    "classify": ("thinking", "Classifying request"),
    "conversational": ("writing", "Composing reply"),
    "retrieve": ("searching", "Searching knowledge base"),
    "synthesise": ("writing", "Drafting answer"),
    "verify": ("checking", "Verifying answer"),
}


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


def sse_step(node: str, diff: dict, state: dict) -> str:
    stage, label = STEP_LABELS.get(node, ("thinking", node))
    detail: str | None = None

    if node == "synthesise" and state.get("verify_iterations", 0) > 0:
        label = "Revising answer"
    if node == "classify":
        task = state.get("task_type")
        if task:
            detail = task
    elif node == "retrieve":
        n = len(state.get("context") or [])
        detail = f"{n} document" if n == 1 else f"{n} documents"
    elif node == "verify":
        iterations = state.get("verify_iterations") or 0
        reason = (state.get("verify_reason") or "").strip()
        if "final" in diff:
            detail = f"accepted after {iterations}" if iterations else "accepted"
        elif reason:
            short = reason if len(reason) <= 80 else reason[:77] + "..."
            detail = f"retry {iterations}: {short}"

    payload: dict = {"node": node, "stage": stage, "label": label}
    if detail:
        payload["detail"] = detail
    return format_sse_event("step", payload)
