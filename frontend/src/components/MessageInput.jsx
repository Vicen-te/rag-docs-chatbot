import { useEffect, useRef, useState } from 'react';

export default function MessageInput({ onSend, onStop, streaming }) {
  const [value, setValue] = useState('');
  const inputRef = useRef(null);

  // Keep focus on the input across stream boundaries so the user can
  // fire off the next message with Enter without re-clicking.
  useEffect(() => {
    if (!streaming) inputRef.current?.focus();
  }, [streaming]);

  const submit = (e) => {
    e.preventDefault();
    if (!value.trim() || streaming) return;
    onSend(value);
    setValue('');
    inputRef.current?.focus();
  };

  return (
    <form onSubmit={submit}>
      <input
        ref={inputRef}
        placeholder={streaming ? 'thinking...' : 'Write a message...'}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        autoFocus
      />
      {streaming ? (
        <button type="button" className="stop-btn" onClick={onStop}>
          Stop
        </button>
      ) : (
        <button type="submit" disabled={!value.trim()}>
          Send
        </button>
      )}
    </form>
  );
}
