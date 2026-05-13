"""Thin wrapper over the OpenAI client pointed at an Ollama endpoint."""
from __future__ import annotations

from typing import Iterable
from threading import Lock

from django.conf import settings
from openai import OpenAI

_client: OpenAI | None = None
_lock = Lock()


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        with _lock:
            if _client is None:
                _client = OpenAI(
                    base_url=settings.OLLAMA_BASE_URL,
                    api_key=settings.OLLAMA_API_KEY,
                )
    return _client


def chat_completion(
    messages: list[dict],
    model: str | None = None,
    tools: list[dict] | None = None,
    temperature: float = 0.2,
) -> dict:
    response = _get_client().chat.completions.create(
        model=model or settings.OLLAMA_MODEL,
        messages=messages,
        tools=tools,
        temperature=temperature,
    )
    return response.model_dump()


def chat_completion_stream(
    messages: list[dict],
    model: str | None = None,
    temperature: float = 0.2,
) -> Iterable[str]:
    stream = _get_client().chat.completions.create(
        model=model or settings.OLLAMA_MODEL,
        messages=messages,
        temperature=temperature,
        stream=True,
    )
    for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta
