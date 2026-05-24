import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// During dev, proxy /api and /webhook to the FastAPI engine so the
// React app can talk to the backend without CORS plumbing.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": "http://localhost:8000",
      "/stream": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "dist",
    sourcemap: true,
  },
});
