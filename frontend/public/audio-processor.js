/**
 * audio-processor.js — AudioWorkletProcessor for mic → PCM pipeline.
 *
 * Runs in the AudioWorklet thread. Converts Float32 samples to Int16 PCM
 * and posts each 128-sample block (8ms at 16kHz) as an ArrayBuffer to
 * the main thread.
 *
 * The main thread accumulates these into ~100ms chunks before sending
 * over the WebSocket.
 */

const CHUNK_SAMPLES = 1600; // 100ms at 16kHz

class PcmProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this._buffer = new Int16Array(CHUNK_SAMPLES);
    this._offset = 0;
  }

  process(inputs) {
    const input = inputs[0];
    if (!input || !input[0]) return true;

    const samples = input[0]; // Float32Array, 128 samples
    for (let i = 0; i < samples.length; i++) {
      // Clamp and convert to Int16
      const clamped = Math.max(-1, Math.min(1, samples[i]));
      this._buffer[this._offset++] = clamped < 0 ? clamped * 0x8000 : clamped * 0x7fff;

      if (this._offset >= CHUNK_SAMPLES) {
        // Copy and post — avoid transferring the live buffer
        const chunk = new Int16Array(CHUNK_SAMPLES);
        chunk.set(this._buffer);
        this.port.postMessage(chunk.buffer, [chunk.buffer]);
        this._buffer = new Int16Array(CHUNK_SAMPLES);
        this._offset = 0;
      }
    }
    return true;
  }
}

registerProcessor("pcm-processor", PcmProcessor);
