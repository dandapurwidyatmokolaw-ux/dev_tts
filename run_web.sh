#!/usr/bin/env bash
# Launcher untuk Web UI Voice & Text Chat Agent
# Lokasi: /mnt/d/dev_tts/run_web.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PYTHON="$SCRIPT_DIR/.venv/bin/python"

if [ ! -f "$VENV_PYTHON" ]; then
    echo "[Error] Virtual environment tidak ditemukan di $SCRIPT_DIR/.venv"
    exit 1
fi

PORT="${PORT:-7860}"
HOST="${HOST:-0.0.0.0}"

echo "================================================================================"
echo "           STARTING VOICE & TEXT CHAT WEB UI (PORT $PORT)"
echo "================================================================================"
echo "Buka di browser Windows Anda:"
echo "-> http://localhost:$PORT"
echo "-> http://127.0.0.1:$PORT"
echo "================================================================================"

exec "$VENV_PYTHON" -m uvicorn web_app:app --host "$HOST" --port "$PORT" --app-dir "$SCRIPT_DIR"
