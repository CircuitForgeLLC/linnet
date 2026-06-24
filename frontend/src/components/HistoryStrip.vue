<template>
  <div class="history-strip">
    <div
      v-for="(evt, i) in recent"
      :key="i"
      class="history-item"
      :data-affect="evt.affect"
      :title="`${speakerShort(evt.speaker_id)} · ${evt.label} (${(evt.confidence * 100).toFixed(0)}%)`"
    >
      <span v-if="speakerShort(evt.speaker_id)" class="history-spk" :data-spk="speakerSlot(evt.speaker_id)">{{ speakerShort(evt.speaker_id) }}</span>
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

// Returns single-letter label for a speaker_id, or empty for silence/unknown
function speakerShort(id: string | undefined): string {
  if (!id || id === "speaker_a") return "";
  if (id === "Multiple") return "M";
  const match = id.match(/Speaker\s+([A-Z]+)/i);
  return match ? match[1] : "";
}

// CSS slot key for per-speaker colour
function speakerSlot(id: string | undefined): string {
  if (!id || id === "speaker_a") return "";
  if (id === "Multiple") return "multi";
  const match = id.match(/Speaker\s+([A-Z]+)/i);
  return match ? match[1].toLowerCase() : "a";
}
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

.history-spk {
  font-size: 0.58rem;
  font-family: var(--font-mono, monospace);
  font-weight: 700;
  padding: 0.05em 0.35em;
  border-radius: 999px;
  border: 1px solid transparent;
  align-self: center;
}
.history-spk[data-spk="a"]     { background: #1e3050; color: #60a5fa; border-color: #60a5fa44; }
.history-spk[data-spk="b"]     { background: #2a1e3a; color: #c084fc; border-color: #c084fc44; }
.history-spk[data-spk="c"]     { background: #1e3a2f; color: #34d399; border-color: #34d39944; }
.history-spk[data-spk="d"]     { background: #2a2a1e; color: #fbbf24; border-color: #fbbf2444; }
.history-spk[data-spk="multi"] { background: #2a1e1e; color: #f87171; border-color: #f8717144; }

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
