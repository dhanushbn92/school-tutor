import path from "node:path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 5173,
    proxy: {
      // Everything the SPA fetches from the FastAPI backend goes through /api.
      // FastAPI itself mounts routes at root (/auth/login, /me/sections, ...),
      // so we strip the /api prefix when proxying.
      //
      // NOTE: backend port temporarily moved from 8000 → 8001 because
      // a stuck Windows phantom socket holds 8000 hostage (PID 34360
      // is dead but the kernel still has the listen socket). After a
      // reboot, change this back to 8000 and start uvicorn on 8000.
      "/api": {
        target: "http://127.0.0.1:8001",
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/api/, ""),
      },
    },
  },
});
