import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import UnoCSS from "unocss/vite";

export default defineConfig({
  plugins: [vue(), UnoCSS()],
  server: {
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
    },
  },
});
