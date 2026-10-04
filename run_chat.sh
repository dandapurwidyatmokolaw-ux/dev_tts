#!/usr/bin/env bash
# Launcher untuk Terminal Voice & Text Chat Agent
# Lokasi: /mnt/d/dev_tts/run_chat.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PYTHON="$SCRIPT_DIR/.venv/bin/python"

if [ ! -f "$VENV_PYTHON" ]; then
    echo "[Error] Virtual environment tidak ditemukan di $SCRIPT_DIR/.venv"
    echo "Silakan jalankan setup terlebih dahulu."
    exit 1
fi

# Jalankan Voice & Text Chat Terminal (dengan Web Mic Controller)
export PYTHONPATH="$SCRIPT_DIR:$PYTHONPATH"
exec "$VENV_PYTHON" -u "$SCRIPT_DIR/voice_terminal_app.py" "$@"
