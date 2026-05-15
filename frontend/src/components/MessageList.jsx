import { useLayoutEffect, useRef } from 'react';

import AssistantMessage from './AssistantMessage.jsx';
import UserMessage from './UserMessage.jsx';

// How close to the bottom the user must be (in px) for new content to
// keep auto-scrolling. If they scrolled further up than this we leave
// them alone so reading older messages mid-stream isn't yanked.
const STICK_THRESHOLD_PX = 80;

export default function MessageList({
  token,
  messages,
  streaming,
  onEdit,
  onRetryAt,
}) {
  const mainRef = useRef(null);
  const anchor = useRef(null);
  const pinned = useRef(true);
  const lastFirstIdRef = useRef(null);
  const prevStreamingRef = useRef(false);

  const handleScroll = () => {
    const el = mainRef.current;
    if (!el) return;
    const dist = el.scrollHeight - el.scrollTop - el.clientHeight;
    pinned.current = dist < STICK_THRESHOLD_PX;
  };

  // useLayoutEffect runs synchronously after DOM mutations but before
  // paint, so the scroll adjustment lands in the same frame as the
  // new message. That removes the tiny "jump" you'd otherwise see
  // when the transcript already overflows.
  useLayoutEffect(() => {
    // Conversation switch (first message identity changes) -> force
    // pin so the freshly loaded chat opens at the bottom.
    const firstId = messages[0]?.id ?? null;
    if (firstId !== lastFirstIdRef.current) {
      lastFirstIdRef.current = firstId;
      pinned.current = true;
    }
    // Rising edge of `streaming` means the user just sent or hit
    // retry. Snap to the new turn regardless of where they were.
    if (streaming && !prevStreamingRef.current) {
      pinned.current = true;
    }
    prevStreamingRef.current = streaming;

    if (pinned.current) {
      anchor.current?.scrollIntoView({ block: 'end' });
    }
  }, [messages, streaming]);

  if (messages.length === 0) {
    return (
      <main ref={mainRef} onScroll={handleScroll}>
        <div className="empty">Ask anything about the corpus.</div>
        <div ref={anchor} />
      </main>
    );
  }

  return (
    <main ref={mainRef} onScroll={handleScroll}>
      {messages.map((m, i) => {
        const isLast = i === messages.length - 1;
        // Index-only key: messages are append-only in this app, and a
        // stable key avoids remounting (and the visible flash) when
        // the backend later attaches a real UUID to a streamed message.
        const key = `msg-${i}`;
        if (m.role === 'user') {
          return (
            <UserMessage
              key={key}
              content={m.content}
              createdAt={m.created_at}
              index={i}
              onEdit={onEdit}
              canEdit={!streaming}
            />
          );
        }
        return (
          <AssistantMessage
            key={key}
            token={token}
            message={m}
            isLast={isLast}
            streaming={streaming}
            onRetry={() => onRetryAt(i)}
          />
        );
      })}
      <div ref={anchor} />
    </main>
  );
}
