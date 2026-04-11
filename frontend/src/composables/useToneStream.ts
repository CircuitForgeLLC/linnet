/**
 * useToneStream — SSE connection + wake lock + visibility reconnect.
 *
 * On page hide (screen lock, tab switch): closes EventSource without ending
 * the session. The backend reaper gives the session a 90s grace window.
 *
 * On page show: re-acquires the wake lock, checks whether the session is
 * still alive on the server, then either reconnects SSE or surfaces an
 * "expired" flag so the UI can prompt the user to start a new session.
 */
import { ref, onUnmounted } from "vue";
import {
  useSessionStore,
  type SpeakerEvent,
  type TranscriptEvent,
  type QueueEvent,
} from "../stores/session";
import { useWakeLock } from "./useWakeLock";

export function useToneStream() {
  const connected = ref(false);
  const expired = ref(false);    // true when the session was reaped while hidden
  let source: EventSource | null = null;
  let activeSessionId: string | null = null;
  const store = useSessionStore();
  const wakeLock = useWakeLock();

  // ── SSE wiring ──────────────────────────────────────────────────────────────

  function _attachListeners() {
    if (!source) return;

    source.addEventListener("tone-event", (e: MessageEvent) => {
      try { store.pushEvent(JSON.parse(e.data)); } catch { /* malformed */ }
    });
    source.addEventListener("speaker-event", (e: MessageEvent) => {
      try { store.updateSpeaker(JSON.parse(e.data) as SpeakerEvent); } catch { /* */ }
    });
    source.addEventListener("transcript-event", (e: MessageEvent) => {
      try { store.updateTranscript(JSON.parse(e.data) as TranscriptEvent); } catch { /* */ }
    });
    source.addEventListener("queue-event", (e: MessageEvent) => {
      try { store.updateQueue(JSON.parse(e.data) as QueueEvent); } catch { /* */ }
    });
    source.addEventListener("environ-event", (e: MessageEvent) => {
      try { store.updateQueue(JSON.parse(e.data) as QueueEvent); } catch { /* */ }
    });

    source.onopen = () => { connected.value = true; };
    source.onerror = () => { connected.value = false; };
  }

  function connect(sessionId: string) {
    if (source) _closeSource();
    activeSessionId = sessionId;
    expired.value = false;
    const apiBase = import.meta.env.VITE_API_BASE ?? "";
    source = new EventSource(`${apiBase}/session/${sessionId}/stream`);
    _attachListeners();
    wakeLock.acquire();
  }

  function _closeSource() {
    source?.close();
    source = null;
    connected.value = false;
  }

  function disconnect() {
    _closeSource();
    activeSessionId = null;
    wakeLock.release();
  }

  // ── Visibility handling ─────────────────────────────────────────────────────

  async function _handleVisibilityChange() {
    if (document.visibilityState === "hidden") {
      // Close the SSE connection without ending the backend session.
      // The reaper gives us SESSION_IDLE_TTL_S (default 90s) before cleanup.
      _closeSource();
      return;
    }

    // Page became visible again — check if session survived the absence.
    if (!activeSessionId) return;

    const apiBase = import.meta.env.VITE_API_BASE ?? "";
    try {
      const resp = await fetch(`${apiBase}/session/${activeSessionId}`);
      if (resp.ok) {
        // Session still alive — reconnect SSE and wake lock
        const apiBase2 = import.meta.env.VITE_API_BASE ?? "";
        source = new EventSource(`${apiBase2}/session/${activeSessionId}/stream`);
        _attachListeners();
        wakeLock.acquire();
      } else {
        // Session was reaped (404) or errored — surface to UI
        expired.value = true;
        store.reset();
        activeSessionId = null;
      }
    } catch {
      // Network error on return — don't immediately expire, user may be offline
      // briefly. They can retry manually.
    }
  }

  document.addEventListener("visibilitychange", _handleVisibilityChange);

  onUnmounted(() => {
    disconnect();
    document.removeEventListener("visibilitychange", _handleVisibilityChange);
  });

  return { connect, disconnect, connected, expired };
}
