import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import UnoCSS from "unocss/vite";

export default defineConfig({
  base: process.env.VITE_BASE_URL ?? "/",
  plugins: [vue(), UnoCSS()],
  server: {
    host: "0.0.0.0",
    port: 8521,
    proxy: {
      "/session": {
        target: "http://localhost:8522",
        changeOrigin: true,
        ws: true,
      },
      "/health": {
        target: "http://localhost:8522",
        changeOrigin: true,
      },
      "/corrections": {
        target: "http://localhost:8522",
        changeOrigin: true,
      },
    },
  },
});
