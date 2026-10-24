# ADR-004: Clip limits, no automatic splitting

Date: 2026-10-24
Status: Accepted. Amends ADR-001 Decision 5.

## Context

ADR-001 Decision 5 said long recordings split into clips of 25 seconds or less. Whistle transcribes up to 30 seconds in one pass. Splitting adds a join step, and a word on a clip edge can split in two.

## Decision

- The browser stops a recording at 25 seconds. The stop is automatic. The user sees the limit in the status line and timer.
- The server accepts WAV clips up to 30 seconds (`MAX_CLIP_SECONDS`) and up to 1,000,000 bytes (`MAX_CLIP_BYTES`). The byte limit fits 30 seconds of 16 kHz 16-bit mono with a margin.
- Longer notes need a new recording. Text already in the note stays. Each transcript appends to the note box.
- Splitting is not built. Revisit it only if users need longer single recordings.

## Consequences

- Good: No join step. No edge-word splits. Simpler code and tests.
- Bad: A note longer than 25 seconds needs several recordings.
- Bad: The 25-second cap is a browser rule. A direct API call can send up to 30 seconds.
- Revisit trigger: Users ask for longer recordings in one go, or the transcript quality drops at clip edges.
