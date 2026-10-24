# ADR-002: Save notes as .txt files in user-chosen folders

Date: 2026-10-24
Status: Accepted

## Context

The user wants each note saved as a `.txt` file in a folder the user picks. The user wants the files to be plain, portable and easy to find without the app. The app runs on the user's own machine, so the server can write to local folders.

Browser options checked:

- File System Access API (`showDirectoryPicker`): Chromium only. Gives a folder handle, not an absolute path. Permission must be granted again in each session. Not usable in Safari or Firefox.
- Server writes to a folder path the user registers: works in any browser. The server has file access because it runs locally.

## Decision

- The server writes each note as a UTF-8 `.txt` file. The file holds the title on the first line, a blank line, then the body.
- The user registers folders by absolute path. The server checks that the path exists, is a folder and is writable. Registered folders are stored in one JSON file (`data/folders.json` by default).
- The file name comes from the title. The server removes path separators, control characters and leading dots, and cuts the name at 80 characters. An empty title uses a timestamp name.
- The server never overwrites a file. A name clash adds ` (2)`, ` (3)` and so on.
- Removing a folder removes only the registry entry. Files stay on disk.
- Requests must come with a `Host` header for `127.0.0.1` or `localhost`, and any `Origin` must match the same address. Other values get 403.
- Notes are not stored in SQLite for this feature. This changes Decision 4 in ADR-001 for note storage. SQLite may still hold other data later.

## Consequences

- Good: Files are plain text in folders the user chooses. No database to back up for notes. Works in any browser. The server rejects requests from other websites and from DNS rebinding.
- Bad: The user types the folder path. A note that fails midway can leave a partial file. The file list is the folder itself, so the app cannot search notes across folders without scanning them.
- Revisit trigger: Users need search or sorting across folders (then add an index). Users need a native folder picker (then add an OS dialog through the server). A note write must be atomic (then write to a temp file and rename).

## Notes

- Limit: 200 characters for a title, 200,000 characters for a body.
- Logs record folder id and body length only. Note text is never logged.
