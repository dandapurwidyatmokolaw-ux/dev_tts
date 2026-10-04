"""
Web UI Backend Server for Voice & Text Chat Agent.
Built with FastAPI, Server-Sent Events (SSE), and Asynchronous Audio Streaming.
Lokasi: /mnt/d/dev_tts/web_app.py
"""

import os
import sys
import json
import asyncio
import re
import tempfile
import concurrent.futures
from typing import List, Dict, Optional

# Tambahkan direktori kerja ke sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from tts_engine import TTSEngine
from stream_synchronizer import clean_text_for_tts
from llm_client import LLMClient

# Inisialisasi Aplikasi
app = FastAPI(title="Voice & Text AI Chat Agent")

# Folder Audio Sementara untuk Web
WEB_AUDIO_DIR = os.path.join(BASE_DIR, "tmp_audio")
os.makedirs(WEB_AUDIO_DIR, exist_ok=True)

# Shared Singletons
tts_engine = TTSEngine(default_engine="kokoro")
llm_client = LLMClient()
thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=4)

SENTENCE_SPLIT_REGEX = re.compile(r'([.?!:\n]+(?:\s+|$))')

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    engine: str = "kokoro"
    voice: Optional[str] = None
    model: str = "ag/gemini-3.8-flash-low"
    enable_audio: bool = True

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    html_path = os.path.join(BASE_DIR, "templates", "index.html")
    with open(html_path, "r", encoding="utf-8") as f:
        return f.read()

@app.get("/api/config")
async def get_config():
    kokoro_voices = tts_engine.get_available_voices("kokoro")
    edge_voices = [
        "id-ID-ArdiNeural",
        "id-ID-GadisNeural",
        "en-US-JennyNeural",
        "en-US-GuyNeural",
        "ja-JP-NanamiNeural"
    ]
    models = [
        "ag/gemini-3.8-flash-low",
        "ag/gemini-3.8-flash-medium",
        "nvidia/deepseek-ai/deepseek-v4-flash",
        "oc/muse-spark-1.2-contributor-free"
    ]
    return {
        "engines": ["kokoro", "edge"],
        "voices": {
            "kokoro": kokoro_voices,
            "edge": edge_voices
        },
        "models": models
    }

@app.api_route("/audio/{filename}", methods=["GET", "HEAD"])
async def serve_audio(filename: str):
    file_path = os.path.join(WEB_AUDIO_DIR, filename)
    if os.path.exists(file_path):
        media_type = "audio/wav" if filename.endswith(".wav") else "audio/mpeg"
        return FileResponse(file_path, media_type=media_type)
    return HTMLResponse(status_code=404, content="Audio file not found")

def _synthesize_sentence(sentence: str, engine: str, voice: str) -> Optional[str]:
    """Helper fungsi yang dijalankan di background thread untuk sintesis audio."""
    clean = clean_text_for_tts(sentence)
    if not clean or len(clean) < 2:
        return None
    try:
        ext = ".wav" if engine == "kokoro" else ".mp3"
        fd, out_path = tempfile.mkstemp(suffix=ext, prefix="web_audio_", dir=WEB_AUDIO_DIR)
        os.close(fd)
        result_path = tts_engine.synthesize(clean, engine=engine, voice=voice, output_path=out_path)
        if result_path and os.path.exists(result_path):
            return os.path.basename(result_path)
    except Exception as e:
        print(f"[WebTTS Error] {e}")
    return None

@app.post("/api/chat/stream")
async def chat_stream(req: ChatRequest):
    async def event_generator():
        raw_messages = [{"role": m.role, "content": m.content} for m in req.messages]
        # Pastikan system prompt ramah suara ada di awal
        if not raw_messages or raw_messages[0]["role"] != "system":
            raw_messages.insert(0, {
                "role": "system",
                "content": (
                    "Kamu adalah asisten AI suara yang cerdas, ramah, dan ringkas. "
                    "Jawab pertanyaan secara jelas dan to the point tanpa format tabel rumit."
                )
            })

        loop = asyncio.get_event_loop()
        full_text = ""
        current_buffer = ""
        pending_audio_tasks = []

        def get_llm_stream():
            return list(llm_client.stream_chat(raw_messages, model=req.model))

        # Ambil token dari LLM di thread terpisah agar async loop tidak terblokir
        # Untuk real-time streaming, kita gunakan async iteration dari generator
        def run_stream_iter():
            for token in llm_client.stream_chat(raw_messages, model=req.model):
                yield token

        # Generator wrapper untuk event loop
        token_queue = asyncio.Queue()

        def producer():
            try:
                for tok in run_stream_iter():
                    asyncio.run_coroutine_threadsafe(token_queue.put(tok), loop)
            finally:
                asyncio.run_coroutine_threadsafe(token_queue.put(None), loop)

        loop.run_in_executor(thread_pool, producer)

        while True:
            token = await token_queue.get()
            if token is None:
                break

            full_text += token
            current_buffer += token

            # Kirim event token ke browser
            yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"

            # Deteksi pemisah kalimat untuk TTS
            if req.enable_audio:
                matches = list(SENTENCE_SPLIT_REGEX.finditer(current_buffer))
                if matches:
                    last_end = matches[-1].end()
                    sentence = current_buffer[:last_end].strip()
                    current_buffer = current_buffer[last_end:]

                    if len(sentence) >= 3:
                        # Jalankan sintesis di thread pool
                        task = loop.run_in_executor(
                            thread_pool, _synthesize_sentence, sentence, req.engine, req.voice
                        )
                        pending_audio_tasks.append(task)

            # Cek jika ada tugas audio yang sudah selesai untuk langsung dikirim
            ready_tasks = [t for t in pending_audio_tasks if t.done()]
            for t in ready_tasks:
                pending_audio_tasks.remove(t)
                filename = t.result()
                if filename:
                    yield f"data: {json.dumps({'type': 'audio', 'url': f'/audio/{filename}'})}\n\n"

            # Beri kesempatan event loop bernapas
            await asyncio.sleep(0.001)

        # Proses sisa teks buffer terakhir jika ada
        if req.enable_audio and current_buffer.strip():
            task = loop.run_in_executor(
                thread_pool, _synthesize_sentence, current_buffer.strip(), req.engine, req.voice
            )
            pending_audio_tasks.append(task)

        # Tunggu semua sisa tugas audio selesai
        if pending_audio_tasks:
            results = await asyncio.gather(*pending_audio_tasks)
            for filename in results:
                if filename:
                    yield f"data: {json.dumps({'type': 'audio', 'url': f'/audio/{filename}'})}\n\n"

        # Kirim event selesai
        yield f"data: {json.dumps({'type': 'done', 'full_text': full_text})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("web_app:app", host="0.0.0.0", port=7860, reload=False)
