/**
 * useAudioCapture — browser mic → WebSocket PCM pipeline.
 *
 * Navigation v0.1.x: sends binary PCM chunks to /session/{id}/audio.
 * The backend acknowledges each chunk. Real inference wiring is v0.2.x.
 *
 * Requires: AudioWorklet support (all modern browsers).
 */
import { ref } from "vue";

export function useAudioCapture() {
  const capturing = ref(false);
  let ctx: AudioContext | null = null;
  let ws: WebSocket | null = null;
  let source: MediaStreamAudioSourceNode | null = null;
  let stream: MediaStream | null = null;

  async function start(sessionId: string) {
    if (capturing.value) return;

    stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
    ctx = new AudioContext({ sampleRate: 16000 });

    await ctx.audioWorklet.addModule("/audio-processor.js");

    source = ctx.createMediaStreamSource(stream);
    const processor = new AudioWorkletNode(ctx, "pcm-processor");

    const wsUrl = `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/session/${sessionId}/audio`;
    ws = new WebSocket(wsUrl);

    ws.binaryType = "arraybuffer";
    ws.onopen = () => { capturing.value = true; };
    ws.onclose = () => { capturing.value = false; };

    processor.port.onmessage = (e: MessageEvent<ArrayBuffer>) => {
      if (ws?.readyState === WebSocket.OPEN) {
        ws.send(e.data);
      }
    };

    source.connect(processor);
    processor.connect(ctx.destination);
  }

  async function stop() {
    source?.disconnect();
    await ctx?.close();
    ws?.close();
    stream?.getTracks().forEach((t) => t.stop());

    ctx = null;
    ws = null;
    source = null;
    stream = null;
    capturing.value = false;
  }

  return { start, stop, capturing };
}
