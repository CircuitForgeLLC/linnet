<!-- ComposeBar.vue — session start/stop controls
     Navigation v0.1.x stub: start/end session only.
     v0.2.x: mic capture, audio routing controls.
-->
<template>
  <div class="compose-bar">
    <button
      v-if="store.state === 'idle' || store.state === 'stopped'"
      class="btn-start"
      @click="handleStart"
      :disabled="starting"
    >
      {{ starting ? "Starting…" : "Start session" }}
    </button>

    <template v-else>
      <div class="session-info">
        <span class="session-dot" :class="{ active: store.state === 'running' }" />
        <span class="session-id">{{ store.sessionId?.slice(0, 8) }}…</span>
      </div>

      <label class="elcor-toggle" title="Elcor subtext mode">
        <input type="checkbox" v-model="elcorLocal" disabled />
        Elcor
      </label>

      <button class="btn-stop" @click="handleStop">End session</button>
    </template>

    <p v-if="error" class="compose-error">{{ error }}</p>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { useSessionStore } from "../stores/session";
import { useToneStream } from "../composables/useToneStream";

const store = useSessionStore();
const { connect, disconnect } = useToneStream();

const starting = ref(false);
const error = ref<string | null>(null);
const elcorLocal = ref(false);

async function handleStart() {
  starting.value = true;
  error.value = null;
  try {
    await store.startSession(elcorLocal.value);
    connect(store.sessionId!);
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : "Failed to start session";
  } finally {
    starting.value = false;
  }
}

async function handleStop() {
  disconnect();
  await store.endSession();
}
</script>

<script lang="ts">
export default { name: "ComposeBar" };
</script>

<style scoped>
.compose-bar {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem 1.5rem;
  background: var(--color-surface, #1a1d27);
  border-top: 1px solid var(--color-border, #2a2d3a);
  flex-wrap: wrap;
}

.btn-start,
.btn-stop {
  padding: 0.5rem 1.25rem;
  border-radius: 0.5rem;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  border: none;
  transition: opacity 0.2s;
}
.btn-start { background: #7c6af7; color: #fff; }
.btn-stop  { background: #374151; color: #e2e8f0; }
.btn-start:disabled { opacity: 0.6; cursor: not-allowed; }

.session-info {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.75rem;
  color: var(--color-muted, #6b7280);
  font-family: var(--font-mono, monospace);
}

.session-dot {
  width: 0.5rem;
  height: 0.5rem;
  border-radius: 50%;
  background: #374151;
}
.session-dot.active {
  background: #34d399;
  box-shadow: 0 0 6px #34d39966;
}

.elcor-toggle {
  font-size: 0.75rem;
  color: var(--color-muted, #6b7280);
  display: flex;
  align-items: center;
  gap: 0.3rem;
  cursor: not-allowed;
  opacity: 0.5;
}

.compose-error {
  width: 100%;
  font-size: 0.75rem;
  color: #ef4444;
  margin: 0;
}
</style>
