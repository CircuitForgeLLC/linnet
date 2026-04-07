import { defineConfig, presetUno, presetWebFonts } from "unocss";

export default defineConfig({
  presets: [
    presetUno(),
    presetWebFonts({
      fonts: {
        sans: "Inter:400,500,600",
        mono: "JetBrains Mono:400",
      },
    }),
  ],
  theme: {
    colors: {
      // Linnet palette: calm neutral base, accent tones per affect
      bg: "#0f1117",
      surface: "#1a1d27",
      border: "#2a2d3a",
      muted: "#6b7280",
      text: "#e2e8f0",
      accent: "#7c6af7",  // Linnet purple
      // Tone affect colours
      warm: "#f59e0b",
      frustrated: "#ef4444",
      confused: "#f97316",
      apologetic: "#60a5fa",
      scripted: "#9ca3af",
      genuine: "#34d399",
      dismissive: "#a78bfa",
      neutral: "#6b7280",
      urgent: "#fbbf24",
      tired: "#94a3b8",
    },
  },
});
