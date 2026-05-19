# Frontend

Minimal React + Vite client for the rag-docs-chatbot API. Two screens:
a login form (calls `/api/token/`) and a chat view that streams the
pipeline's response via SSE from `/api/rag/chat/`.

## Run

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The Vite dev server proxies `/api/*` to
`http://127.0.0.1:8000`, so the Django backend must be running first.

## Notes

- The access token is stored in `localStorage`. No refresh-token flow
  yet -- if the token expires, log out and back in.
- Token streaming reads `event-stream` chunks directly from the fetch
  response body. SSE leading-space stripping is handled in
  `parseSseChunk` so word breaks survive.
- No state management library. If this grows, swap in Zustand or
  TanStack Query.
