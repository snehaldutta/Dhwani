from pathlib import Path

import pytest

from voicenotes.folders import (
    DuplicateFolderError,
    FolderError,
    FolderRegistry,
    UnknownFolderError,
)


def test_add_folder_stores_resolved_path_and_survives_reload(tmp_path: Path) -> None:
    store = tmp_path / "data" / "folders.json"
    notes_dir = tmp_path / "Notes"
    notes_dir.mkdir()

    registry = FolderRegistry(store)
    folder = registry.add(str(notes_dir), "Work")

    assert folder.name == "Work"
    assert folder.path == str(notes_dir.resolve())
    assert FolderRegistry(store).get(folder.id) == folder


def test_add_folder_defaults_name_to_directory_name(tmp_path: Path) -> None:
    notes_dir = tmp_path / "Ideas"
    notes_dir.mkdir()

    folder = FolderRegistry(tmp_path / "folders.json").add(str(notes_dir))

    assert folder.name == "Ideas"


@pytest.mark.parametrize(
    ("make_target", "expected"),
    [
        (lambda tmp: "relative/Notes", "Folder path must be absolute."),
        (lambda tmp: str(tmp / "missing"), "Folder does not exist."),
        (lambda tmp: str(_make_file(tmp / "file.txt")), "Path is not a folder."),
    ],
)
def test_add_folder_rejects_unusable_paths(
    tmp_path: Path, make_target, expected: str
) -> None:
    registry = FolderRegistry(tmp_path / "folders.json")

    with pytest.raises(FolderError, match=expected):
        registry.add(make_target(tmp_path))


def test_add_folder_rejects_duplicate(tmp_path: Path) -> None:
    notes_dir = tmp_path / "Notes"
    notes_dir.mkdir()
    registry = FolderRegistry(tmp_path / "folders.json")
    registry.add(str(notes_dir))

    with pytest.raises(DuplicateFolderError):
        registry.add(str(notes_dir))


def test_remove_folder_keeps_files_on_disk(tmp_path: Path) -> None:
    notes_dir = tmp_path / "Notes"
    notes_dir.mkdir()
    note = _make_file(notes_dir / "keep.txt")
    registry = FolderRegistry(tmp_path / "folders.json")
    folder = registry.add(str(notes_dir))

    registry.remove(folder.id)

    assert note.exists()
    with pytest.raises(UnknownFolderError):
        registry.get(folder.id)


def test_get_unknown_folder_raises(tmp_path: Path) -> None:
    with pytest.raises(UnknownFolderError):
        FolderRegistry(tmp_path / "folders.json").get("missing")


def _make_file(path: Path) -> Path:
    path.write_text("not a folder", encoding="utf-8")
    return path
