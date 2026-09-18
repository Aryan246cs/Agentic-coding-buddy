import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // Published apps live at /a/<slug> and sites at /s/<slug>, so the dev
    // server must serve index.html for any path rather than 404ing.
    proxy: {
      '/api': { target: 'http://localhost:8000', changeOrigin: true },
    },
  },
});
