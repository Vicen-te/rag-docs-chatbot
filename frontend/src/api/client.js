// Thin fetch wrappers for the Django API. URLs are relative so the
// Vite dev proxy can forward them to the backend.
import { parseSseChunk } from '../lib/sse.js';

const json = (token) => ({
  'Content-Type': 'application/json',
  ...(token ? { Authorization: `Bearer ${token}` } : {}),
});

export async function login(username, password) {
  const res = await fetch('/api/token/', {
    method: 'POST',
    headers: json(),
    body: JSON.stringify({ username, password }),
  });
  if (!res.ok) {
    throw new Error(`login failed (${res.status})`);
  }
  return res.json();
}

export async function listConversations(token) {
  const res = await fetch('/api/rag/conversations/', { headers: json(token) });
  if (!res.ok) throw new Error(`conversations failed (${res.status})`);
  return res.json();
}

export async function getConversation(token, id) {
  const res = await fetch(`/api/rag/conversations/${id}/`, {
    headers: json(token),
  });
  if (!res.ok) throw new Error(`conversation failed (${res.status})`);
  return res.json();
}

export async function deleteConversation(token, id) {
  const res = await fetch(`/api/rag/conversations/${id}/`, {
    method: 'DELETE',
    headers: json(token),
  });
  if (!res.ok && res.status !== 204) {
    throw new Error(`delete failed (${res.status})`);
  }
}

export async function submitFeedback(token, { message, rating, comment }) {
  const res = await fetch('/api/rag/feedback/', {
    method: 'POST',
    headers: json(token),
    body: JSON.stringify({
      message,
      rating,
      comment: comment ?? '',
      categories: [],
    }),
  });
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(`feedback failed (${res.status}): ${txt}`);
  }
  return res.json();
}

// Streams chat events as they arrive. `onEvent` is called once per
// SSE message with { event, data }. Pass `regenerateAssistantId` to
// have the backend replace that assistant message in place instead
// of creating a new user turn.
export async function streamChat({
  token,
  conversationId,
  message,
  regenerateAssistantId,
  onEvent,
  signal,
}) {
  const body = { conversation_id: conversationId };
  if (regenerateAssistantId) {
    body.regenerate_assistant_message_id = regenerateAssistantId;
  } else {
    body.message = message;
  }
  const res = await fetch('/api/rag/chat/', {
    method: 'POST',
    headers: json(token),
    body: JSON.stringify(body),
    signal,
  });
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(`chat failed (${res.status}): ${txt}`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const [events, leftover] = parseSseChunk(buffer);
    buffer = leftover;
    for (const evt of events) onEvent(evt);
  }
}
