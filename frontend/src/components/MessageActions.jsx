import { useEffect, useState } from 'react';

import { submitFeedback } from '../api/client.js';

export default function MessageActions({
  token,
  messageId,
  content,
  initialVote,
  onRetry,
}) {
  const [copied, setCopied] = useState(false);
  const [voted, setVoted] = useState(initialVote ?? null);
  const [feedbackError, setFeedbackError] = useState('');

  useEffect(() => {
    setVoted(initialVote ?? null);
    setFeedbackError('');
  }, [initialVote, messageId]);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      setCopied(false);
    }
  };

  const rate = async (rating) => {
    if (!messageId || voted === rating) return;
    setFeedbackError('');
    const previous = voted;
    setVoted(rating);
    try {
      await submitFeedback(token, { message: messageId, rating });
    } catch (err) {
      setVoted(previous);
      setFeedbackError(err.message);
    }
  };

  return (
    <div className="actions">
      <button type="button" onClick={copy} title="copy">
        {copied ? 'copied' : 'copy'}
      </button>
      <button type="button" onClick={onRetry} title="retry" disabled={!onRetry}>
        retry
      </button>
      <button
        type="button"
        onClick={() => rate('positive')}
        disabled={!messageId || voted !== null}
        className={voted === 'positive' ? 'voted up' : ''}
        title="thumbs up"
      >
        +1
      </button>
      <button
        type="button"
        onClick={() => rate('negative')}
        disabled={!messageId || voted !== null}
        className={voted === 'negative' ? 'voted down' : ''}
        title="thumbs down"
      >
        -1
      </button>
      {feedbackError && <span className="actions-error">{feedbackError}</span>}
    </div>
  );
}
