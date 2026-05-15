import { formatMessageTime } from '../lib/time.js';
import MessageActions from './MessageActions.jsx';

export default function AssistantMessage({
  token,
  message,
  isLast,
  streaming,
  onRetry,
}) {
  const regenerating = !!message.regenerating;
  // Only the message currently being generated is "in flight": either
  // the trailing placeholder of a fresh send (streaming && isLast &&
  // no id yet) or one being regenerated in place. Other prior
  // assistant messages keep their action row visible, which prevents
  // the whole transcript from jumping every time a new turn streams.
  const inFlight = (streaming && isLast && !message.id) || regenerating;
  const steps = message.steps || [];
  const hasSteps = steps.length > 0;
  const placeholder = inFlight && !message.content && !hasSteps ? '...' : '';
  const showActions = !inFlight && message.content && !message.content.startsWith('Error');

  const stepsList = hasSteps && (
    <ol className="steps">
      {steps.map((s, idx) => {
        const isActive = inFlight && idx === steps.length - 1 && !message.content;
        return (
          <li
            key={`${s.node}-${idx}`}
            className={`step stage-${s.stage}${isActive ? ' active' : ''}`}
          >
            <span className="step-dot" aria-hidden="true" />
            <span className="step-label">{s.label}</span>
            {s.detail && <span className="step-detail">{s.detail}</span>}
          </li>
        );
      })}
    </ol>
  );

  return (
    <div className={`msg assistant${regenerating ? ' regenerating' : ''}`}>
      <div className="role">
        assistant
        {message.created_at && (
          <span className="time">{formatMessageTime(message.created_at)}</span>
        )}
        {regenerating && <span className="time">regenerating...</span>}
      </div>
      {hasSteps && (
        inFlight ? stepsList : (
          <details className="steps-collapsed">
            <summary>
              process ({steps.length} step{steps.length === 1 ? '' : 's'})
            </summary>
            {stepsList}
          </details>
        )
      )}
      {(message.content || placeholder) && (
        <div className="content">{message.content || placeholder}</div>
      )}
      {showActions && (
        <MessageActions
          token={token}
          messageId={message.id}
          content={message.content}
          initialVote={message.feedback_rating ?? null}
          onRetry={onRetry}
        />
      )}
    </div>
  );
}
