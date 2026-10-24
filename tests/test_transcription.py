import pytest

from tests.wav import make_wav
from voicenotes.transcription import TranscriptionError, read_wav_samples


def test_read_wav_samples_returns_float_samples_in_range() -> None:
    samples = read_wav_samples(make_wav(seconds=0.5))

    assert len(samples) == 8000
    assert all(-1.0 <= sample <= 1.0 for sample in samples)


@pytest.mark.parametrize(
    ("wav_bytes", "message"),
    [
        (make_wav(rate=44_100), "Audio must be 16 kHz mono 16-bit WAV."),
        (make_wav(channels=2), "Audio must be 16 kHz mono 16-bit WAV."),
        (make_wav(width=1), "Audio must be 16 kHz mono 16-bit WAV."),
        (make_wav(seconds=31), "Clip is longer than 30 seconds."),
        (b"not a wav file", "Audio is not a valid WAV file."),
    ],
)
def test_read_wav_samples_rejects_unusable_audio(wav_bytes: bytes, message: str) -> None:
    with pytest.raises(TranscriptionError, match=message):
        read_wav_samples(wav_bytes)
