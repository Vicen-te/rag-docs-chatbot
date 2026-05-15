import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// The dev server proxies /api/* to the Django backend so the browser
// treats them as same-origin and we avoid configuring CORS.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
});
