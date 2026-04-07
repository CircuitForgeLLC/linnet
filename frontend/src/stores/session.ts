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

export const useSessionStore = defineStore("session", () => {
  const sessionId = ref<string | null>(null);
  const elcor = ref(false);
  const state = ref<"idle" | "running" | "stopped">("idle");
  const events = ref<ToneEvent[]>([]);
  const latest = computed(() => events.value.at(-1) ?? null);

  async function startSession(withElcor = false) {
    const resp = await fetch("/session/start", {
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
    await fetch(`/session/${sessionId.value}/end`, { method: "DELETE" });
    state.value = "stopped";
  }

  function pushEvent(evt: ToneEvent) {
    events.value.push(evt);
    // Cap history at 200 in the store (history endpoint handles server-side cap)
    if (events.value.length > 200) events.value.shift();
  }

  function reset() {
    sessionId.value = null;
    state.value = "idle";
    events.value = [];
    elcor.value = false;
  }

  return { sessionId, elcor, state, events, latest, startSession, endSession, pushEvent, reset };
});
