<template>
  <div class="history-strip">
    <div
      v-for="(evt, i) in recent"
      :key="i"
      class="history-item"
      :data-affect="evt.affect"
      :title="`${evt.label} (${(evt.confidence * 100).toFixed(0)}%)`"
    >
      <span class="history-label">{{ evt.label }}</span>
      <span class="history-conf">{{ (evt.confidence * 100).toFixed(0) }}%</span>
    </div>
    <div v-if="!recent.length" class="history-empty">
      No annotations yet
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useSessionStore } from "../stores/session";

const DISPLAY_COUNT = 8;

const store = useSessionStore();
// Most recent N events, newest last (scroll right)
const recent = computed(() => store.events.slice(-DISPLAY_COUNT));
</script>

<script lang="ts">
export default { name: "HistoryStrip" };
</script>

<style scoped>
.history-strip {
  display: flex;
  flex-direction: row;
  gap: 0.5rem;
  overflow-x: auto;
  padding: 0.75rem 0;
  scrollbar-width: thin;
}

.history-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.2rem;
  padding: 0.5rem 0.75rem;
  border-radius: 0.5rem;
  background: var(--color-surface, #1a1d27);
  border: 1px solid var(--color-border, #2a2d3a);
  min-width: 5rem;
  cursor: default;
  flex-shrink: 0;
}

/* Affect tints — same palette as NowPanel */
.history-item[data-affect="warm"]       { border-color: #f59e0b66; }
.history-item[data-affect="frustrated"] { border-color: #ef444466; }
.history-item[data-affect="confused"]   { border-color: #f9731666; }
.history-item[data-affect="apologetic"] { border-color: #60a5fa66; }
.history-item[data-affect="genuine"]    { border-color: #34d39966; }
.history-item[data-affect="dismissive"] { border-color: #a78bfa66; }
.history-item[data-affect="urgent"]     { border-color: #fbbf2466; }

.history-label {
  font-size: 0.7rem;
  color: var(--color-text, #e2e8f0);
  text-align: center;
  line-height: 1.2;
}

.history-conf {
  font-size: 0.65rem;
  color: var(--color-muted, #6b7280);
  font-family: var(--font-mono, monospace);
}

.history-empty {
  font-size: 0.8rem;
  color: var(--color-muted, #6b7280);
  padding: 0.5rem;
}
</style>
