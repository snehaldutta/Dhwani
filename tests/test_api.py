from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from array import array

from voicenotes.app import create_app
from voicenotes.config import Settings
from voicenotes.folders import FolderRegistry
from voicenotes.transcription import MAX_CLIP_BYTES, TranscriberUnavailable
from tests.wav import make_wav

FIXED_NOW = datetime(2026, 10, 24, 14, 30, 12)
BASE_URL = "http://127.0.0.1:8000"


class FakeTranscriber:
    def __init__(self, text: str = "hello there", error: Exception | None = None) -> None:
        self.text = text
        self.error = error
        self.calls: list[array] = []

    def transcribe(self, samples: array) -> str:
        self.calls.append(samples)
        if self.error is not None:
            raise self.error
        return self.text


@pytest.fixture
def notes_dir(tmp_path: Path) -> Path:
    folder = tmp_path / "Notes"
    folder.mkdir()
    return folder


@pytest.fixture
def transcriber() -> FakeTranscriber:
    return FakeTranscriber()


@pytest.fixture
def client(tmp_path: Path, transcriber: FakeTranscriber) -> TestClient:
    return TestClient(make_app(tmp_path, transcriber, debug_clips_dir=None), base_url=BASE_URL)


def make_app(tmp_path: Path, transcriber: FakeTranscriber, debug_clips_dir: Path | None):
    settings = Settings(
        host="127.0.0.1",
        port=8000,
        folders_path=tmp_path / "folders.json",
        keywords=(),
        debug_clips_dir=debug_clips_dir,
    )
    return create_app(
        settings,
        FolderRegistry(settings.folders_path),
        transcriber,
        clock=lambda: FIXED_NOW,
    )


def add_folder(client: TestClient, path: Path, name: str | None = None) -> dict[str, str]:
    response = client.post("/api/folders", json={"path": str(path), "name": name})
    assert response.status_code == 201
    return response.json()


def test_healthz(client: TestClient) -> None:
    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_add_and_list_folders(client: TestClient, notes_dir: Path) -> None:
    folder = add_folder(client, notes_dir, "Work")

    response = client.get("/api/folders")

    assert response.json() == {"items": [folder]}


def test_add_folder_rejects_relative_path(client: TestClient) -> None:
    response = client.post("/api/folders", json={"path": "Notes"})

    assert response.status_code == 400
    assert response.json()["detail"] == "Folder path must be absolute."


def test_add_folder_rejects_duplicate(client: TestClient, notes_dir: Path) -> None:
    add_folder(client, notes_dir)

    response = client.post("/api/folders", json={"path": str(notes_dir)})

    assert response.status_code == 409


def test_save_note_writes_txt_file_in_chosen_folder(
    client: TestClient, notes_dir: Path
) -> None:
    folder = add_folder(client, notes_dir)

    response = client.post(
        "/api/notes",
        json={"folder_id": folder["id"], "title": "Shopping", "body": "bread and tea"},
    )

    assert response.status_code == 201
    saved = Path(response.json()["file"])
    assert saved == notes_dir.resolve() / "Shopping.txt"
    assert saved.read_text(encoding="utf-8") == "Shopping\n\nbread and tea"


def test_save_note_rejects_unknown_folder(client: TestClient) -> None:
    response = client.post(
        "/api/notes", json={"folder_id": "missing", "title": "", "body": "text"}
    )

    assert response.status_code == 404


def test_save_note_rejects_empty_body(client: TestClient, notes_dir: Path) -> None:
    folder = add_folder(client, notes_dir)

    response = client.post(
        "/api/notes", json={"folder_id": folder["id"], "title": "", "body": ""}
    )

    assert response.status_code == 422


def test_save_note_rejects_multiline_title(client: TestClient, notes_dir: Path) -> None:
    folder = add_folder(client, notes_dir)

    response = client.post(
        "/api/notes",
        json={"folder_id": folder["id"], "title": "one\ntwo", "body": "text"},
    )

    assert response.status_code == 422


def test_save_note_reports_folder_deleted_from_disk(
    client: TestClient, notes_dir: Path
) -> None:
    folder = add_folder(client, notes_dir)
    notes_dir.rmdir()

    response = client.post(
        "/api/notes", json={"folder_id": folder["id"], "title": "", "body": "text"}
    )

    assert response.status_code == 409


def test_remove_folder(client: TestClient, notes_dir: Path) -> None:
    folder = add_folder(client, notes_dir)

    assert client.delete(f"/api/folders/{folder['id']}").status_code == 204
    assert client.delete(f"/api/folders/{folder['id']}").status_code == 404


def test_rejects_foreign_host_header(client: TestClient) -> None:
    response = client.get("/healthz", headers={"host": "evil.example"})

    assert response.status_code == 403


def test_rejects_foreign_origin(client: TestClient, notes_dir: Path) -> None:
    response = client.post(
        "/api/folders",
        json={"path": str(notes_dir)},
        headers={"origin": "http://evil.example"},
    )

    assert response.status_code == 403
    assert client.get("/api/folders").json() == {"items": []}


def test_serves_homepage(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "Speak a note" in response.text


def test_serves_notes_app_and_its_scripts(client: TestClient) -> None:
    page = client.get("/app")

    assert page.status_code == 200
    assert "New note" in page.text
    assert client.get("/app.js").status_code == 200
    assert client.get("/recorder.js").status_code == 200


def test_transcribe_clip_returns_text(
    client: TestClient, transcriber: FakeTranscriber
) -> None:
    response = client.post(
        "/api/transcriptions", content=make_wav(), headers={"Content-Type": "audio/wav"}
    )

    assert response.status_code == 200
    assert response.json() == {"text": "hello there"}
    assert len(transcriber.calls) == 1
    assert len(transcriber.calls[0]) == 8000


def test_transcribe_clip_rejects_other_content_type(client: TestClient) -> None:
    response = client.post(
        "/api/transcriptions", content=make_wav(), headers={"Content-Type": "audio/webm"}
    )

    assert response.status_code == 415


def test_transcribe_clip_rejects_invalid_wav(client: TestClient) -> None:
    response = client.post(
        "/api/transcriptions", content=b"nope", headers={"Content-Type": "audio/wav"}
    )

    assert response.status_code == 400


def test_transcribe_clip_rejects_oversized_upload(client: TestClient) -> None:
    response = client.post(
        "/api/transcriptions",
        content=b"\x00" * (MAX_CLIP_BYTES + 1),
        headers={"Content-Type": "audio/wav"},
    )

    assert response.status_code == 413


def test_transcribe_clip_reports_model_failure(
    client: TestClient, transcriber: FakeTranscriber
) -> None:
    transcriber.error = TranscriberUnavailable("Transcription failed.")

    response = client.post(
        "/api/transcriptions", content=make_wav(), headers={"Content-Type": "audio/wav"}
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "Transcription failed."


def test_debug_mode_saves_clip_and_transcript(
    tmp_path: Path, transcriber: FakeTranscriber
) -> None:
    debug_dir = tmp_path / "debug"
    client = TestClient(make_app(tmp_path, transcriber, debug_dir), base_url=BASE_URL)
    clip = make_wav()

    client.post("/api/transcriptions", content=clip, headers={"Content-Type": "audio/wav"})

    saved_wav = list(debug_dir.glob("clip-*.wav"))
    saved_txt = list(debug_dir.glob("clip-*.txt"))
    assert len(saved_wav) == 1 and len(saved_txt) == 1
    assert saved_wav[0].read_bytes() == clip
    assert saved_txt[0].read_text(encoding="utf-8") == "hello there\n"


def test_no_debug_files_by_default(client: TestClient, tmp_path: Path) -> None:
    client.post("/api/transcriptions", content=make_wav(), headers={"Content-Type": "audio/wav"})

    assert not list(tmp_path.glob("**/clip-*"))
