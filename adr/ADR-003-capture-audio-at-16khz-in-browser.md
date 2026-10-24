# ADR-003: Capture audio at 16 kHz in the browser

Date: 2026-10-24
Status: Accepted

## Context

Whistle takes 16 kHz mono audio. The browser's microphone runs at 48 kHz on most machines. The first version captured at the device rate and resampled in JavaScript with linear interpolation. The user reported a wrong transcript. Linear interpolation without a low-pass filter aliases speech above 8 kHz. Consonants such as s, f and t suffer most.

Options checked:

- `MediaRecorder`: outputs WebM or MP4 (Opus or AAC). The server would need a decoder such as ffmpeg. Adds a dependency.
- JavaScript resampling with a filter: more code, more places to get wrong.
- `new AudioContext({ sampleRate: 16000 })`: the browser resamples with its own filter.

## Decision

- Create the `AudioContext` at 16 kHz. Browsers that refuse the rate fall back to the device rate, and the JavaScript resampler still runs.
- Capture samples in an `AudioWorkletProcessor` (`recorder-worklet.js`). Do not use the deprecated `ScriptProcessorNode`.
- Encode the WAV in the browser: 16-bit PCM, mono, 16 kHz.
- The worklet output goes to a zero-gain node. The node must reach the destination for the browser to run it. The speaker stays silent.

## Consequences

- Good: No extra server decoder. Browser filters the rate change. Output format matches what Whistle expects.
- Bad: Relies on `AudioContext` rate support. Tested in headless Chrome only. Safari is not tested. Browsers that refuse the rate use the fallback path.
- Bad: The JavaScript resampler is still used on fallback and has the aliasing issue above.
- Revisit trigger: A browser that drops the `sampleRate` option. Or Whistle accepts another input format.
