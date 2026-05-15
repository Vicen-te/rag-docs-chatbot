export default function Sidebar({
  conversations,
  activeId,
  onSelect,
  onNewChat,
  onDelete,
  loading,
}) {
  return (
    <aside className="sidebar">
      <button type="button" className="new-chat" onClick={onNewChat}>
        + New chat
      </button>
      {/* {loading && <div className="sidebar-state">loading...</div>} */}
      {!loading && conversations.length === 0 && (
        <div className="sidebar-state">No conversations yet.</div>
      )}
      <ul>
        {conversations.map((c) => {
          const isActive = c.id === activeId;
          return (
            <li
              key={c.id}
              className={isActive ? 'active' : ''}
              onClick={() => onSelect(c.id)}
            >
              <div className="conv-title">{c.title || 'Untitled'}</div>
              <div className="conv-date">
                {new Date(c.updated_at).toLocaleString()}
              </div>
              <button
                type="button"
                className="conv-delete"
                onClick={(e) => {
                  e.stopPropagation();
                  onDelete(c.id);
                }}
                title="delete"
              >
                x
              </button>
            </li>
          );
        })}
      </ul>
    </aside>
  );
}
