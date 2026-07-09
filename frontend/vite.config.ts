import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

// The dashboard talks to the FastAPI backend. In dev we proxy /api and /v1 to
// http://localhost:8000 so there are no CORS surprises and no hard-coded URLs.
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 5173,
    proxy: {
      "/api": "http://localhost:8000",
      "/v1": "http://localhost:8000",
      "/health": "http://localhost:8000",
    },
  },
});
