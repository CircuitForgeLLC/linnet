<!-- DevPanel.vue — dev-only cf-voice lifecycle controls and UI feature flags -->
<!-- Only rendered when import.meta.env.DEV is true (Vite dev server) -->
<template>
  <div class="dev-panel">
    <span class="dev-label">dev</span>
    <span class="dev-section">cf-voice</span>

    <button class="dev-btn" :disabled="busy" @click="stop">Stop</button>
    <button class="dev-btn" :disabled="busy" @click="restart">Restart</button>

    <span v-if="status" class="dev-status" :class="statusClass">{{ status }}</span>

    <span class="dev-divider" aria-hidden="true">|</span>
    <span class="dev-section">ui</span>
    <button
      class="dev-btn dev-btn--toggle"
      :class="{ 'dev-btn--active': settings.threadView }"
      @click="settings.threadView = !settings.threadView"
      :title="settings.threadView ? 'Switch to v0.1.x (NowPanel)' : 'Switch to v0.2.x (ThreadView preview)'"
    >
      {{ settings.threadView ? 'v0.2 thread' : 'v0.1 now' }}
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from "vue";
import { useSettingsStore } from "../stores/settings";

const settings = useSettingsStore();
const apiBase = import.meta.env.VITE_API_BASE ?? "";
const busy = ref(false);
const status = ref<string | null>(null);
const isError = ref(false);

const statusClass = computed(() => isError.value ? "dev-status--err" : "dev-status--ok");

async function call(action: "stop" | "restart") {
  busy.value = true;
  status.value = action === "restart" ? "restarting…" : "stopping…";
  isError.value = false;
  try {
    const resp = await fetch(`${apiBase}/dev/voice/${action}`, { method: "POST" });
    if (!resp.ok) {
      const body = await resp.json().catch(() => ({ detail: resp.statusText }));
      throw new Error(body.detail ?? resp.statusText);
    }
    status.value = action === "restart" ? "restarted" : "stopped";
  } catch (e: unknown) {
    isError.value = true;
    status.value = e instanceof Error ? e.message : "failed";
  } finally {
    busy.value = false;
    // Clear status after 4 s
    setTimeout(() => { status.value = null; }, 4000);
  }
}

function stop() { call("stop"); }
function restart() { call("restart"); }
</script>

<script lang="ts">
export default { name: "DevPanel" };
</script>

<style scoped>
.dev-panel {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.3rem 1rem;
  background: color-mix(in srgb, #f59e0b 8%, var(--color-surface, #1a1d27));
  border-top: 1px solid color-mix(in srgb, #f59e0b 25%, transparent);
  font-size: 0.7rem;
  flex-wrap: wrap;
}

.dev-label {
  font-family: var(--font-mono, monospace);
  font-size: 0.62rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #f59e0b;
  background: color-mix(in srgb, #f59e0b 15%, transparent);
  border: 1px solid color-mix(in srgb, #f59e0b 30%, transparent);
  border-radius: 0.2rem;
  padding: 0.1rem 0.35rem;
}

.dev-section {
  color: var(--color-muted, #6b7280);
  font-family: var(--font-mono, monospace);
}

.dev-btn {
  padding: 0.2rem 0.6rem;
  border-radius: 0.3rem;
  border: 1px solid var(--color-border, #2a2d3a);
  background: transparent;
  color: var(--color-text, #e2e8f0);
  font-size: 0.7rem;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
}
.dev-btn:hover:not(:disabled) {
  border-color: #f59e0b;
  background: color-mix(in srgb, #f59e0b 10%, transparent);
}
.dev-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.dev-status {
  font-family: var(--font-mono, monospace);
  font-size: 0.68rem;
}
.dev-status--ok  { color: #34d399; }
.dev-status--err { color: #ef4444; }

.dev-divider {
  color: var(--color-border, #2a2d3a);
  user-select: none;
}

.dev-btn--toggle {
  border-color: color-mix(in srgb, #7c6af7 40%, transparent);
  color: var(--color-muted, #6b7280);
}
.dev-btn--toggle.dev-btn--active {
  border-color: #7c6af7;
  color: #7c6af7;
  background: color-mix(in srgb, #7c6af7 12%, transparent);
}
</style>
