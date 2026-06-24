<!-- ComposeBar.vue — session start/stop controls with audio settings -->
<template>
  <div class="compose-bar">

    <!-- ── Pre-session: settings + start ───────────────────────────── -->
    <template v-if="store.state === 'idle' || store.state === 'stopped'">

      <transition name="settings-slide">
        <div v-if="showSettings" class="settings-panel">
          <label class="settings-item">
            <span class="settings-label">Window</span>
            <select v-model.number="settings.windowMs" class="settings-select">
              <option :value="500">500 ms</option>
              <option :value="1000">1 s (default)</option>
              <option :value="2000">2 s</option>
              <option :value="3000">3 s</option>
            </select>
          </label>

          <label class="settings-item">
            <span class="settings-label">Language</span>
            <select v-model="settings.transcribeLang" class="settings-select">
              <option value="">Auto-detect</option>
              <option value="en">English</option>
              <option value="es">Spanish</option>
              <option value="fr">French</option>
              <option value="de">German</option>
              <option value="pt">Portuguese</option>
              <option value="it">Italian</option>
              <option value="ja">Japanese</option>
              <option value="ko">Korean</option>
              <option value="zh">Chinese</option>
            </select>
          </label>

          <label class="settings-item">
            <span class="settings-label">Speakers</span>
            <select v-model.number="settings.numSpeakers" class="settings-select">
              <option :value="0">Auto-detect</option>
              <option :value="1">1 speaker</option>
              <option :value="2">2 speakers</option>
              <option :value="3">3 speakers</option>
              <option :value="4">4 speakers</option>
            </select>
          </label>

          <label class="settings-item settings-checkbox">
            <input type="checkbox" v-model="settings.elcor" />
            <span class="settings-label">Elcor prefix</span>
          </label>
        </div>
      </transition>

      <div class="compose-row">
        <button
          class="btn-icon"
          :class="{ active: showSettings }"
          @click="showSettings = !showSettings"
          :title="showSettings ? 'Hide settings' : 'Audio settings'"
          aria-label="Toggle audio settings"
        >⚙</button>
        <button class="btn-start" @click="handleStart" :disabled="starting">
          {{ starting ? "Starting…" : "Start session" }}
        </button>
      </div>
    </template>

    <!-- ── Active session ───────────────────────────────────────────── -->
    <template v-else>
      <div class="session-info">
        <span class="session-dot" :class="{ active: store.state === 'running' }" />
        <span class="session-id">{{ store.sessionId?.slice(0, 8) }}…</span>
      </div>

      <!-- Active settings badges -->
      <span class="session-badge">{{ settings.windowMs }}ms</span>
      <span v-if="settings.transcribeLang" class="session-badge">{{ settings.transcribeLang }}</span>
      <span v-if="settings.numSpeakers > 0" class="session-badge">{{ settings.numSpeakers }}spk</span>
      <span v-if="settings.elcor" class="session-badge">elcor</span>

      <button
        class="btn-mic"
        :class="{ active: capturing, loading: !store.voiceReady && !store.voiceError }"
        :disabled="!store.voiceReady && !store.voiceError"
        @click="handleMicToggle"
        :aria-label="capturing ? 'Stop microphone' : store.voiceReady ? 'Start microphone' : 'Voice service loading'"
        :title="store.voiceError ?? undefined"
      >
        <span v-if="!store.voiceReady && !store.voiceError" class="mic-spinner" aria-hidden="true" />
        {{ capturing ? "Mic on" : store.voiceReady ? "Mic off" : store.voiceError ? "Voice error" : "Loading…" }}
      </button>

      <button class="btn-stop" @click="handleStop">End session</button>
    </template>

    <p v-if="expired" class="compose-notice">
      Session timed out after inactivity. Start a new one to continue.
    </p>
    <p v-else-if="store.voiceError" class="compose-error">{{ store.voiceError }}</p>
    <p v-else-if="error" class="compose-error">{{ error }}</p>
    <p v-if="store.voiceWarning" class="compose-warning">{{ store.voiceWarning }}</p>
    <p v-if="store.voiceLoadingDetail" class="compose-loading">
      <span class="compose-loading-spinner" aria-hidden="true" />{{ store.voiceLoadingDetail }}
    </p>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { useSessionStore } from "../stores/session";
import { useSettingsStore } from "../stores/settings";
import { useToneStream } from "../composables/useToneStream";
import { useAudioCapture } from "../composables/useAudioCapture";

const store = useSessionStore();
const settings = useSettingsStore();
const { connect, disconnect, expired } = useToneStream();
const { start: startMic, stop: stopMic, capturing } = useAudioCapture();

const starting = ref(false);
const error = ref<string | null>(null);
const showSettings = ref(false);

async function handleStart() {
  starting.value = true;
  error.value = null;
  try {
    await store.startSession({
      elcor: settings.elcor,
      windowMs: settings.windowMs,
      transcribeLang: settings.transcribeLang,
      numSpeakers: settings.numSpeakers,
    });
    connect(store.sessionId!);
    showSettings.value = false; // collapse settings once running
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : "Failed to start session";
  } finally {
    starting.value = false;
  }
}

async function handleStop() {
  if (capturing.value) stopMic();
  disconnect();
  await store.endSession();
}

async function handleMicToggle() {
  error.value = null;
  try {
    if (capturing.value) {
      stopMic();
    } else {
      await startMic(store.sessionId!);
    }
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : "Mic access failed";
  }
}
</script>

<script lang="ts">
export default { name: "ComposeBar" };
</script>

<style scoped>
.compose-bar {
  display: flex;
  flex-direction: column;
  background: var(--color-surface, #1a1d27);
  border-top: 1px solid var(--color-border, #2a2d3a);
}

/* ── Settings panel ──────────────────────────────────────────────── */
.settings-panel {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem 1.25rem;
  padding: 0.75rem 1.5rem;
  border-bottom: 1px solid var(--color-border, #2a2d3a);
  background: color-mix(in srgb, var(--color-surface, #1a1d27) 80%, black);
}

.settings-item {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  cursor: pointer;
}

.settings-checkbox {
  user-select: none;
}

.settings-label {
  font-size: 0.72rem;
  color: var(--color-muted, #6b7280);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.settings-select {
  font-size: 0.8rem;
  color: var(--color-text, #e2e8f0);
  background: var(--color-bg, #0f1117);
  border: 1px solid var(--color-border, #2a2d3a);
  border-radius: 0.375rem;
  padding: 0.2rem 0.4rem;
  cursor: pointer;
  outline-offset: 2px;
}

.settings-select:focus {
  outline: 2px solid var(--color-accent, #7c6af7);
}

/* Slide transition */
.settings-slide-enter-active,
.settings-slide-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}
.settings-slide-enter-from,
.settings-slide-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

/* ── Bottom compose row ──────────────────────────────────────────── */
.compose-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.875rem 1.5rem;
  flex-wrap: wrap;
}

/* Active-session row reuses compose-bar padding directly */
.compose-bar > .session-info,
.compose-bar > .btn-mic,
.compose-bar > .btn-stop,
.compose-bar > .session-badge {
  margin: 0;
}

/* Inline flex for the running-session controls */
.compose-bar > template,
.compose-bar {
  /* children from v-else template land here directly */
}

/* Running-session controls sit in a flex row via compose-bar */
:deep(.compose-bar) { }  /* noop, just for clarity */

.compose-bar > *:not(.settings-panel):not(.compose-row):not(p) {
  /* session-running items: give them the compose padding */
  margin-inline: 0;
}

/* Hack: running-session template children need horizontal layout */
.session-info ~ .session-badge,
.session-info ~ .btn-mic,
.session-info ~ .btn-stop {
  /* siblings of session-info are in the same flex flow */
}

/* Override: when session is running the compose-bar itself is the flex row */
.compose-bar:has(.session-info) {
  flex-direction: row;
  align-items: center;
  gap: 0.75rem;
  padding: 0.875rem 1.5rem;
  flex-wrap: wrap;
}

/* ── Buttons ─────────────────────────────────────────────────────── */
.btn-start,
.btn-stop {
  padding: 0.5rem 1.25rem;
  border-radius: 0.5rem;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  border: none;
  transition: opacity 0.2s;
}
.btn-start { background: var(--color-accent, #7c6af7); color: #fff; }
.btn-stop  { background: #374151; color: #e2e8f0; }
.btn-start:disabled { opacity: 0.6; cursor: not-allowed; }

.btn-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2rem;
  height: 2rem;
  border-radius: 0.375rem;
  border: 1px solid var(--color-border, #2a2d3a);
  background: transparent;
  color: var(--color-muted, #6b7280);
  font-size: 0.9rem;
  cursor: pointer;
  transition: color 0.15s, border-color 0.15s, background 0.15s;
  flex-shrink: 0;
}
.btn-icon:hover   { color: var(--color-text, #e2e8f0); border-color: var(--color-muted, #6b7280); }
.btn-icon.active  { color: var(--color-accent, #7c6af7); border-color: var(--color-accent, #7c6af7); background: color-mix(in srgb, var(--color-accent, #7c6af7) 12%, transparent); }

/* ── Session info + badges ───────────────────────────────────────── */
.session-info {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.75rem;
  color: var(--color-muted, #6b7280);
  font-family: var(--font-mono, monospace);
}

.session-dot {
  width: 0.5rem;
  height: 0.5rem;
  border-radius: 50%;
  background: #374151;
}
.session-dot.active {
  background: #34d399;
  box-shadow: 0 0 6px #34d39966;
}

.session-badge {
  font-size: 0.68rem;
  font-family: var(--font-mono, monospace);
  color: var(--color-muted, #6b7280);
  background: color-mix(in srgb, var(--color-border, #2a2d3a) 60%, transparent);
  border: 1px solid var(--color-border, #2a2d3a);
  border-radius: 0.25rem;
  padding: 0.1rem 0.35rem;
}

/* ── Mic button ──────────────────────────────────────────────────── */
.btn-mic {
  padding: 0.5rem 1rem;
  border-radius: 0.5rem;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  border: 1px solid var(--color-border, #2a2d3a);
  background: transparent;
  color: var(--color-muted, #6b7280);
  transition: background 0.15s, color 0.15s, border-color 0.15s;
}
.btn-mic.active {
  background: #dc262622;
  border-color: #dc2626;
  color: #dc2626;
}
.btn-mic.loading {
  opacity: 0.6;
  cursor: not-allowed;
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
}
.btn-mic:disabled { cursor: not-allowed; }

@keyframes spin { to { transform: rotate(360deg); } }
.mic-spinner {
  display: inline-block;
  width: 0.7rem;
  height: 0.7rem;
  border: 2px solid var(--color-border, #2a2d3a);
  border-top-color: var(--color-muted, #6b7280);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  flex-shrink: 0;
}

/* ── Notices ─────────────────────────────────────────────────────── */
.compose-error {
  width: 100%;
  font-size: 0.75rem;
  color: #ef4444;
  margin: 0;
  padding: 0 1.5rem 0.75rem;
}

.compose-notice {
  width: 100%;
  font-size: 0.75rem;
  color: var(--color-muted, #6b7280);
  margin: 0;
  padding: 0 1.5rem 0.75rem;
}

.compose-warning {
  width: 100%;
  font-size: 0.72rem;
  color: #f59e0b;
  margin: 0;
  padding: 0.4rem 1.5rem 0.5rem;
  border-top: 1px solid color-mix(in srgb, #f59e0b 20%, transparent);
  background: color-mix(in srgb, #f59e0b 5%, transparent);
  line-height: 1.5;
}

.compose-loading {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.7rem;
  font-family: var(--font-mono, monospace);
  color: var(--color-muted, #6b7280);
  margin: 0;
  padding: 0.3rem 1.5rem 0.4rem;
  border-top: 1px solid var(--color-border, #2a2d3a);
}

.compose-loading-spinner {
  display: inline-block;
  width: 0.55rem;
  height: 0.55rem;
  border: 1.5px solid var(--color-border, #2a2d3a);
  border-top-color: var(--color-muted, #6b7280);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  flex-shrink: 0;
}
</style>
