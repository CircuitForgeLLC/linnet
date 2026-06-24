<template>
  <div class="app-shell">
    <header class="app-header">
      <img src="/linnet.svg" alt="Linnet" class="header-logo" />
      <h1 class="header-title">Linnet</h1>
      <span class="header-tagline">tone annotation</span>
    </header>

    <main class="app-main">
      <!-- v0.1.x: flat single-stream view (default, internal test fixture) -->
      <template v-if="!settings.threadView">
        <section class="now-section">
          <p class="section-label">Now</p>
          <NowPanel :event="store.latest" />
        </section>

        <section class="history-section">
          <p class="section-label">Recent</p>
          <HistoryStrip />
        </section>
      </template>

      <!-- v0.2.x: per-speaker thread view (dev preview — toggle in DevPanel) -->
      <template v-else>
        <section class="thread-section">
          <p class="section-label">Conversation threads <span class="thread-preview-badge">v0.2 preview</span></p>
          <div class="thread-placeholder">ThreadView not yet built — coming in v0.2.x</div>
        </section>
      </template>
    </main>

    <footer class="app-footer">
      <DevPanel v-if="isDev" />
      <ComposeBar />
    </footer>
  </div>
</template>

<script setup lang="ts">
import { useSessionStore } from "./stores/session";
import { useSettingsStore } from "./stores/settings";
import NowPanel from "./components/NowPanel.vue";
import HistoryStrip from "./components/HistoryStrip.vue";
import ComposeBar from "./components/ComposeBar.vue";
import DevPanel from "./components/DevPanel.vue";

const store = useSessionStore();
const settings = useSettingsStore();
const isDev = import.meta.env.DEV;
</script>

<style>
/* Global reset + CSS custom properties */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --color-bg:      #0f1117;
  --color-surface: #1a1d27;
  --color-border:  #2a2d3a;
  --color-muted:   #6b7280;
  --color-text:    #e2e8f0;
  --color-accent:  #7c6af7;
  --font-sans: "Inter", system-ui, sans-serif;
  --font-mono: "JetBrains Mono", monospace;
}

body {
  background: var(--color-bg);
  color: var(--color-text);
  font-family: var(--font-sans);
  min-height: 100dvh;
}

/* Respect prefers-reduced-motion throughout */
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { transition: none !important; animation: none !important; }
}
</style>

<style scoped>
.app-shell {
  display: flex;
  flex-direction: column;
  min-height: 100dvh;
  max-width: 640px;
  margin: 0 auto;
}

.app-header {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 1rem 1.5rem;
  border-bottom: 1px solid var(--color-border);
}

.header-logo { width: 1.75rem; height: 1.75rem; }

.header-title {
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--color-text);
}

.header-tagline {
  font-size: 0.75rem;
  color: var(--color-muted);
  margin-left: 0.2rem;
}

.app-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  padding: 1.5rem;
}

.section-label {
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--color-muted);
  margin-bottom: 0.5rem;
}

.thread-preview-badge {
  font-size: 0.6rem;
  text-transform: none;
  letter-spacing: 0;
  color: var(--color-accent);
  border: 1px solid color-mix(in srgb, var(--color-accent) 40%, transparent);
  border-radius: 0.25rem;
  padding: 0.05rem 0.3rem;
  margin-left: 0.4rem;
  vertical-align: middle;
}

.thread-placeholder {
  color: var(--color-muted);
  font-size: 0.85rem;
  font-style: italic;
  padding: 2rem 0;
  text-align: center;
}

.app-footer {
  position: sticky;
  bottom: 0;
}
</style>
