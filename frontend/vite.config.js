import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  envPrefix: ['VITE_', 'NEXT_PUBLIC_'],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:5000',
      '/ws': { target: 'ws://localhost:5000', ws: true },
      '/ai': {
        target: process.env.AI_SERVICE_URL || 'http://localhost:8001',
        rewrite: (path) => path.replace(/^\/ai/, ''),
      },
      '/uploads': 'http://localhost:5000',
      '/media': {
        target: process.env.AI_SERVICE_URL || 'http://localhost:8001',
      },
      '/ws/events': {
        target: 'ws://localhost:5000',
        ws: true,
      },
      '/socket.io': { target: 'http://localhost:5000', ws: true },
    },
  },
});
