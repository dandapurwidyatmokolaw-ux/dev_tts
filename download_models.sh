#!/usr/bin/env bash
# Script untuk mengunduh model Kokoro-82M ONNX lokal
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODELS_DIR="$SCRIPT_DIR/models"
mkdir -p "$MODELS_DIR"

echo "=== Mengunduh Model Kokoro ONNX ==="

KOKORO_URL="https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx"
VOICES_URL="https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin"

if [ ! -f "$MODELS_DIR/kokoro-v1.0.onnx" ]; then
    echo "Mengunduh kokoro-v1.0.onnx (~325 MB)..."
    curl -L -o "$MODELS_DIR/kokoro-v1.0.onnx" "$KOKORO_URL"
else
    echo "kokoro-v1.0.onnx sudah ada."
fi

if [ ! -f "$MODELS_DIR/voices-v1.0.bin" ]; then
    echo "Mengunduh voices-v1.0.bin (~28 MB)..."
    curl -L -o "$MODELS_DIR/voices-v1.0.bin" "$VOICES_URL"
else
    echo "voices-v1.0.bin sudah ada."
fi

echo "=== Model Kokoro siap di: $MODELS_DIR ==="
