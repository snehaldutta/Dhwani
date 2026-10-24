# ADR-007: Whistle runtime settings

Date: 2026-10-24
Status: Accepted

## Context

The `cactus-needle` package, which provides Whistle, has settings that affect privacy and behavior:

- It sends anonymous usage events to a remote server (`needle/_telemetry.py`) unless turned off.
- It checks Hugging Face on each model load. The first use downloads the engine library and model weights into `~/.cache/cactus-needle/`.
- It detects the spoken language unless it is set.
- It accepts keyword biasing for names and jargon.

The app is English only, and must keep audio and text on the machine (ADR-001 Decisions 1 and 7).

## Decision

- `voicenotes/transcription.py` sets `NEEDLE_TELEMETRY=0` and `DO_NOT_TRACK=1` before the package loads. These are forced, not defaults.
- It sets `HF_HUB_OFFLINE=1` by default. The first model download needs `HF_HUB_OFFLINE=0`. The README explains this.
- Every transcription passes `language="en"`.
- `VOICENOTES_KEYWORDS` (comma-separated) passes names and terms for biasing. Keyword biasing helped "Priya" in a test. It did not fix "Deep" in a later test.
- Whistle runs one clip at a time behind a lock. The model loads on first use.
- Logs record the error type on failure. Logs never record transcript text.

## Consequences

- Good: No usage events. No network calls after the one-time model download. English only, as scoped.
- Bad: The first run needs network access and `HF_HUB_OFFLINE=0`.
- Bad: Keyword biasing is a partial fix. Some names still need a manual edit.
- Revisit trigger: The package changes its telemetry or download behavior. Or a second speech model is compared on saved clips.
