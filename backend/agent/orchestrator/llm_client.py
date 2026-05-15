"""Chat-completion wrapper.

Dispatches on `settings.LLM_PROVIDER`:

* ``"ollama"`` -- POST to Ollama's native ``/api/chat``. This is the
  only path that reliably forwards ``options.num_ctx`` to the model.
* ``"openai"`` -- OpenAI SDK against ``OLLAMA_BASE_URL`` (any
  OpenAI-compatible endpoint).

Both paths return an OpenAI-shaped dict so callers in
``agent/orchestrator/graph.py`` are provider-agnostic.
"""
from __future__ import annotations

import json
from threading import Lock
from typing import Iterable

import requests
from django.conf import settings
from openai import OpenAI

_openai_client: OpenAI | None = None
_lock = Lock()


def _get_openai_client() -> OpenAI:
    global _openai_client
    if _openai_client is None:
        with _lock:
            if _openai_client is None:
                _openai_client = OpenAI(
                    base_url=settings.OLLAMA_BASE_URL,
                    api_key=settings.OLLAMA_API_KEY,
                )
    return _openai_client


def _ollama_native_base() -> str:
    base = settings.OLLAMA_BASE_URL.rstrip("/")
    if base.endswith("/v1"):
        base = base[: -len("/v1")]
    return base


def _ollama_options(temperature: float) -> dict:
    return {"num_ctx": settings.OLLAMA_NUM_CTX, "temperature": temperature}


def _to_openai_message(msg: dict) -> dict:
    out: dict = {
        "role": msg.get("role", "assistant"),
        "content": msg.get("content", ""),
    }
    raw_calls = msg.get("tool_calls")
    if raw_calls:
        calls = []
        for i, c in enumerate(raw_calls):
            fn = c.get("function", {})
            args = fn.get("arguments", {})
            if not isinstance(args, str):
                args = json.dumps(args, ensure_ascii=False)
            calls.append({
                "id": c.get("id", f"call_{i}"),
                "type": "function",
                "function": {"name": fn.get("name", ""), "arguments": args},
            })
        out["tool_calls"] = calls
    return out


def _ollama_native_chat(
    messages: list[dict],
    model: str,
    tools: list[dict] | None,
    temperature: float,
) -> dict:
    payload: dict = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": _ollama_options(temperature),
    }
    if tools:
        payload["tools"] = tools
    r = requests.post(
        f"{_ollama_native_base()}/api/chat", json=payload, timeout=600,
    )
    r.raise_for_status()
    data = r.json()
    return {
        "model": data.get("model", model),
        "choices": [{
            "index": 0,
            "message": _to_openai_message(data.get("message", {})),
            "finish_reason": data.get("done_reason", "stop"),
        }],
    }


def _openai_chat(
    messages: list[dict],
    model: str,
    tools: list[dict] | None,
    temperature: float,
) -> dict:
    response = _get_openai_client().chat.completions.create(
        model=model,
        messages=messages,
        tools=tools,
        temperature=temperature,
        extra_body={"options": {"num_ctx": settings.OLLAMA_NUM_CTX}},
    )
    return response.model_dump()


def chat_completion(
    messages: list[dict],
    model: str | None = None,
    tools: list[dict] | None = None,
    temperature: float = 0.2,
) -> dict:
    model = model or settings.OLLAMA_MODEL
    if settings.LLM_PROVIDER == "ollama":
        return _ollama_native_chat(messages, model, tools, temperature)
    return _openai_chat(messages, model, tools, temperature)


def _ollama_native_stream(
    messages: list[dict],
    model: str,
    temperature: float,
) -> Iterable[str]:
    payload = {
        "model": model,
        "messages": messages,
        "stream": True,
        "options": _ollama_options(temperature),
    }
    with requests.post(
        f"{_ollama_native_base()}/api/chat",
        json=payload,
        timeout=600,
        stream=True,
    ) as r:
        r.raise_for_status()
        for line in r.iter_lines(decode_unicode=True):
            if not line:
                continue
            try:
                chunk = json.loads(line)
            except json.JSONDecodeError:
                continue
            delta = chunk.get("message", {}).get("content")
            if delta:
                yield delta
            if chunk.get("done"):
                break


def _openai_stream(
    messages: list[dict],
    model: str,
    temperature: float,
) -> Iterable[str]:
    stream = _get_openai_client().chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        stream=True,
        extra_body={"options": {"num_ctx": settings.OLLAMA_NUM_CTX}},
    )
    for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta


def chat_completion_stream(
    messages: list[dict],
    model: str | None = None,
    temperature: float = 0.2,
) -> Iterable[str]:
    model = model or settings.OLLAMA_MODEL
    if settings.LLM_PROVIDER == "ollama":
        return _ollama_native_stream(messages, model, temperature)
    return _openai_stream(messages, model, temperature)
