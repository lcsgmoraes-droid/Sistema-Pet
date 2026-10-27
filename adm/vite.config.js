import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

// Em desenvolvimento e em producao o painel fala com a API pelo MESMO endereco dele ("/api"):
// o navegador nunca faz pedido para outro dominio, entao nao ha CORS e o cookie de sessao
// fica restrito a este endereco. Em dev o Vite faz a ponte; em producao, o nginx.
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const alvo = env.VITE_DEV_API_PROXY_TARGET || "http://127.0.0.1:8000";
  return {
    plugins: [react()],
    server: {
      proxy: {
        "/api": { target: alvo, changeOrigin: false, rewrite: (caminho) => caminho.replace(/^\/api/, "") },
      },
    },
    build: { emptyOutDir: true, sourcemap: false },
  };
});
