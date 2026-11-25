import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";
import { VitePWA } from "vite-plugin-pwa";

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: "autoUpdate",
      includeAssets: ["icon.svg"],
      manifest: {
        name: "AI Executive Co-pilot",
        short_name: "Co-pilot",
        description: "Executive attention dashboard",
        theme_color: "#12372a",
        background_color: "#f4f7f5",
        display: "standalone",
        start_url: "/",
        icons: [
          {
            src: "/icon.svg",
            sizes: "any",
            type: "image/svg+xml",
            purpose: "any",
          },
        ],
      },
    }),
  ],
  server: {
    proxy: {
      "/api": {
        target: process.env.VITE_API_PROXY_TARGET ?? "http://127.0.0.1:8000",
        changeOrigin: false,
      },
      "/healthz": {
        target: process.env.VITE_API_PROXY_TARGET ?? "http://127.0.0.1:8000",
      },
      "/readyz": {
        target: process.env.VITE_API_PROXY_TARGET ?? "http://127.0.0.1:8000",
      },
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: "./src/test/setup.ts",
    include: ["src/**/*.{test,spec}.{ts,tsx}"],
    css: true,
  },
});
