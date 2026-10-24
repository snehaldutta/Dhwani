# ADR-005: Keep audio only in opt-in debug mode

Date: 2026-10-24
Status: Accepted. Amends ADR-001 Decision 6.

## Context

ADR-001 Decision 6 said the app stores transcripts, not audio. Transcript quality problems need the real clip to diagnose. The user reported an inaccurate transcript, and the server had no clip to compare with the text.

## Decision

- Add `VOICENOTES_DEBUG_CLIPS_DIR`. When set, the server saves each clip as a WAV file and its transcript as a `.txt` file.
- The variable is off by default. Normal use keeps no audio.
- The server logs a warning for each saved clip. The log holds no transcript text.
- Tests check that nothing is saved by default, and that debug mode saves the clip and transcript.
- Delete debug folders when the diagnosis is done. The user asked for their clips to be deleted after the 2026-10-24 test.

## Consequences

- Good: Clips can be checked against the reference text. Normal use stays private.
- Bad: Debug mode writes personal audio to disk. Users must remember to turn it off.
- Revisit trigger: A user wants audio playback, or a feature needs stored audio.
