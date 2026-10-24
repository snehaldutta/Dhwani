import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    host: str
    port: int
    folders_path: Path
    keywords: tuple[str, ...]
    # Debug only. When set, each clip and its transcript are saved here.
    debug_clips_dir: Path | None


def load_settings(env: Mapping[str, str] = os.environ) -> Settings:
    keywords = tuple(
        word.strip() for word in env.get("VOICENOTES_KEYWORDS", "").split(",") if word.strip()
    )
    debug_dir = env.get("VOICENOTES_DEBUG_CLIPS_DIR")
    return Settings(
        host=env.get("VOICENOTES_HOST", "127.0.0.1"),
        port=int(env.get("VOICENOTES_PORT", "8000")),
        folders_path=Path(env.get("VOICENOTES_FOLDERS_PATH", "data/folders.json")),
        keywords=keywords,
        debug_clips_dir=Path(debug_dir) if debug_dir else None,
    )
