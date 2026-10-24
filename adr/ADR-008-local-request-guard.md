# ADR-008: Accept only local Host and Origin headers

Date: 2026-10-24
Status: Accepted

## Context

The server listens on `127.0.0.1` and has no login. Two attacks reach a local server from a browser:

- DNS rebinding: a remote site resolves its name to `127.0.0.1` and reads the API.
- Cross-site requests: a page on another site sends a POST to `localhost:8000`.

The app writes files to folders the user registers, so these attacks matter.

## Decision

- Middleware rejects any request whose `Host` header is not `127.0.0.1:<port>` or `localhost:<port>`. It returns 403.
- It rejects any request with an `Origin` header that is not the same local address. It returns 403.
- Requests without an `Origin` header (same-site GET requests, for example) pass the Origin check.
- The app sends no CORS headers. Other sites cannot read responses.

## Consequences

- Good: Blocks DNS rebinding and cross-site writes without a token or login.
- Bad: Access from another device on the network is blocked. This is intended.
- Bad: A changed port needs the same `VOICENOTES_PORT` value in the Host allow list. The code builds the list from settings.
- Revisit trigger: The app runs on another machine or behind a reverse proxy. Then add login and a proper auth design first (ADR-001 section 7).
