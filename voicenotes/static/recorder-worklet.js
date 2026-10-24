// Runs on the audio thread. Copies each block of mono samples to the page.
class CaptureProcessor extends AudioWorkletProcessor {
  process(inputs) {
    const channel = inputs[0] && inputs[0][0];
    if (channel) {
      this.port.postMessage(channel.slice(0));
    }
    return true;
  }
}

registerProcessor("pcm-capture", CaptureProcessor);
