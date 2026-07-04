import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

// В dev проксируем /api и /ws на backend (без CORS-хлопот).
// В проде фронт (Vercel) обращается к VITE_API_URL (Railway).
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@": path.resolve(__dirname, "src") },
  },
  server: {
    port: 5173,
    proxy: {
      "/api": "http://localhost:8000",
      "/ws": { target: "ws://localhost:8000", ws: true },
    },
  },
  build: {
    // Code-splitting: вынести тяжёлые вендоры отдельно (§6.4)
    rollupOptions: {
      output: {
        manualChunks: {
          react: ["react", "react-dom", "react-router-dom"],
          query: ["@tanstack/react-query", "@tanstack/react-query-persist-client"],
        },
      },
    },
  },
});
