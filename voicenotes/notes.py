import re
from datetime import datetime
from pathlib import Path

MAX_TITLE_CHARS = 200
MAX_BODY_CHARS = 200_000
MAX_STEM_CHARS = 80
MAX_NAME_ATTEMPTS = 100

_UNSAFE_CHARS = re.compile(r'[\x00-\x1f\x7f/\\:*?"<>|]')
_SPACES = re.compile(r"\s+")


class NoteSaveError(OSError):
    """The note file cannot be written."""


def file_stem(title: str, now: datetime) -> str:
    """Build a file name without the extension. It never holds a path separator or a leading dot."""
    cleaned = _SPACES.sub(" ", _UNSAFE_CHARS.sub(" ", title)).strip(" .")
    if not cleaned:
        return now.strftime("note-%Y%m%d-%H%M%S")
    return cleaned[:MAX_STEM_CHARS].rstrip(" .")


def save_note(folder: Path, title: str, body: str, now: datetime) -> Path:
    """Write a new .txt file in the folder. Never overwrite an existing file."""
    stem = file_stem(title, now)
    clean_title = title.strip()
    content = f"{clean_title}\n\n{body}" if clean_title else body

    for attempt in range(1, MAX_NAME_ATTEMPTS + 1):
        suffix = "" if attempt == 1 else f" ({attempt})"
        candidate = folder / f"{stem}{suffix}.txt"
        try:
            with candidate.open("x", encoding="utf-8") as handle:
                handle.write(content)
        except FileExistsError:
            continue
        except OSError as error:
            raise NoteSaveError("Folder is missing or not writable.") from error
        return candidate
    raise NoteSaveError("Too many notes with the same name.")
