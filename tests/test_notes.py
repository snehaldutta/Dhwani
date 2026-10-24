from datetime import datetime
from pathlib import Path

import pytest

from voicenotes.notes import MAX_STEM_CHARS, NoteSaveError, file_stem, save_note

NOW = datetime(2026, 10, 24, 14, 30, 12)


def test_file_stem_removes_path_separators_and_leading_dots() -> None:
    stem = file_stem("../../etc/passwd", NOW)

    assert "/" not in stem
    assert not stem.startswith(".")
    assert stem == "etc passwd"


def test_file_stem_replaces_unsafe_characters() -> None:
    assert file_stem('a:b*c?d"e<f>g|h', NOW) == "a b c d e f g h"


def test_file_stem_uses_timestamp_for_empty_title() -> None:
    assert file_stem("   ", NOW) == "note-20261024-143012"


def test_file_stem_limits_length() -> None:
    assert len(file_stem("x" * 500, NOW)) == MAX_STEM_CHARS


def test_save_note_writes_title_and_body_as_utf8(tmp_path: Path) -> None:
    saved = save_note(tmp_path, "Groceries", "milk, eggs, café ✓", NOW)

    assert saved == tmp_path / "Groceries.txt"
    assert saved.read_text(encoding="utf-8") == "Groceries\n\nmilk, eggs, café ✓"


def test_save_note_without_title_writes_body_only(tmp_path: Path) -> None:
    saved = save_note(tmp_path, "", "just the body", NOW)

    assert saved.name == "note-20261024-143012.txt"
    assert saved.read_text(encoding="utf-8") == "just the body"


def test_save_note_adds_suffix_instead_of_overwriting(tmp_path: Path) -> None:
    first = save_note(tmp_path, "Idea", "first", NOW)
    second = save_note(tmp_path, "Idea", "second", NOW)

    assert first.name == "Idea.txt"
    assert second.name == "Idea (2).txt"
    assert first.read_text(encoding="utf-8") == "Idea\n\nfirst"
    assert second.read_text(encoding="utf-8") == "Idea\n\nsecond"


def test_save_note_never_touches_existing_file(tmp_path: Path) -> None:
    existing = tmp_path / "Plan.txt"
    existing.write_text("keep me", encoding="utf-8")

    save_note(tmp_path, "Plan", "new text", NOW)

    assert existing.read_text(encoding="utf-8") == "keep me"


def test_save_note_fails_when_folder_is_missing(tmp_path: Path) -> None:
    with pytest.raises(NoteSaveError):
        save_note(tmp_path / "gone", "Title", "body", NOW)
