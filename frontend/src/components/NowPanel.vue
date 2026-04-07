<template>
  <div class="now-panel" :data-affect="affect">
    <div class="now-label">{{ label }}</div>
    <div v-if="subtext" class="now-subtext">{{ subtext }}</div>
    <div class="now-meta">
      <span class="now-confidence">{{ (confidence * 100).toFixed(0) }}%</span>
      <span v-if="prosodyFlags.length" class="now-flags">
        {{ prosodyFlags.join(" · ") }}
      </span>
    </div>
    <div v-if="shiftMagnitude > 0.15" class="now-shift" :data-direction="shiftDirection">
      <span v-if="shiftDirection === 'escalating'">↑</span>
      <span v-else-if="shiftDirection === 'de-escalating'">↓</span>
      <span v-else>~</span>
      shift {{ (shiftMagnitude * 100).toFixed(0) }}%
    </div>
  </div>
</template>

<script setup lang="ts">
import type { ToneEvent } from "../stores/session";

const props = defineProps<{
  event: ToneEvent | null;
}>();

const label = computed(() => props.event?.label ?? "—");
const confidence = computed(() => props.event?.confidence ?? 0);
const subtext = computed(() => props.event?.subtext ?? null);
const affect = computed(() => props.event?.affect ?? "neutral");
const prosodyFlags = computed(() => props.event?.prosody_flags ?? []);
const shiftMagnitude = computed(() => props.event?.shift_magnitude ?? 0);
const shiftDirection = computed(() => props.event?.shift_direction ?? "stable");
</script>

<script lang="ts">
import { computed } from "vue";
export default { name: "NowPanel" };
</script>

<style scoped>
.now-panel {
  padding: 1.5rem 2rem;
  border-radius: 1rem;
  background: var(--color-surface, #1a1d27);
  border: 1px solid var(--color-border, #2a2d3a);
  transition: border-color 0.4s ease;
  min-height: 7rem;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

/* Affect-aware border tint */
.now-panel[data-affect="warm"]       { border-color: #f59e0b44; }
.now-panel[data-affect="frustrated"] { border-color: #ef444444; }
.now-panel[data-affect="confused"]   { border-color: #f9731644; }
.now-panel[data-affect="apologetic"] { border-color: #60a5fa44; }
.now-panel[data-affect="genuine"]    { border-color: #34d39944; }
.now-panel[data-affect="dismissive"] { border-color: #a78bfa44; }
.now-panel[data-affect="urgent"]     { border-color: #fbbf2444; }

.now-label {
  font-size: 1.35rem;
  font-weight: 600;
  color: var(--color-text, #e2e8f0);
  line-height: 1.2;
}

.now-subtext {
  font-size: 0.85rem;
  color: var(--color-muted, #6b7280);
  font-style: italic;
}

.now-meta {
  display: flex;
  gap: 1rem;
  font-size: 0.75rem;
  color: var(--color-muted, #6b7280);
  font-family: var(--font-mono, monospace);
}

.now-shift {
  font-size: 0.75rem;
  color: var(--color-muted, #6b7280);
}
.now-shift[data-direction="escalating"] { color: #f59e0b; }
.now-shift[data-direction="de-escalating"] { color: #60a5fa; }
</style>
