import { useCallback, useRef, useState } from 'react';

import { streamChat } from '../api/client.js';

// A message is { id, role, content, created_at }. id is null while
// streaming until the backend reports it in the meta / done events;
// created_at is stamped locally for new messages and preserved when
// loading an existing conversation from history.

export function useChat(token) {
  const [messages, setMessages] = useState([]);
  const [streaming, setStreaming] = useState(false);
  const [conversationId, setConversationId] = useState(null);

  // Tracks the current in-flight stream so we can abort it when the
  // user fires off a retry, edit, or switches conversations mid-run.
  // { controller, cancelled } -- `cancelled` lets the catch arm
  // distinguish a user abort from a real network/parse error.
  const inFlight = useRef(null);

  const cancelInFlight = useCallback(() => {
    const cur = inFlight.current;
    if (cur) {
      cur.cancelled = true;
      cur.controller.abort();
      inFlight.current = null;
    }
  }, []);

  const reset = useCallback(() => {
    cancelInFlight();
    setMessages([]);
    setConversationId(null);
    setStreaming(false);
  }, [cancelInFlight]);

  const loadFromConversation = useCallback(
    (conv) => {
      if (!conv) return;
      cancelInFlight();
      setStreaming(false);
      setConversationId(conv.id);
      setMessages(
        (conv.messages ?? []).map((m) => ({
          id: m.id,
          role: m.role,
          content: m.content,
          created_at: m.created_at,
          feedback_rating: m.feedback_rating ?? null,
        })),
      );
    },
    [cancelInFlight],
  );

  const _sendInternal = useCallback(
    async (text, baseMessages, conversationOverride) => {
      cancelInFlight();
      const controller = new AbortController();
      const me = { controller, cancelled: false };
      inFlight.current = me;

      const now = new Date().toISOString();
      const placeholderMessages = [
        ...baseMessages,
        { id: null, role: 'user', content: text, created_at: now },
        { id: null, role: 'assistant', content: '', created_at: now },
      ];
      setMessages(placeholderMessages);
      setStreaming(true);

      const updateAt = (offsetFromEnd, mutate) => {
        setMessages((m) => {
          const copy = [...m];
          const idx = copy.length - 1 - offsetFromEnd;
          if (idx < 0) return copy;
          copy[idx] = { ...copy[idx], ...mutate(copy[idx]) };
          return copy;
        });
      };

      try {
        await streamChat({
          token,
          conversationId: conversationOverride ?? conversationId,
          message: text,
          signal: controller.signal,
          onEvent: ({ event, data }) => {
            if (event === 'meta') {
              try {
                const parsed = JSON.parse(data);
                if (parsed.conversation_id) {
                  setConversationId(parsed.conversation_id);
                }
                if (parsed.user_message_id) {
                  updateAt(1, () => ({ id: parsed.user_message_id }));
                }
              } catch {
                // ignore malformed meta
              }
            } else if (event === 'step') {
              try {
                const step = JSON.parse(data);
                updateAt(0, (last) => ({
                  steps: [...(last.steps || []), step],
                }));
              } catch {
                // ignore malformed step
              }
            } else if (event === 'token') {
              updateAt(0, (last) => ({ content: last.content + data }));
            } else if (event === 'done') {
              try {
                const parsed = JSON.parse(data);
                if (parsed.assistant_message_id) {
                  updateAt(0, () => ({ id: parsed.assistant_message_id }));
                }
              } catch {
                // ignore malformed done
              }
            } else if (event === 'error') {
              updateAt(0, () => ({ content: `Error: ${data}` }));
            }
          },
        });
      } catch (err) {
        if (!me.cancelled) {
          updateAt(0, () => ({ content: `Error: ${err.message}` }));
        }
      } finally {
        if (inFlight.current === me) {
          inFlight.current = null;
          setStreaming(false);
        }
      }
    },
    [token, conversationId, cancelInFlight],
  );

  const send = useCallback(
    (text) => {
      if (!text.trim() || streaming) return;
      return _sendInternal(text, messages);
    },
    [messages, streaming, _sendInternal],
  );

  // Replace the user message at `index` with `newText` and stream a
  // fresh answer. Anything after `index` is discarded locally.
  // Aborts any in-flight stream so the edit takes over immediately.
  const editAt = useCallback(
    (index, newText) => {
      if (!newText.trim()) return;
      const base = messages.slice(0, index);
      return _sendInternal(newText, base);
    },
    [messages, _sendInternal],
  );

  // Regenerate the assistant message at `index` in place. The
  // preceding user message (and its timestamp) is left untouched on
  // screen and in the DB. Anything after the regenerated message is
  // dropped both locally and server-side, since the conversation
  // branches here. The old assistant text stays visible (with a
  // `regenerating` flag for styling) until the first token of the
  // new answer arrives, so the row does not flash empty.
  const retryAssistantAt = useCallback(
    async (index) => {
      const target = messages[index];
      if (!target || target.role !== 'assistant' || !target.id) return;

      cancelInFlight();
      const controller = new AbortController();
      const me = { controller, cancelled: false };
      inFlight.current = me;

      setMessages((m) => {
        const truncated = m.slice(0, index + 1);
        truncated[index] = {
          ...truncated[index],
          regenerating: true,
          feedback_rating: null,
          steps: [],
        };
        return truncated;
      });
      setStreaming(true);

      let firstToken = true;
      const updateAt = (mutate) => {
        setMessages((m) => {
          const copy = [...m];
          if (index >= copy.length) return copy;
          copy[index] = { ...copy[index], ...mutate(copy[index]) };
          return copy;
        });
      };

      try {
        await streamChat({
          token,
          conversationId,
          regenerateAssistantId: target.id,
          signal: controller.signal,
          onEvent: ({ event, data }) => {
            if (event === 'step') {
              try {
                const step = JSON.parse(data);
                updateAt((last) => ({
                  steps: [...(last.steps || []), step],
                }));
              } catch {
                // ignore malformed step
              }
            } else if (event === 'token') {
              if (firstToken) {
                firstToken = false;
                updateAt(() => ({
                  content: data,
                  id: null,
                  regenerating: false,
                  created_at: new Date().toISOString(),
                }));
              } else {
                updateAt((last) => ({ content: last.content + data }));
              }
            } else if (event === 'done') {
              try {
                const parsed = JSON.parse(data);
                if (parsed.assistant_message_id) {
                  updateAt(() => ({
                    id: parsed.assistant_message_id,
                    regenerating: false,
                  }));
                }
              } catch {
                // ignore malformed done
              }
            } else if (event === 'error') {
              updateAt(() => ({
                content: `Error: ${data}`,
                regenerating: false,
              }));
            }
          },
        });
      } catch (err) {
        if (!me.cancelled) {
          updateAt(() => ({
            content: `Error: ${err.message}`,
            regenerating: false,
          }));
        }
      } finally {
        if (inFlight.current === me) {
          inFlight.current = null;
          setStreaming(false);
        }
      }
    },
    [messages, token, conversationId, cancelInFlight],
  );

  return {
    messages,
    streaming,
    conversationId,
    send,
    editAt,
    retryAssistantAt,
    reset,
    loadFromConversation,
  };
}
