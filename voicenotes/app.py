import logging
from collections.abc import Awaitable, Callable
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator
from starlette.concurrency import run_in_threadpool

from voicenotes.config import Settings
from voicenotes.folders import (
    DuplicateFolderError,
    Folder,
    FolderError,
    FolderRegistry,
    UnknownFolderError,
)
from voicenotes.notes import MAX_BODY_CHARS, MAX_TITLE_CHARS, NoteSaveError, save_note
from voicenotes.transcription import (
    MAX_CLIP_BYTES,
    Transcriber,
    TranscriberUnavailable,
    TranscriptionError,
    read_wav_samples,
)

STATIC_DIR = Path(__file__).parent / "static"
WAV_TYPES = {"audio/wav", "audio/x-wav"}
logger = logging.getLogger("voicenotes")


class FolderIn(BaseModel):
    path: str = Field(min_length=1, max_length=4096)
    name: str | None = Field(default=None, max_length=120)


class NoteIn(BaseModel):
    folder_id: str = Field(min_length=1, max_length=64)
    title: str = Field(default="", max_length=MAX_TITLE_CHARS)
    body: str = Field(min_length=1, max_length=MAX_BODY_CHARS)

    @field_validator("title")
    @classmethod
    def title_is_one_line(cls, value: str) -> str:
        if "\n" in value or "\r" in value:
            raise ValueError("Title must be one line.")
        return value


def folder_view(folder: Folder) -> dict[str, str]:
    return asdict(folder)


def save_debug_clip(folder: Path, now: datetime, data: bytes, text: str) -> None:
    """Debug only. Keeps the clip and what Whistle returned for it, so both can be compared."""
    folder.mkdir(parents=True, exist_ok=True)
    stem = f"clip-{now:%Y%m%d-%H%M%S-%f}"
    (folder / f"{stem}.wav").write_bytes(data)
    (folder / f"{stem}.txt").write_text(text + "\n", encoding="utf-8")
    logger.warning("debug_clip_saved folder=%s", folder)


async def read_limited(request: Request, limit: int) -> bytes:
    chunks: list[bytes] = []
    total = 0
    async for chunk in request.stream():
        total += len(chunk)
        if total > limit:
            raise HTTPException(status_code=413, detail="Clip is too large.")
        chunks.append(chunk)
    return b"".join(chunks)


def create_app(
    settings: Settings,
    folders: FolderRegistry,
    transcriber: Transcriber,
    clock: Callable[[], datetime] = datetime.now,
) -> FastAPI:
    app = FastAPI(title="Voice Notes")
    allowed_hosts = {f"127.0.0.1:{settings.port}", f"localhost:{settings.port}"}
    allowed_origins = {f"http://{host}" for host in allowed_hosts}

    @app.middleware("http")
    async def local_requests_only(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        # Blocks DNS rebinding (Host check) and pages on other sites (Origin check).
        if request.headers.get("host") not in allowed_hosts:
            return JSONResponse({"detail": "Host not allowed."}, status_code=403)
        origin = request.headers.get("origin")
        if origin is not None and origin not in allowed_origins:
            return JSONResponse({"detail": "Origin not allowed."}, status_code=403)
        return await call_next(request)

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/", include_in_schema=False)
    def home() -> FileResponse:
        return FileResponse(STATIC_DIR / "home.html")

    @app.get("/app", include_in_schema=False)
    def notes_app() -> FileResponse:
        return FileResponse(STATIC_DIR / "app.html")

    @app.get("/api/folders")
    def list_folders() -> dict[str, list[dict[str, str]]]:
        return {"items": [folder_view(folder) for folder in folders.list()]}

    @app.post("/api/folders", status_code=201)
    def add_folder(payload: FolderIn) -> dict[str, str]:
        try:
            folder = folders.add(payload.path, payload.name)
        except DuplicateFolderError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        except FolderError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        logger.info("folder_added folder_id=%s", folder.id)
        return folder_view(folder)

    @app.delete("/api/folders/{folder_id}", status_code=204)
    def remove_folder(folder_id: str) -> Response:
        try:
            folders.remove(folder_id)
        except UnknownFolderError as error:
            raise HTTPException(status_code=404, detail="Folder not found.") from error
        logger.info("folder_removed folder_id=%s", folder_id)
        return Response(status_code=204)

    @app.post("/api/notes", status_code=201)
    def create_note(payload: NoteIn) -> dict[str, str]:
        try:
            folder = folders.get(payload.folder_id)
        except UnknownFolderError as error:
            raise HTTPException(status_code=404, detail="Folder not found.") from error
        try:
            saved = save_note(Path(folder.path), payload.title, payload.body, clock())
        except NoteSaveError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        # Log ids and sizes only. Never log note text.
        logger.info("note_saved folder_id=%s chars=%d", folder.id, len(payload.body))
        return {"file": str(saved)}

    @app.post("/api/transcriptions")
    async def transcribe_clip(request: Request) -> dict[str, str]:
        content_type = request.headers.get("content-type", "").split(";")[0].strip()
        if content_type not in WAV_TYPES:
            raise HTTPException(status_code=415, detail="Send the clip as audio/wav.")
        data = await read_limited(request, MAX_CLIP_BYTES)
        try:
            samples = read_wav_samples(data)
        except TranscriptionError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        try:
            text = await run_in_threadpool(transcriber.transcribe, samples)
        except TranscriberUnavailable as error:
            raise HTTPException(status_code=503, detail=str(error)) from error
        logger.info("transcription_done samples=%d chars=%d", len(samples), len(text))
        if settings.debug_clips_dir is not None:
            save_debug_clip(settings.debug_clips_dir, clock(), data, text)
        return {"text": text}

    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
    return app
