import io
import wave


def make_wav(
    seconds: float = 0.5, rate: int = 16_000, channels: int = 1, width: int = 2
) -> bytes:
    """Build WAV bytes of silence with the given format."""
    frames = int(seconds * rate)
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(channels)
        wav.setsampwidth(width)
        wav.setframerate(rate)
        wav.writeframes(b"\x00" * frames * channels * width)
    return buffer.getvalue()
