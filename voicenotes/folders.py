import json
import os
import threading
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path


class FolderError(ValueError):
    """The path cannot be used as a note folder."""


class DuplicateFolderError(FolderError):
    """The folder is already in the list."""


class UnknownFolderError(KeyError):
    """No folder has the given id."""


@dataclass(frozen=True)
class Folder:
    id: str
    name: str
    path: str


class FolderRegistry:
    """Keeps the folders the user chose. Stores the list in one JSON file."""

    def __init__(self, store_path: Path) -> None:
        self._store_path = store_path
        self._lock = threading.Lock()
        self._folders = self._load()

    def list(self) -> list[Folder]:
        with self._lock:
            return list(self._folders.values())

    def get(self, folder_id: str) -> Folder:
        with self._lock:
            folder = self._folders.get(folder_id)
        if folder is None:
            raise UnknownFolderError(folder_id)
        return folder

    def add(self, path_text: str, name: str | None = None) -> Folder:
        path = Path(path_text)
        if not path.is_absolute():
            raise FolderError("Folder path must be absolute.")
        try:
            resolved = path.resolve(strict=True)
        except FileNotFoundError:
            raise FolderError("Folder does not exist.") from None
        if not resolved.is_dir():
            raise FolderError("Path is not a folder.")
        if not os.access(resolved, os.W_OK):
            raise FolderError("Folder is not writable.")

        with self._lock:
            if any(folder.path == str(resolved) for folder in self._folders.values()):
                raise DuplicateFolderError("Folder is already in the list.")
            folder = Folder(
                id=uuid.uuid4().hex,
                name=(name or "").strip() or resolved.name or str(resolved),
                path=str(resolved),
            )
            self._folders[folder.id] = folder
            self._save()
        return folder

    def remove(self, folder_id: str) -> None:
        """Remove a folder from the list. Files in the folder stay on disk."""
        with self._lock:
            if folder_id not in self._folders:
                raise UnknownFolderError(folder_id)
            del self._folders[folder_id]
            self._save()

    def _load(self) -> dict[str, Folder]:
        if not self._store_path.exists():
            return {}
        # TODO(proto): a corrupt file stops startup. Add a backup and recovery path later.
        records = json.loads(self._store_path.read_text(encoding="utf-8"))
        folders = (Folder(**record) for record in records)
        return {folder.id: folder for folder in folders}

    def _save(self) -> None:
        self._store_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self._store_path.with_suffix(".tmp")
        records = [asdict(folder) for folder in self._folders.values()]
        temp_path.write_text(json.dumps(records, indent=2), encoding="utf-8")
        os.replace(temp_path, self._store_path)
