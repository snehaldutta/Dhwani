// Captures microphone audio and returns 16 kHz mono 16-bit WAV bytes.
// The browser sends the clip to the local server. Nothing is saved on disk.

const TARGET_RATE = 16000;

export async function startRecording() {
  const stream = await navigator.mediaDevices.getUserMedia({
    audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true },
  });
  // Ask the browser for 16 kHz. Its resampler filters before it drops samples.
  // Plain interpolation in JavaScript aliases speech above 8 kHz.
  const context = new AudioContext({ sampleRate: TARGET_RATE });
  await context.audioWorklet.addModule("recorder-worklet.js");

  const source = context.createMediaStreamSource(stream);
  const capture = new AudioWorkletNode(context, "pcm-capture");
  const silence = context.createGain();
  silence.gain.value = 0; // The worklet must reach the destination to run. Output stays silent.
  const chunks = [];
  capture.port.onmessage = (event) => chunks.push(event.data);
  source.connect(capture);
  capture.connect(silence);
  silence.connect(context.destination);

  return {
    async stop() {
      capture.port.onmessage = null;
      source.disconnect();
      capture.disconnect();
      stream.getTracks().forEach((track) => track.stop());
      const rate = context.sampleRate;
      await context.close();
      const samples = resample(concat(chunks), rate, TARGET_RATE);
      return encodeWav(samples, TARGET_RATE);
    },
  };
}

function concat(chunks) {
  const total = chunks.reduce((sum, chunk) => sum + chunk.length, 0);
  const output = new Float32Array(total);
  let offset = 0;
  for (const chunk of chunks) {
    output.set(chunk, offset);
    offset += chunk.length;
  }
  return output;
}

// Linear interpolation. Adequate for speech, not for music.
function resample(input, fromRate, toRate) {
  if (fromRate === toRate) {
    return input;
  }
  const ratio = fromRate / toRate;
  const length = Math.floor(input.length / ratio);
  const output = new Float32Array(length);
  for (let i = 0; i < length; i++) {
    const position = i * ratio;
    const index = Math.floor(position);
    const fraction = position - index;
    const next = input[index + 1] ?? input[index];
    output[i] = input[index] * (1 - fraction) + next * fraction;
  }
  return output;
}

function encodeWav(samples, sampleRate) {
  const buffer = new ArrayBuffer(44 + samples.length * 2);
  const view = new DataView(buffer);
  writeText(view, 0, "RIFF");
  view.setUint32(4, 36 + samples.length * 2, true);
  writeText(view, 8, "WAVE");
  writeText(view, 12, "fmt ");
  view.setUint32(16, 16, true); // PCM format chunk size
  view.setUint16(20, 1, true); // PCM
  view.setUint16(22, 1, true); // mono
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true); // bytes per second
  view.setUint16(32, 2, true); // bytes per frame
  view.setUint16(34, 16, true); // bits per sample
  writeText(view, 36, "data");
  view.setUint32(40, samples.length * 2, true);
  for (let i = 0; i < samples.length; i++) {
    const clamped = Math.max(-1, Math.min(1, samples[i]));
    view.setInt16(44 + i * 2, clamped < 0 ? clamped * 0x8000 : clamped * 0x7fff, true);
  }
  return new Blob([buffer], { type: "audio/wav" });
}

function writeText(view, offset, text) {
  for (let i = 0; i < text.length; i++) {
    view.setUint8(offset + i, text.charCodeAt(i));
  }
}
