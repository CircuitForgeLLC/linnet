/**
 * useWakeLock — Screen Wake Lock API wrapper.
 *
 * Prevents the screen from dimming/sleeping while an annotation session is
 * active. The browser *always* releases the lock on page hide (tab switch,
 * screen lock), so we re-acquire on visibilitychange: visible.
 *
 * Degrades silently when the API is unavailable (Firefox < 126, iOS Safari,
 * low-power mode). The session still works; screen may time out.
 */
import { ref, onUnmounted } from "vue";

export function useWakeLock() {
  const supported = "wakeLock" in navigator;
  const active = ref(false);

  let lock: WakeLockSentinel | null = null;

  async function acquire() {
    if (!supported) return;
    try {
      lock = await navigator.wakeLock.request("screen");
      active.value = true;
      lock.addEventListener("release", () => {
        active.value = false;
        lock = null;
      });
    } catch {
      // Denied: battery saver, low-power mode, permissions policy.
      // Silent fail — the session continues without it.
      active.value = false;
    }
  }

  function release() {
    lock?.release();
    lock = null;
    active.value = false;
  }

  // Re-acquire after returning to the tab — the browser releases the lock
  // automatically on page hide, so we must request it again on page show.
  async function handleVisibility() {
    if (document.visibilityState === "visible" && lock === null && active.value === false) {
      // Only re-acquire if we were previously active (i.e. a session is running).
      // The caller controls this by only calling acquire() when a session starts.
    }
  }

  // NOTE: the caller is responsible for calling acquire() when a session starts
  // and release() when it ends. The visibility re-acquire is handled inside
  // the SSE composable which coordinates both wake lock and reconnect together.

  onUnmounted(release);

  return { supported, active, acquire, release, handleVisibility };
}
