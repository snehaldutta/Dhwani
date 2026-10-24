import io
import logging
import os
import sys
import threading
import wave
from array import array
from typing import Protocol

# The Whistle package sends usage events by default and checks Hugging Face on
# load. Turn off the events. Keep Hugging Face offline unless the user sets
# HF_HUB_OFFLINE=0 for the one-time model download. Audio and notes stay local.
os.environ["NEEDLE_TELEMETRY"] = "0"
os.environ["DO_NOT_TRACK"] = "1"
os.environ.setdefault("HF_HUB_OFFLINE", "1")

logger = logging.getLogger("voicenotes")

SAMPLE_RATE = 16_000
MAX_CLIP_SECONDS = 30  # Whistle transcribes up to 30 seconds in one pass.
MAX_CLIP_BYTES = 1_000_000  # 30 seconds of 16 kHz 16-bit mono is about 960 kB.


class TranscriptionError(ValueError):
    """The uploaded audio cannot be transcribed."""


class TranscriberUnavailable(RuntimeError):
    """The speech model failed or is not available."""


class Transcriber(Protocol):
    def transcribe(self, samples: array) -> str: ...


def read_wav_samples(data: bytes) -> array:
    """Read 16 kHz mono 16-bit WAV bytes into float samples in [-1, 1]."""
    try:
        with wave.open(io.BytesIO(data), "rb") as wav:
            if (
                wav.getnchannels() != 1
                or wav.getsampwidth() != 2
                or wav.getframerate() != SAMPLE_RATE
            ):
                raise TranscriptionError("Audio must be 16 kHz mono 16-bit WAV.")
            frame_count = wav.getnframes()
            frames = wav.readframes(frame_count)
    except (wave.Error, EOFError) as error:
        raise TranscriptionError("Audio is not a valid WAV file.") from error

    if frame_count / SAMPLE_RATE > MAX_CLIP_SECONDS:
        raise TranscriptionError(f"Clip is longer than {MAX_CLIP_SECONDS} seconds.")

    pcm = array("h")
    pcm.frombytes(frames)
    if sys.byteorder == "big":
        pcm.byteswap()
    return array("f", (sample / 32768 for sample in pcm))


class WhistleTranscriber:
    """Runs Whistle one clip at a time. The model loads on first use."""

    def __init__(self, keywords: tuple[str, ...] = ()) -> None:
        self._keywords = list(keywords) or None
        self._lock = threading.Lock()

    def transcribe(self, samples: array) -> str:
        # Import here: the model load is slow, and the env settings above must run first.
        from needle import transcribe

        with self._lock:
            try:
                result = transcribe(samples, language="en", keywords=self._keywords)
            except Exception as error:
                # Log the error type only. Never log audio or transcript text.
                logger.error("transcription_failed error=%s", type(error).__name__)
                raise TranscriberUnavailable("Transcription failed.") from error
        return result["text"].strip()
