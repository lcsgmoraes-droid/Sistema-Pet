import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const devApiProxyTarget = env.VITE_DEV_API_PROXY_TARGET || "http://127.0.0.1:8000";

  return {
    plugins: [react()],
    build: {
      emptyOutDir: true,
      rolldownOptions: {
        output: {
          codeSplitting: {
            groups: [
              {
                name: "vendor-react",
                test: /node_modules[\\/](react|react-dom|react-router-dom)[\\/]/,
                priority: 40,
              },
              {
                name: "vendor-charts-d3",
                test: /node_modules[\\/](victory-vendor|d3-[^\\/]+)[\\/]/,
                priority: 35,
              },
              {
                name: "vendor-charts-runtime",
                test: /node_modules[\\/](@reduxjs[\\/]toolkit|react-redux|redux|redux-thunk|reselect|immer|use-sync-external-store|eventemitter3|decimal\.js-light|es-toolkit)[\\/]/,
                priority: 34,
              },
              {
                name: "vendor-charts",
                test: /node_modules[\\/]recharts[\\/]/,
                priority: 33,
              },
              {
                name: "vendor-dnd",
                test: /node_modules[\\/]@dnd-kit[\\/]/,
                priority: 30,
              },
              {
                name: "vendor-utils",
                test: /node_modules[\\/](xlsx|file-saver)[\\/]/,
                priority: 30,
              },
              {
                name: "vendor-icons",
                test: /node_modules[\\/](lucide-react|react-icons)[\\/]/,
                priority: 30,
              },
            ],
          },
          entryFileNames: "assets/[name]-[hash].js",
          chunkFileNames: "assets/[name]-[hash].js",
          assetFileNames: "assets/[name]-[hash].[ext]",
        },
      },
    },
    server: {
      host: "0.0.0.0",
      port: 5173,
      strictPort: false,
      proxy: {
        // Em DEV: /api/* sempre aponta para o backend local (não para nginx de produção)
        "/api": {
          target: devApiProxyTarget,
          changeOrigin: true,
          secure: false,
          ws: true, // Habilita proxy de WebSocket (wss://localhost:5173/api/ws/...)
          rewrite: (path) => path.replace(/^\/api/, ""),
        },
        // Em DEV: /uploads/* aponta para o backend local (imagens de produtos, logos, banners)
        "/uploads": {
          target: devApiProxyTarget,
          changeOrigin: true,
          secure: false,
        },
      },
    },
  };
});
