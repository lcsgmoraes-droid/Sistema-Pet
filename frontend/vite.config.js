import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

const timestamp = Date.now();

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const devApiProxyTarget = env.VITE_DEV_API_PROXY_TARGET || 'http://127.0.0.1:8000';

  return {
    plugins: [react()],
    build: {
      rollupOptions: {
        output: {
          manualChunks(id) {
            if (!id.includes('node_modules')) {
              return;
            }

            if (id.includes('react') || id.includes('react-dom') || id.includes('react-router-dom')) {
              return 'vendor-react';
            }
            if (id.includes('recharts')) {
              return 'vendor-charts';
            }
            if (id.includes('@dnd-kit')) {
              return 'vendor-dnd';
            }
            if (id.includes('xlsx') || id.includes('file-saver')) {
              return 'vendor-utils';
            }
            if (id.includes('lucide-react') || id.includes('react-icons')) {
              return 'vendor-icons';
            }
          },
          entryFileNames: `assets/[name]-${timestamp}.js`,
          chunkFileNames: `assets/[name]-${timestamp}.js`,
          assetFileNames: `assets/[name]-${timestamp}.[ext]`
        }
      }
    },
    server: {
      host: '0.0.0.0',
      port: 5173,
      strictPort: false,
      proxy: {
        // Em DEV: /api/* sempre aponta para o backend local (não para nginx de produção)
        '/api': {
          target: devApiProxyTarget,
          changeOrigin: true,
          secure: false,
          ws: true, // Habilita proxy de WebSocket (wss://localhost:5173/api/ws/...)
          rewrite: (path) => path.replace(/^\/api/, ''),
        },
      }
    },
  };
});
