"""Download and load the Whistle engine and model once. Called by scripts/setup.sh."""

import sys
from array import array

from voicenotes.transcription import SAMPLE_RATE, TranscriberUnavailable, WhistleTranscriber


def main() -> int:
    # One second of silence. Loading the model is the goal, not the text.
    silence = array("f", [0.0] * SAMPLE_RATE)
    try:
        WhistleTranscriber().transcribe(silence)
    except TranscriberUnavailable as error:
        cause = type(error.__cause__).__name__
        print(f"Whistle model setup failed ({cause}). Check the network and run the setup again.", file=sys.stderr)
        return 1
    print("Whistle model ready.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
