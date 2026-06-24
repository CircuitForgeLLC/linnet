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
  // Dimensional emotion (audeering model — Navigation v0.2.x)
  valence: number | null;
  arousal: number | null;
  dominance: number | null;
  // Prosodic signals (openSMILE — Navigation v0.2.x)
  sarcasm_risk: number | null;
  flat_f0_score: number | null;
  // Trajectory signals — null until baseline established (min 3 frames per speaker)
  arousal_delta: number | null;
  valence_delta: number | null;
  trend: string | null;
  // Coherence signals (SER vs VAD cross-comparison)
  coherence_score: number | null;
  suppression_flag: boolean | null;
  reframe_type: string | null;
  affect_divergence: number | null;
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

export interface ServiceEvent {
  event_type: "service";
  session_id: string;
  status: "ready" | "loading" | "error";
  detail: string;
}

export interface SceneEvent {
  event_type: "scene";
  session_id: string;
  label: string;
  confidence: number;
  timestamp: number;
  privacy_risk: "low" | "moderate" | "high";
}

export interface AccentEvent {
  event_type: "accent";
  session_id: string;
  region: string;
  language: string;
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
  const currentScene = ref<SceneEvent | null>(null);
  const currentAccent = ref<AccentEvent | null>(null);

  // voiceReady: false until the backend probes cf-voice and emits service-event status="ready".
  // voiceError: non-null when the probe times out — surfaced as a warning in the UI.
  // voiceWarning: non-null for soft/non-fatal warnings (e.g. diarizer misconfigured).
  // voiceLoadingDetail: non-null while models are downloading (cleared when all stable).
  const voiceReady = ref(false);
  const voiceError = ref<string | null>(null);
  const voiceWarning = ref<string | null>(null);
  const voiceLoadingDetail = ref<string | null>(null);

  const apiBase = import.meta.env.VITE_API_BASE ?? "";

  async function startSession(opts: {
    elcor?: boolean;
    windowMs?: number;
    transcribeLang?: string;
    numSpeakers?: number;
  } = {}) {
    const resp = await fetch(`${apiBase}/session/start`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        elcor: opts.elcor ?? false,
        window_ms: opts.windowMs ?? 1000,
        transcribe_lang: opts.transcribeLang ?? "",
        num_speakers: opts.numSpeakers ?? 0,
      }),
    });
    if (!resp.ok) throw new Error(`Failed to start session: ${resp.status}`);
    const data = await resp.json();
    sessionId.value = data.session_id;
    elcor.value = data.elcor;
    state.value = "running";
    events.value = [];
    voiceReady.value = false;
    voiceError.value = null;
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

  function updateScene(evt: SceneEvent) {
    currentScene.value = evt;
  }

  function updateAccent(evt: AccentEvent) {
    currentAccent.value = evt;
  }

  // TTL timers — clear environ/queue badges when the signal drops out.
  // AST classifier emits nothing when confidence falls below threshold, so without
  // a TTL the badge stays stuck indefinitely (e.g. music badge after music stops).
  let _environTimer: ReturnType<typeof setTimeout> | null = null;
  let _queueTimer: ReturnType<typeof setTimeout> | null = null;
  const ENVIRON_TTL_MS = 5000;
  const QUEUE_TTL_MS = 4000;

  function updateQueue(evt: QueueEvent) {
    if (evt.event_type === "queue") {
      currentQueue.value = evt;
      if (_queueTimer) clearTimeout(_queueTimer);
      _queueTimer = setTimeout(() => { currentQueue.value = null; }, QUEUE_TTL_MS);
    } else {
      currentEnviron.value = evt;
      if (_environTimer) clearTimeout(_environTimer);
      _environTimer = setTimeout(() => { currentEnviron.value = null; }, ENVIRON_TTL_MS);
    }
  }

  function updateService(evt: ServiceEvent) {
    if (evt.status === "ready") {
      voiceReady.value = true;
      voiceError.value = null;
    } else if (evt.status === "error") {
      voiceError.value = evt.detail || "Voice service failed to start.";
    } else if (evt.status === "warning") {
      voiceWarning.value = evt.detail || null;
    } else if (evt.status === "loading") {
      // Empty detail = all models done loading; clear the indicator
      voiceLoadingDetail.value = evt.detail || null;
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
    currentScene.value = null;
    currentAccent.value = null;
    voiceReady.value = false;
    voiceError.value = null;
    voiceWarning.value = null;
    voiceLoadingDetail.value = null;
  }

  return {
    sessionId, elcor, state, events, latest,
    currentSpeaker, currentTranscript, currentQueue, currentEnviron,
    currentScene, currentAccent,
    voiceReady, voiceError, voiceWarning, voiceLoadingDetail,
    startSession, endSession, pushEvent,
    updateSpeaker, updateTranscript, updateQueue, updateService,
    updateScene, updateAccent,
    reset,
  };
});
