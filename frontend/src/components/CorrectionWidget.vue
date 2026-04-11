<template>
  <div class="correction-widget" :class="{ 'correction-widget--expanded': expanded }">
    <!-- Idle: thumbs row -->
    <div v-if="state === 'idle'" class="rating-row">
      <span class="rating-label">Was this annotation accurate?</span>
      <button
        type="button"
        class="thumb-btn thumb-btn--up"
        aria-label="Accurate"
        @click="rate('up')"
      >👍</button>
      <button
        type="button"
        class="thumb-btn thumb-btn--down"
        aria-label="Inaccurate — submit correction"
        @click="rate('down')"
      >👎</button>
    </div>

    <!-- Thumbs-down: correction form -->
    <form v-else-if="state === 'correcting'" class="correction-form" @submit.prevent="submit">
      <label class="field-label" for="corrected-output">
        What should the annotation say?
      </label>
      <textarea
        id="corrected-output"
        v-model="correctedOutput"
        class="correction-textarea"
        rows="3"
        placeholder="e.g. [RELUCTANTLY] [MASKING_STRESS] I'll have it done by end of day."
        required
        autofocus
      />
      <label class="optin-label">
        <input v-model="optedIn" type="checkbox" class="optin-check" />
        Share this correction anonymously to improve the model
      </label>
      <div class="form-actions">
        <button type="button" class="btn-cancel" @click="cancel">Cancel</button>
        <button
          type="submit"
          class="btn-submit"
          :disabled="submitting || !correctedOutput.trim()"
        >
          {{ submitting ? 'Saving…' : 'Submit correction' }}
        </button>
      </div>
      <p v-if="error" class="correction-error" role="alert">{{ error }}</p>
    </form>

    <!-- Thumbs-up: optional praise form -->
    <form v-else-if="state === 'praising'" class="correction-form" @submit.prevent="submitPraise">
      <label class="field-label" for="praise-input">
        What worked well? <span class="field-optional">(optional)</span>
      </label>
      <textarea
        id="praise-input"
        v-model="praiseText"
        class="correction-textarea"
        rows="2"
        placeholder="e.g. Caught the sarcasm without over-labeling it."
        autofocus
      />
      <div class="form-actions">
        <button type="button" class="btn-cancel" @click="submitPraise">Skip</button>
        <button type="submit" class="btn-submit" :disabled="submitting">
          {{ submitting ? 'Saving…' : 'Submit' }}
        </button>
      </div>
      <p v-if="error" class="correction-error" role="alert">{{ error }}</p>
    </form>

    <!-- Thumbs-up submitted -->
    <div v-else-if="state === 'done-up'" class="done-msg done-msg--up">
      ✓ Thanks — glad that was helpful.
    </div>

    <!-- Correction submitted -->
    <div v-else-if="state === 'done-down'" class="done-msg done-msg--down">
      ✓ Correction saved{{ optedIn ? ' and flagged for training' : '' }}.
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

const props = defineProps<{
  itemId?: string
  inputText: string
  originalOutput: string
  correctionType?: string
  apiPath?: string
  context?: Record<string, unknown>
}>()

type State = 'idle' | 'praising' | 'correcting' | 'done-up' | 'done-down'

const state = ref<State>('idle')
const correctedOutput = ref('')
const praiseText = ref('')
const optedIn = ref(false)
const submitting = ref(false)
const error = ref<string | null>(null)

const expanded = computed(() => state.value === 'correcting' || state.value === 'praising')

const apiBase = import.meta.env.VITE_API_BASE ?? "";
const endpoint = computed(() => `${apiBase}${props.apiPath ?? '/corrections'}`)

function rate(rating: 'up' | 'down') {
  if (rating === 'up') {
    state.value = 'praising'
  } else {
    state.value = 'correcting'
  }
}

function cancel() {
  state.value = 'idle'
  correctedOutput.value = ''
  praiseText.value = ''
  error.value = null
}

async function submit() {
  await submitRating('down', correctedOutput.value.trim())
}

async function submitPraise() {
  const praise = praiseText.value.trim()
  const context = { ...props.context ?? {}, ...(praise ? { praise } : {}) }
  await submitRating('up', '', context)
}

async function submitRating(
  rating: 'up' | 'down',
  correction: string,
  contextOverride?: Record<string, unknown>,
) {
  submitting.value = true
  error.value = null
  // Thumbs-up rows contain no user text — auto-consent so they export for training.
  const effectiveOptIn = rating === 'up' ? true : optedIn.value
  const context = contextOverride ?? props.context ?? {}
  try {
    const res = await fetch(endpoint.value, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        item_id: props.itemId ?? '',
        product: 'linnet',
        correction_type: props.correctionType ?? 'annotation',
        input_text: props.inputText,
        original_output: props.originalOutput,
        corrected_output: correction,
        rating,
        context,
        opted_in: effectiveOptIn,
      }),
    })
    if (!res.ok) {
      const body = await res.json().catch(() => ({}))
      throw new Error(body?.detail ?? `HTTP ${res.status}`)
    }
    state.value = rating === 'up' ? 'done-up' : 'done-down'
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Something went wrong — please try again.'
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.correction-widget {
  display: flex;
  flex-direction: column;
  gap: var(--space-2, 0.5rem);
  padding: var(--space-2, 0.5rem) var(--space-3, 0.75rem);
  border-top: 1px solid var(--color-border, #2a2d3a);
  font-size: 0.8rem;
  color: var(--color-muted, #6b7280);
  transition: padding 0.15s ease;
}

.correction-widget--expanded {
  padding: var(--space-3, 0.75rem);
}

/* Rating row */
.rating-row {
  display: flex;
  align-items: center;
  gap: var(--space-2, 0.5rem);
}

.rating-label {
  flex: 1;
  font-size: 0.75rem;
  color: var(--color-muted, #6b7280);
}

.thumb-btn {
  background: none;
  border: 1px solid var(--color-border, #2a2d3a);
  border-radius: var(--radius-sm, 4px);
  padding: 0.2rem 0.45rem;
  font-size: 1rem;
  cursor: pointer;
  line-height: 1;
  transition: background 0.1s ease, border-color 0.1s ease;
}

.thumb-btn:hover {
  background: var(--color-surface, #1a1d27);
  border-color: var(--color-accent, #7c6af7);
}

/* Correction form */
.correction-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-2, 0.5rem);
}

.field-label {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--color-text, #e2e8f0);
}

.field-optional {
  font-weight: 400;
  color: var(--color-muted, #6b7280);
}

.correction-textarea {
  width: 100%;
  resize: vertical;
  background: var(--color-bg, #0f1117);
  border: 1px solid var(--color-border, #2a2d3a);
  border-radius: var(--radius-sm, 4px);
  color: var(--color-text, #e2e8f0);
  font-family: var(--font-mono, monospace);
  font-size: 0.78rem;
  padding: var(--space-2, 0.5rem);
  box-sizing: border-box;
}

.correction-textarea:focus {
  outline: none;
  border-color: var(--color-accent, #7c6af7);
}

.optin-label {
  display: flex;
  align-items: center;
  gap: var(--space-2, 0.5rem);
  font-size: 0.72rem;
  color: var(--color-muted, #6b7280);
  cursor: pointer;
}

.optin-check {
  accent-color: var(--color-accent, #7c6af7);
}

.form-actions {
  display: flex;
  gap: var(--space-2, 0.5rem);
  justify-content: flex-end;
}

.btn-cancel {
  background: none;
  border: 1px solid var(--color-border, #2a2d3a);
  border-radius: var(--radius-sm, 4px);
  color: var(--color-muted, #6b7280);
  font-size: 0.78rem;
  padding: var(--space-1, 0.25rem) var(--space-3, 0.75rem);
  cursor: pointer;
}

.btn-submit {
  background: var(--color-accent, #7c6af7);
  border: none;
  border-radius: var(--radius-sm, 4px);
  color: #fff;
  font-size: 0.78rem;
  font-weight: 600;
  padding: var(--space-1, 0.25rem) var(--space-3, 0.75rem);
  cursor: pointer;
  transition: opacity 0.1s ease;
}

.btn-submit:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.correction-error {
  font-size: 0.72rem;
  color: var(--color-error, #dc2626);
  margin: 0;
}

/* Done states */
.done-msg {
  font-size: 0.75rem;
  font-weight: 600;
}

.done-msg--up   { color: var(--color-success, #16a34a); }
.done-msg--down { color: var(--color-accent,  #7c6af7); }
</style>
