import uvicorn

from voicenotes.app import create_app
from voicenotes.config import load_settings
from voicenotes.folders import FolderRegistry
from voicenotes.transcription import WhistleTranscriber


def main() -> None:
    settings = load_settings()
    app = create_app(
        settings,
        FolderRegistry(settings.folders_path),
        WhistleTranscriber(keywords=settings.keywords),
    )
    uvicorn.run(app, host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()
