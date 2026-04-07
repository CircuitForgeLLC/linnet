/**
 * useToneStream — manages the SSE connection for a session's tone-event stream.
 *
 * Usage:
 *   const { connect, disconnect, connected } = useToneStream();
 *   connect(sessionId);   // opens EventSource
 *   disconnect();         // closes it
 */
import { ref, onUnmounted } from "vue";
import { useSessionStore } from "../stores/session";

export function useToneStream() {
  const connected = ref(false);
  let source: EventSource | null = null;
  const store = useSessionStore();

  function connect(sessionId: string) {
    if (source) disconnect();
    source = new EventSource(`/session/${sessionId}/stream`);

    source.addEventListener("tone-event", (e: MessageEvent) => {
      try {
        const evt = JSON.parse(e.data);
        store.pushEvent(evt);
      } catch {
        // malformed frame — ignore
      }
    });

    source.onopen = () => { connected.value = true; };
    source.onerror = () => { connected.value = false; };
  }

  function disconnect() {
    source?.close();
    source = null;
    connected.value = false;
  }

  onUnmounted(disconnect);

  return { connect, disconnect, connected };
}
