import { useEffect, useRef, useState } from 'react';

export default function MessageInput({ onSend, streaming }) {
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
      <button type="submit" disabled={streaming || !value.trim()}>
        Send
      </button>
    </form>
  );
}
