import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath, URL } from "node:url";

const backend = process.env.VITE_BACKEND_URL ?? "http://127.0.0.1:8000";

const proxy = {
  "/api": backend,
  "/health": backend,
  "/admin": backend,
  "/static": backend,
};

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
  },
  server: { port: 5173, host: "127.0.0.1", proxy },
  preview: { port: 4173, host: "127.0.0.1", proxy },
  build: {
    outDir: "dist",
    sourcemap: false,
    chunkSizeWarningLimit: 600,
  },
});
