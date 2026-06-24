<template>
  <div class="now-panel" :data-affect="affect">
    <!-- Row 1: diarization identity + speaker type + queue state badges -->
    <div class="now-badges">
      <div v-if="diarSpeaker" class="now-diar-id" :data-diar="diarSpeakerSlot">
        {{ diarSpeaker }}
      </div>
      <div v-if="speakerLabel" class="now-speaker" :data-speaker="speakerKind">
        {{ speakerLabel }}
      </div>
      <div v-if="queueLabel" class="now-queue-badge" :data-queue="queueKind">
        {{ queueLabel }}
      </div>
      <div v-if="environLabel" class="now-environ-badge" :data-environ="environKind">
        {{ environLabel }}
      </div>
      <div v-if="sceneLabel" class="now-scene-badge" :data-scene="sceneKind">
        {{ sceneLabel }}
      </div>
      <div
        v-if="privacyVisible"
        class="now-privacy-badge"
        :data-privacy="privacyRisk"
        :title="privacyTitle"
      >
        {{ privacyBadgeText }}
      </div>
    </div>

    <!-- Live transcript strip -->
    <div v-if="transcriptText" class="now-transcript">
      "{{ transcriptText }}"
    </div>

    <!-- Tone annotation -->
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
    <CorrectionWidget
      v-if="props.event"
      :item-id="props.event.session_id"
      :input-text="''"
      :original-output="annotationOutput"
      correction-type="annotation"
      api-path="/corrections"
      :context="{ session_id: props.event.session_id, label: props.event.label }"
    />
  </div>
</template>

<script setup lang="ts">
import type { ToneEvent } from "../stores/session";
import { useSessionStore } from "../stores/session";
import CorrectionWidget from "./CorrectionWidget.vue";

const props = defineProps<{
  event: ToneEvent | null;
}>();

const store = useSessionStore();

const label = computed(() => props.event?.label ?? "—");
const confidence = computed(() => props.event?.confidence ?? 0);
const subtext = computed(() => props.event?.subtext ?? null);
const affect = computed(() => props.event?.affect ?? "neutral");
const prosodyFlags = computed(() => props.event?.prosody_flags ?? []);
const shiftMagnitude = computed(() => props.event?.shift_magnitude ?? 0);
const shiftDirection = computed(() => props.event?.shift_direction ?? "stable");
const annotationOutput = computed(() => {
  if (!props.event) return "";
  const parts = [`[${props.event.label}]`];
  if (props.event.subtext) parts.push(props.event.subtext);
  return parts.join(" ");
});

// Diarization identity badge — shows "Speaker A", "Speaker B", "Multiple" from pyannote
// Hidden when speaker_id is "speaker_a" (the silence/unknown default) or absent
const diarSpeaker = computed(() => {
  const id = props.event?.speaker_id;
  if (!id || id === "speaker_a") return null;
  return id; // "Speaker A", "Speaker B", "Multiple"
});
// Slot letter for CSS colour mapping: "a" for Speaker A, "b" for Speaker B, etc.
const diarSpeakerSlot = computed(() => {
  const id = props.event?.speaker_id ?? "";
  if (id === "Multiple") return "multi";
  const match = id.match(/Speaker\s+([A-Z]+)/i);
  return match ? match[1].toLowerCase() : "a";
});

// Speaker type badge — hidden when no_speaker or no session
const SPEAKER_LABELS: Record<string, string> = {
  human_single: "Human",
  human_multi:  "Group",
  ivr_synth:    "IVR",
  no_speaker:   "",
  transfer:     "Transfer",
};
const speakerLabel = computed(() => {
  const raw = store.currentSpeaker?.label;
  if (!raw) return null;
  const mapped = SPEAKER_LABELS[raw] ?? raw;
  return mapped || null;
});
const speakerKind = computed(() => store.currentSpeaker?.label ?? "");

// Queue state badge (hold_music, ringback, silence, etc.)
const QUEUE_LABELS: Record<string, string> = {
  hold_music: "On Hold",
  ringback:   "Ringing",
  busy:       "Busy",
  dtmf_tone:  "DTMF",
  silence:    "Silence",
  dead_air:   "Dead Air",
};
const queueLabel = computed(() => {
  const raw = store.currentQueue?.label;
  if (!raw || raw === "silence") return null;
  return QUEUE_LABELS[raw] ?? raw;
});
const queueKind = computed(() => store.currentQueue?.label ?? "");

// Environment badge (call_center, music, noise, etc.)
const ENVIRON_LABELS: Record<string, string> = {
  call_center:       "Call Centre",
  music:             "Music",
  background_shift:  "Shift",
  noise_floor_change: "Noise",
  quiet:             "",
};
const environLabel = computed(() => {
  const raw = store.currentEnviron?.label;
  if (!raw || raw === "quiet") return null;
  return ENVIRON_LABELS[raw] ?? raw;
});
const environKind = computed(() => store.currentEnviron?.label ?? "");

// Acoustic scene badge
const SCENE_LABELS: Record<string, string> = {
  indoor_quiet:    "Quiet Indoor",
  indoor_crowd:    "Crowded Indoor",
  outdoor_urban:   "Urban",
  outdoor_nature:  "Nature",
  vehicle:         "Vehicle",
  public_transit:  "Transit",
};
const sceneLabel = computed(() => {
  const raw = store.currentScene?.label;
  if (!raw) return null;
  return SCENE_LABELS[raw] ?? raw;
});
const sceneKind = computed(() => store.currentScene?.label ?? "");

// Privacy risk indicator — calm, informational only. No alarm states.
const privacyRisk = computed(() => store.currentScene?.privacy_risk ?? "low");
const privacyVisible = computed(() => privacyRisk.value !== "low");
const PRIVACY_BADGE_TEXT: Record<string, string> = {
  moderate: "Private",
  high:     "Private",
};
const PRIVACY_TITLES: Record<string, string> = {
  moderate: "This environment may be identifiable — local processing preferred.",
  high:     "Private environment detected — audio is being processed locally only.",
};
const privacyBadgeText = computed(() => PRIVACY_BADGE_TEXT[privacyRisk.value] ?? "");
const privacyTitle = computed(() => PRIVACY_TITLES[privacyRisk.value] ?? "");

// Live transcript strip
const transcriptText = computed(() => store.currentTranscript?.text ?? null);
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

.now-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  align-items: center;
  min-height: 1.4rem;
}

/* Shared pill base for speaker / queue / environ / scene / privacy badges */
.now-speaker,
.now-queue-badge,
.now-environ-badge,
.now-scene-badge,
.now-privacy-badge {
  display: inline-block;
  font-size: 0.65rem;
  font-family: var(--font-mono, monospace);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  padding: 0.15em 0.6em;
  border-radius: 999px;
  background: var(--color-border, #2a2d3a);
  color: var(--color-muted, #6b7280);
  border: 1px solid transparent;
  transition: background 0.3s, color 0.3s;
}

/* Diarization identity badge — per-speaker colours */
.now-diar-id {
  display: inline-block;
  font-size: 0.65rem;
  font-family: var(--font-mono, monospace);
  font-weight: 700;
  letter-spacing: 0.06em;
  padding: 0.15em 0.6em;
  border-radius: 999px;
  border: 1px solid transparent;
  transition: background 0.3s, color 0.3s;
}
.now-diar-id[data-diar="a"]     { background: #1e3050; color: #60a5fa; border-color: #60a5fa44; }
.now-diar-id[data-diar="b"]     { background: #2a1e3a; color: #c084fc; border-color: #c084fc44; }
.now-diar-id[data-diar="c"]     { background: #1e3a2f; color: #34d399; border-color: #34d39944; }
.now-diar-id[data-diar="d"]     { background: #2a2a1e; color: #fbbf24; border-color: #fbbf2444; }
.now-diar-id[data-diar="multi"] { background: #2a1e1e; color: #f87171; border-color: #f8717144; }

/* Speaker type colours */
.now-speaker[data-speaker="human_single"] { background: #1e3a2f; color: #34d399; border-color: #34d39933; }
.now-speaker[data-speaker="human_multi"]  { background: #1e3a2f; color: #34d399; border-color: #34d39933; }
.now-speaker[data-speaker="ivr_synth"]    { background: #1e2a3a; color: #60a5fa; border-color: #60a5fa33; }
.now-speaker[data-speaker="transfer"]     { background: #2a2a1e; color: #fbbf24; border-color: #fbbf2433; }

/* Queue state colours */
.now-queue-badge[data-queue="hold_music"] { background: #2a1e3a; color: #a78bfa; border-color: #a78bfa33; }
.now-queue-badge[data-queue="ringback"]   { background: #2a2a1e; color: #fbbf24; border-color: #fbbf2433; }
.now-queue-badge[data-queue="busy"]       { background: #3a1e1e; color: #f87171; border-color: #f8717133; }
.now-queue-badge[data-queue="dtmf_tone"]  { background: #1e2a3a; color: #60a5fa; border-color: #60a5fa33; }
.now-queue-badge[data-queue="dead_air"]   { background: #1e1e1e; color: #4b5563; border-color: #4b556333; }

/* Environment colours — telephony */
.now-environ-badge[data-environ="call_center"]        { background: #1e2a3a; color: #60a5fa; border-color: #60a5fa22; }
.now-environ-badge[data-environ="music"]              { background: #2a1e3a; color: #a78bfa; border-color: #a78bfa22; }
.now-environ-badge[data-environ="background_shift"]   { background: #2a2a1e; color: #fbbf24; border-color: #fbbf2422; }
.now-environ-badge[data-environ="noise_floor_change"] { background: #2a1e1e; color: #f87171; border-color: #f8717122; }
/* Environment colours — nature */
.now-environ-badge[data-environ="birdsong"]   { background: #1e2e1e; color: #86efac; border-color: #86efac22; }
.now-environ-badge[data-environ="wind"]       { background: #1e2a2e; color: #7dd3fc; border-color: #7dd3fc22; }
.now-environ-badge[data-environ="rain"]       { background: #1e222e; color: #93c5fd; border-color: #93c5fd22; }
.now-environ-badge[data-environ="water"]      { background: #1e2a2e; color: #67e8f9; border-color: #67e8f922; }
/* Environment colours — urban */
.now-environ-badge[data-environ="traffic"]      { background: #2a201e; color: #fdba74; border-color: #fdba7422; }
.now-environ-badge[data-environ="crowd_chatter"]{ background: #2a1e28; color: #d8b4fe; border-color: #d8b4fe22; }
.now-environ-badge[data-environ="construction"] { background: #2a201e; color: #fb923c; border-color: #fb923c22; }
/* Environment colours — indoor */
.now-environ-badge[data-environ="hvac"]           { background: #1e2226; color: #94a3b8; border-color: #94a3b822; }
.now-environ-badge[data-environ="keyboard_typing"]{ background: #1e2226; color: #94a3b8; border-color: #94a3b822; }
.now-environ-badge[data-environ="restaurant"]     { background: #2a1e22; color: #fca5a5; border-color: #fca5a522; }

/* Acoustic scene badges — informational, cool tones */
.now-scene-badge[data-scene="indoor_quiet"]   { background: #1e2226; color: #94a3b8; border-color: #94a3b822; }
.now-scene-badge[data-scene="indoor_crowd"]   { background: #2a1e28; color: #c084fc; border-color: #c084fc22; }
.now-scene-badge[data-scene="outdoor_urban"]  { background: #2a201e; color: #fdba74; border-color: #fdba7422; }
.now-scene-badge[data-scene="outdoor_nature"] { background: #1e2e1e; color: #86efac; border-color: #86efac22; }
.now-scene-badge[data-scene="vehicle"]        { background: #1e2226; color: #7dd3fc; border-color: #7dd3fc22; }
.now-scene-badge[data-scene="public_transit"] { background: #1e2226; color: #7dd3fc; border-color: #7dd3fc22; }

/* Privacy risk indicator — calm, never alarming. Teal for both levels. */
.now-privacy-badge                        { cursor: default; }
.now-privacy-badge[data-privacy="moderate"]{ background: #1e2a2e; color: #67e8f9; border-color: #67e8f933; }
.now-privacy-badge[data-privacy="high"]   { background: #1e2a2e; color: #22d3ee; border-color: #22d3ee44; }

/* Live transcript strip */
.now-transcript {
  font-size: 0.8rem;
  color: var(--color-muted, #6b7280);
  font-style: italic;
  border-left: 2px solid var(--color-border, #2a2d3a);
  padding-left: 0.6rem;
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 100%;
}

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
