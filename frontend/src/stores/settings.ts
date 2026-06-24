// stores/settings.ts — persistent user preferences, survives page reload via localStorage.
//
// All settings here apply to the NEXT session start. Mid-session changes take
// effect on the following session (the ComposeBar shows current-session values
// as read-only badges while a session is running).

import { defineStore } from "pinia";
import { ref, watch } from "vue";

const STORAGE_KEY = "linnet:settings:v1";

interface PersistedSettings {
  windowMs: number;
  transcribeLang: string;
  elcor: boolean;
  numSpeakers: number; // 0 = auto-detect
  threadView: boolean; // dev-only: preview v0.2.x thread UI (toggled from DevPanel)
}

const DEFAULTS: PersistedSettings = {
  windowMs: 1000,
  transcribeLang: "",
  elcor: false,
  numSpeakers: 0,
  threadView: false,
};

function loadFromStorage(): PersistedSettings {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      // Merge with defaults so new fields added after initial save get their defaults
      return { ...DEFAULTS, ...(JSON.parse(raw) as Partial<PersistedSettings>) };
    }
  } catch {
    // corrupt or missing — fall through to defaults
  }
  return { ...DEFAULTS };
}

export const useSettingsStore = defineStore("settings", () => {
  const saved = loadFromStorage();

  const windowMs = ref<number>(saved.windowMs);
  const transcribeLang = ref<string>(saved.transcribeLang);
  const elcor = ref<boolean>(saved.elcor);
  // 0 = auto; 1–8 = fixed count passed to pyannote as min_speakers=max_speakers
  const numSpeakers = ref<number>(saved.numSpeakers);
  // Dev-only: show v0.2.x thread UI instead of v0.1.x NowPanel/HistoryStrip.
  // Toggled from DevPanel; not exposed in user-facing settings.
  const threadView = ref<boolean>(saved.threadView);

  // Persist to localStorage whenever any setting changes
  watch(
    [windowMs, transcribeLang, elcor, numSpeakers, threadView],
    () => {
      localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({
          windowMs: windowMs.value,
          transcribeLang: transcribeLang.value,
          elcor: elcor.value,
          numSpeakers: numSpeakers.value,
          threadView: threadView.value,
        }),
      );
    },
    { deep: false },
  );

  return { windowMs, transcribeLang, elcor, numSpeakers, threadView };
});
