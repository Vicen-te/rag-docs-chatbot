import { useEffect, useRef } from 'react';

import { useChat } from '../hooks/useChat.js';
import { useConversations } from '../hooks/useConversations.js';
import MessageInput from './MessageInput.jsx';
import MessageList from './MessageList.jsx';
import Sidebar from './Sidebar.jsx';

export default function Chat({ token, onLogout }) {
  const {
    messages,
    send,
    editAt,
    retryAssistantAt,
    streaming,
    conversationId,
    stop,
    reset,
    loadFromConversation,
  } = useChat(token);

  const { conversations, loading, refresh, load, remove } =
    useConversations(token);

  // Refresh the sidebar whenever a new conversation id appears.
  const lastSeenConvId = useRef(null);
  useEffect(() => {
    if (
      conversationId &&
      conversationId !== lastSeenConvId.current &&
      !streaming
    ) {
      lastSeenConvId.current = conversationId;
      refresh();
    }
  }, [conversationId, streaming, refresh]);

  const handleSelect = async (id) => {
    if (id === conversationId || streaming) return;
    const conv = await load(id);
    if (conv) loadFromConversation(conv);
  };

  const handleNewChat = () => {
    if (streaming) return;
    reset();
    lastSeenConvId.current = null;
  };

  const handleDelete = async (id) => {
    if (id === conversationId) {
      reset();
      lastSeenConvId.current = null;
    }
    await remove(id);
  };

  return (
    <div className="layout">
      <Sidebar
        conversations={conversations}
        activeId={conversationId}
        onSelect={handleSelect}
        onNewChat={handleNewChat}
        onDelete={handleDelete}
        loading={loading}
      />
      <div className="chat">
        <header>
          <h1>rag-docs-chatbot</h1>
          <button type="button" onClick={onLogout}>
            Logout
          </button>
        </header>
        <MessageList
          token={token}
          messages={messages}
          streaming={streaming}
          onEdit={editAt}
          onRetryAt={retryAssistantAt}
        />
        <MessageInput onSend={send} onStop={stop} streaming={streaming} />
      </div>
    </div>
  );
}
