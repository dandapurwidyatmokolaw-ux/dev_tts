# 🎙️ Terminal Voice & Text Chat Agent (Ultra-Fast Local TTS)

A real-time voice and text conversational AI agent designed for CLI / Terminal users. It synchronizes immediate streaming text output in your terminal with fast, asynchronous audio speech synthesis (Kokoro-82M ONNX local GPU & Edge-TTS).

Includes a minimal **Web Microphone Controller** for hands-free speech-to-text input from any browser.

---

## 🌟 Key Features

1. **Dual-Engine Speech Synthesis:**
   - **Kokoro-82M ONNX (Local GPU / CPU):** Ultra-fast local synthesis via ONNX Runtime with CUDA acceleration (RTX series or CPU). 50+ voices available (`af_sarah`, `am_adam`, `bm_george`, etc.).
   - **Edge-TTS (Cloud / Free):** Natural multi-lingual neural voices (Indonesian `id-ID-ArdiNeural`, `id-ID-GadisNeural`, English, etc.) without requiring an API key.
2. **Synchronous Screen & Audio Streaming:**
   - User inputs and AI replies stream word-by-word directly to stdout in the terminal.
   - First sentence begins playing audio immediately without waiting for the full response to finish generating.
3. **Web Microphone Controller:**
   - Lightweight Web UI running on `http://localhost:7860`.
   - Talk to your browser mic &rarr; Browser Web Speech STT transcribes speech &rarr; Text automatically appears in the terminal &rarr; LLM streams response and speaks back.
4. **LLM Agnostic:**
   - Connects to any OpenAI-compatible API (e.g. 9router, Ollama, vLLM, LocalAI, or OpenRouter) via configurable base URL.
5. **Cross-Platform Audio Playback:**
   - Automatically supports native Linux (ALSA/PulseAudio/aplay/mpv) and WSL-to-Windows host playback.

---

## 📁 Project Structure

```
dev_tts/
├── voice_terminal_app.py   # Main CLI application + Web Mic Controller
├── chat_terminal.py        # Terminal-only chat interface
├── tts_engine.py           # Multi-engine TTS synthesizer (Kokoro + Edge + F5)
├── audio_player.py         # Asynchronous background audio player
├── llm_client.py           # Streaming client for OpenAI-compatible endpoints
├── stream_synchronizer.py  # Text display & sentence chunking synchronizer
├── web_app.py              # Standalone Web Chat UI
├── download_models.sh      # Helper script to download Kokoro-82M ONNX model
├── run_chat.sh             # Quick startup script for Terminal + Web Mic
├── run_web.sh              # Quick startup script for Full Web UI
├── requirements.txt        # Python package dependencies
├── models/                 # Directory for model weights (.onnx, .bin)
└── voices_f5/              # Reference audio samples for voice cloning
```

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.10 or 3.11
- `ffmpeg` installed on your system:
  ```bash
  # Ubuntu / Debian / WSL:
  sudo apt update && sudo apt install -y ffmpeg
  ```
- An active OpenAI-compatible LLM endpoint (default: `http://localhost:20128/v1` or customize via environment variables).

### 2. Installation

Clone this repository and set up a virtual environment:

```bash
git clone https://github.com/dandapurwidyatmokolaw-ux/dev_tts.git
cd dev_tts

python3 -m venv .venv
source .venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt
```

*(Optional for NVIDIA GPU acceleration)*:
```bash
pip install onnxruntime-gpu
```

### 3. Download Local Kokoro TTS Model (Optional for Offline Mode)

If you plan to use the offline Kokoro engine:
```bash
chmod +x download_models.sh
./download_models.sh
```
*Note: If you skip this step, the agent automatically falls back to Edge-TTS.*

---

## 💻 Usage

### Option A: Terminal Voice Chat with Web Mic (Recommended)

Run the launcher:
```bash
./run_chat.sh
```

1. The terminal starts the interactive session.
2. Open your browser at **`http://localhost:7860`**.
3. Select your voice and click **"START MODE SUARA (MIC)"**.
4. Speak into your microphone. Your words will appear in the terminal, and the AI will stream its response both to the terminal and as spoken audio!

### Option B: Full Web UI Chat

```bash
./run_web.sh
```
Open **`http://localhost:7860`** for a browser-based chat interface.

### Option C: Interactive Terminal Commands

During a terminal chat session, you can use built-in commands:
- `/engine [kokoro|edge]` : Switch TTS engine.
- `/voice [name]` : Switch voice preset (e.g. `/voice id-ID-ArdiNeural` or `/voice af_sarah`).
- `/voices` : List all available voices for the current engine.
- `/model [name]` : Switch LLM model name.
- `/mute` / `/unmute` : Toggle audio playback.
- `/clear` : Clear conversation history.
- `/exit` : Exit the app.

---

## ⚙️ Configuration

You can customize the LLM endpoint and model via environment variables or CLI flags:

```bash
# Example with custom OpenAI-compatible server:
export OPENAI_BASE_URL="http://localhost:11434/v1"   # e.g. Ollama
export OPENAI_API_KEY="your-key-if-any"
export LLM_MODEL="llama3"

./run_chat.sh
```

---

## 📄 License
MIT License. Open-source and free for personal and commercial development.
