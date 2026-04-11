import { defineStore } from "pinia";
import { ref, computed } from "vue";

export interface ToneEvent {
  event_type: string;
  label: string;
  confidence: number;
  speaker_id: string;
  shift_magnitude: number;
  timestamp: number;
  session_id: string;
  subtext: string | null;
  affect: string;
  shift_direction: string;
  prosody_flags: string[];
}

export interface SpeakerEvent {
  event_type: "speaker";
  session_id: string;
  label: string;
  confidence: number;
  timestamp: number;
}

export interface TranscriptEvent {
  event_type: "transcript";
  session_id: string;
  text: string;
  speaker_id: string;
  timestamp: number;
}

export interface QueueEvent {
  event_type: "queue" | "environ";
  session_id: string;
  label: string;
  confidence: number;
  timestamp: number;
}

export const useSessionStore = defineStore("session", () => {
  const sessionId = ref<string | null>(null);
  const elcor = ref(false);
  const state = ref<"idle" | "running" | "stopped">("idle");
  const events = ref<ToneEvent[]>([]);
  const latest = computed(() => events.value.at(-1) ?? null);
  const currentSpeaker = ref<SpeakerEvent | null>(null);
  const currentTranscript = ref<TranscriptEvent | null>(null);
  const currentQueue = ref<QueueEvent | null>(null);
  const currentEnviron = ref<QueueEvent | null>(null);

  const apiBase = import.meta.env.VITE_API_BASE ?? "";

  async function startSession(withElcor = false) {
    const resp = await fetch(`${apiBase}/session/start`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ elcor: withElcor }),
    });
    if (!resp.ok) throw new Error(`Failed to start session: ${resp.status}`);
    const data = await resp.json();
    sessionId.value = data.session_id;
    elcor.value = data.elcor;
    state.value = "running";
    events.value = [];
  }

  async function endSession() {
    if (!sessionId.value) return;
    await fetch(`${apiBase}/session/${sessionId.value}/end`, { method: "DELETE" });
    state.value = "stopped";
  }

  function pushEvent(evt: ToneEvent) {
    events.value.push(evt);
    // Cap history at 200 in the store (history endpoint handles server-side cap)
    if (events.value.length > 200) events.value.shift();
  }

  function updateSpeaker(evt: SpeakerEvent) {
    currentSpeaker.value = evt;
  }

  function updateTranscript(evt: TranscriptEvent) {
    currentTranscript.value = evt;
  }

  function updateQueue(evt: QueueEvent) {
    if (evt.event_type === "queue") {
      currentQueue.value = evt;
    } else {
      currentEnviron.value = evt;
    }
  }

  function reset() {
    sessionId.value = null;
    state.value = "idle";
    events.value = [];
    elcor.value = false;
    currentSpeaker.value = null;
    currentTranscript.value = null;
    currentQueue.value = null;
    currentEnviron.value = null;
  }

  return {
    sessionId, elcor, state, events, latest,
    currentSpeaker, currentTranscript, currentQueue, currentEnviron,
    startSession, endSession, pushEvent,
    updateSpeaker, updateTranscript, updateQueue,
    reset,
  };
});
