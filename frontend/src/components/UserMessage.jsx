import { useState } from 'react';

import { formatMessageTime } from '../lib/time.js';

export default function UserMessage({
  content,
  createdAt,
  index,
  onEdit,
  canEdit,
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(content);

  const startEdit = () => {
    setDraft(content);
    setEditing(true);
  };

  const cancel = () => {
    setDraft(content);
    setEditing(false);
  };

  const save = () => {
    if (!draft.trim() || draft === content) {
      cancel();
      return;
    }
    onEdit(index, draft);
    setEditing(false);
  };

  if (editing) {
    return (
      <div className="msg user editing">
        <div className="role">user (editing)</div>
        <textarea
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          autoFocus
          rows={Math.max(2, draft.split('\n').length)}
        />
        <div className="edit-actions">
          <button type="button" onClick={cancel}>
            Cancel
          </button>
          <button type="button" onClick={save}>
            Save and retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="msg user">
      <div className="role">
        user
        {createdAt && (
          <span className="time">{formatMessageTime(createdAt)}</span>
        )}
        <button
          type="button"
          className="edit-btn"
          onClick={startEdit}
          disabled={!canEdit}
        >
          edit
        </button>
      </div>
      <div className="content">{content}</div>
    </div>
  );
}
