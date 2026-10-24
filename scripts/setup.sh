#!/usr/bin/env bash
# First-time setup for Dhwani. Run once after cloning:  ./scripts/setup.sh
# Needs network access for this run only. After setup, speech recognition runs offline.
set -euo pipefail

cd "$(dirname "$0")/.."

info() { printf '\n\033[1m==> %s\033[0m\n' "$*"; }
die() { printf '\nerror: %s\n' "$*" >&2; exit 1; }

case "$(uname -s)" in
  Darwin|Linux) ;;
  *) die "Unsupported system. Use macOS, Linux, or WSL on Windows." ;;
esac

if ! command -v uv >/dev/null 2>&1; then
  die "uv is not installed. Install it from https://docs.astral.sh/uv/getting-started/installation/ then run this script again."
fi

info "Installing Python 3.12 and the project dependencies"
uv sync

info "Running the test suite"
uv run pytest -q

# Hugging Face is offline by default in the app. Allow it for this one step only.
info "Downloading the Whistle engine and model (one time)"
HF_HUB_OFFLINE=0 uv run python -m voicenotes.warmup

info "Setup complete"
cat <<'EOF'
Start the app:
  uv run python -m voicenotes

Then open http://127.0.0.1:8000 in your browser.
Add a folder on the notes page before you save your first note.
EOF
