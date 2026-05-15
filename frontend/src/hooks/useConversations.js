import { useCallback, useEffect, useState } from 'react';

import {
  deleteConversation,
  getConversation,
  listConversations,
} from '../api/client.js';

export function useConversations(token) {
  const [conversations, setConversations] = useState([]);
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const data = await listConversations(token);
      setConversations(Array.isArray(data) ? data : data.results ?? []);
    } catch (err) {
      console.error('listConversations failed', err);
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const load = useCallback(
    async (id) => {
      if (!token || !id) return null;
      try {
        return await getConversation(token, id);
      } catch (err) {
        console.error('getConversation failed', err);
        return null;
      }
    },
    [token],
  );

  const remove = useCallback(
    async (id) => {
      if (!token || !id) return;
      try {
        await deleteConversation(token, id);
        setConversations((c) => c.filter((x) => x.id !== id));
      } catch (err) {
        console.error('deleteConversation failed', err);
      }
    },
    [token],
  );

  return { conversations, loading, refresh, load, remove };
}
