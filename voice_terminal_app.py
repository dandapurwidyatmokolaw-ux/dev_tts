#!/usr/bin/env python3
"""
Terminal Voice & Text Chat Agent with Web Mic Controller.
Lokasi: /mnt/d/dev_tts/voice_terminal_app.py

Fitur:
- Web UI (http://localhost:7860): Pengontrol suara, Mic STT (Continuous & Push-to-Talk), Stop Audio, Shutdown App.
- Echo Cancellation / Loop Prevention: Mic otomatis dijeda saat AI sedang berbicara agar tidak menangkap suara speaker.
- Tampilan Terminal Elegan: Format border dan prompt '>' persis seperti Hermes CLI (text.png).
- Dual Engine: Edge-TTS untuk Bahasa Indonesia alami (Gadis/Ardi) & Kokoro-82M GPU untuk English ultra-cepat.
"""

import os
import sys
import re
import time
import select
import queue
import socket
import threading
import uvicorn
from pydantic import BaseModel
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from tts_engine import TTSEngine
from audio_player import AudioPlayer
from llm_client import LLMClient
from stream_synchronizer import StreamSynchronizer

# Antrean input terpadu
input_queue = queue.Queue()

# State Pengaturan Aktif (Default Edge Gadis agar Bahasa Indonesia alami)
active_settings = {
    "engine": "edge",
    "voice": "id-ID-GadisNeural",
    "model": "ag/gemini-3.8-flash-low",
    "audio_enabled": True
}

# Inisialisasi FastAPI
web_server = FastAPI(title="Voice Controller API")

class SpeechPayload(BaseModel):
    text: str
    engine: str = "edge"
    voice: str = "id-ID-GadisNeural"

class VoiceConfigPayload(BaseModel):
    engine: str
    voice: str

@web_server.get("/", response_class=HTMLResponse)
async def serve_index():
    html_path = os.path.join(BASE_DIR, "templates", "index.html")
    with open(html_path, "r", encoding="utf-8") as f:
        return f.read()

tts_global = None
player_global = None
llm_global = None
syncer_global = None
app_running = True
agent_busy = False
latest_chat = {
    "user": "",
    "source": "voice",
    "agent": "",
    "is_streaming": False,
    "timestamp": 0
}

@web_server.get("/api/status")
async def get_status():
    is_playing = (player_global.is_playing() if player_global else False) or agent_busy
    return {
        "ready": tts_global is not None,
        "engine": active_settings["engine"],
        "voice": active_settings["voice"],
        "is_playing": is_playing,
        "agent_busy": agent_busy,
        "latest_chat": latest_chat
    }

@web_server.get("/api/playback-status")
async def get_playback_status():
    """Endpoint untuk mengecek apakah audio AI sedang diputar dan status streaming."""
    is_playing = (player_global.is_playing() if player_global else False) or agent_busy
    return {
        "is_playing": is_playing,
        "agent_busy": agent_busy,
        "latest_chat": latest_chat
    }

@web_server.post("/api/stop-audio")
async def stop_audio():
    """Hentikan pemutaran audio AI seketika dan kosongkan antrean."""
    global agent_busy
    agent_busy = False
    latest_chat["is_streaming"] = False
    if player_global:
        player_global.clear()
    return {"status": "stopped", "message": "Audio pemutaran dihentikan."}

@web_server.post("/api/stop-app")
async def stop_app():
    """Hentikan seluruh aplikasi dan matikan server."""
    global app_running, agent_busy
    app_running = False
    agent_busy = False
    if player_global:
        player_global.stop()
    
    def delayed_exit():
        time.sleep(0.5)
        os._exit(0)

    threading.Thread(target=delayed_exit, daemon=True).start()
    return {"status": "exiting", "message": "Server dan aplikasi sedang dimatikan..."}

@web_server.get("/api/config")
async def get_config():
    kokoro_voices = [
        "af_sarah", "af_bella", "af_alloy", "af_heart",
        "am_adam", "am_echo", "am_eric", "bm_george"
    ]
    f5_voices = ["f5_gadis", "f5_ardi", "f5_jenny"]
    if tts_global:
        try:
            kokoro_voices = tts_global.get_available_voices("kokoro")
        except Exception:
            pass

    edge_voices = [
        "id-ID-GadisNeural",
        "id-ID-ArdiNeural",
        "en-US-JennyNeural",
        "en-US-GuyNeural",
        "ja-JP-NanamiNeural"
    ]
    return {
        "engines": ["edge", "f5", "kokoro"],
        "voices": {
            "edge": edge_voices,
            "f5": f5_voices,
            "kokoro": kokoro_voices
        }
    }

@web_server.post("/api/set-voice")
async def set_voice(payload: VoiceConfigPayload):
    active_settings["engine"] = payload.engine
    active_settings["voice"] = payload.voice
    return {"status": "ok", "settings": active_settings}

def is_echo_of_recent_agent(user_text: str, recent_agent_text: str) -> bool:
    """Mendeteksi apakah input user merupakan gema / suara bocor dari speaker agent."""
    if not recent_agent_text or not user_text:
        return False
    u = re.sub(r'[^\w\s]', ' ', user_text.lower()).strip()
    a = re.sub(r'[^\w\s]', ' ', recent_agent_text.lower()).strip()
    u_clean = ' '.join(u.split())
    a_clean = ' '.join(a.split())
    if not u_clean or not a_clean:
        return False
        
    # 1. Jika teks user persis ada di dalam teks jawaban agent atau sebaliknya
    if len(u_clean) >= 6 and (u_clean in a_clean or a_clean in u_clean):
        return True
        
    # 2. Periksa kesamaan kata (token overlap / Jaccard similarity)
    u_words = set(u_clean.split())
    a_words = set(a_clean.split())
    if len(u_words) >= 2:
        overlap = len(u_words.intersection(a_words))
        ratio = overlap / len(u_words)
        if ratio >= 0.55:  # 55% atau lebih kata user berasal dari kalimat agent
            return True
            
    return False

@web_server.post("/api/submit-speech")
async def submit_speech(payload: SpeechPayload):
    global agent_busy
    text = payload.text.strip()
    if not text:
        return {"status": "empty"}

    is_busy = agent_busy or (player_global.is_playing() if player_global else False)
    if is_busy:
        return {"status": "busy", "message": "AI sedang berbicara, input mic ditolak otomatis."}

    last_agent_text = latest_chat.get("agent", "")
    if is_echo_of_recent_agent(text, last_agent_text):
        print(f"\n\033[33m[🛡️ Anti-Loop Filter] Web Mic menolak gema speaker AI: \"{text}\"\033[0m")
        return {"status": "echo_ignored", "message": "Gema speaker diabaikan."}

    agent_busy = True
    active_settings["engine"] = payload.engine
    active_settings["voice"] = payload.voice
    latest_chat["user"] = text
    latest_chat["source"] = "voice"
    latest_chat["agent"] = "..."
    latest_chat["is_streaming"] = True
    latest_chat["timestamp"] = time.time()
    input_queue.put(("voice", text, payload.engine, payload.voice))
    return {"status": "success", "text": text}

def find_available_port(start_port: int = 7860) -> int:
    """Mencari port yang bebas untuk server web jika port utama sedang dipakai."""
    for p in range(start_port, start_port + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('0.0.0.0', p))
                return p
            except OSError:
                continue
    return start_port

def start_web_server(port: int = 7860):
    config = uvicorn.Config(
        app=web_server,
        host="0.0.0.0",
        port=port,
        log_level="error"
    )
    server = uvicorn.Server(config)
    server.install_signal_handlers = lambda: None
    server.run()

BANNER = """
\033[1;36m================================================================================\033[0m
\033[1;37m          TERMINAL VOICE & TEXT CHAT (DENGAN WEB MIC CONTROLLER)\033[0m
\033[1;36m================================================================================\033[0m
\033[38;5;215mWeb Controller : http://localhost:{port} (atau http://127.0.0.1:{port})\033[0m
* Buka URL di browser Windows untuk kontrol Mic STT & Pilihan Suara.
* Output teks User diformat rapi seperti baris prompt CLI (text.png).
* Respons AI dicetak secara streaming di terminal dan disuarakan via TTS.
* Tombol Stop Audio & Stop Aplikasi tersedia di Web UI dan terminal (/exit).
\033[1;36m================================================================================\033[0m
"""

def print_terminal_header(model_name: str):
    """Mencetak status bar atas persis seperti text.png"""
    header = f"☤ | {model_name} | ~29.3K/1M [░░░░░░░░] ~3% | ◎ 62.1% | $ 0.00"
    print(f"\n\033[1;33m{header}\033[0m")

def print_prompt_box(text: str, source: str = "voice"):
    """Mencetak baris input user dengan gaya border prompt persis seperti text.png"""
    border_color = "\033[38;5;209m"  # Peach/Salmon line
    reset = "\033[0m"
    prompt_sym = "\033[1;36m>\033[0m"
    label = f"\033[38;5;246m[{source.upper()}]\033[0m " if source == "voice" else ""
    text_color = "\033[38;5;215m"    # Amber/orange prompt text
    
    line = border_color + ("─" * 74) + reset
    print(line)
    print(f"{prompt_sym} {label}{text_color}{text}{reset}")
    print(f"{line}")

def main():
    global tts_global, player_global, llm_global, syncer_global, app_running, agent_busy
    requested_port = int(os.environ.get("PORT", "7860"))
    port = find_available_port(requested_port)
    
    server_thread = threading.Thread(target=start_web_server, args=(port,), daemon=True)
    server_thread.start()

    print(BANNER.format(port=port))
    print(f"[Ready] Web Controller aktif di http://localhost:{port}")
    print("Menginisialisasi mesin AI dan TTS...")

    tts_global = TTSEngine(default_engine=active_settings["engine"])
    player_global = AudioPlayer()
    llm_global = LLMClient()
    syncer_global = StreamSynchronizer(tts_global, player_global)

    print(f"[Status] Engine Default : {active_settings['engine'].upper()} (Alami) | Voice: {active_settings['voice']}")
    print("[Siap] Bicara lewat Web Mic atau ketik pesan di terminal:\n")

    system_prompt = (
        "Kamu adalah asisten AI suara yang cerdas, ramah, dan ringkas. "
        "Jawab pertanyaan secara to-the-point dan jelas dalam bahasa yang sama dengan pengguna. "
        "Hindari format markdown yang terlalu rumit (seperti tabel besar atau tanda bintang berlebih) "
        "karena jawabanmu akan dibacakan langsung melalui suara."
    )
    history = [{"role": "system", "content": system_prompt}]

    stdin_active = True
    while app_running:
        try:
            message_item = None

            # 1. Periksa apakah ada suara masuk dari Web Mic
            try:
                message_item = input_queue.get_nowait()
            except queue.Empty:
                pass

            # 2. Periksa apakah ada ketikan dari keyboard terminal
            if not message_item and stdin_active:
                try:
                    rlist, _, _ = select.select([sys.stdin], [], [], 0.05)
                    if rlist:
                        line = sys.stdin.readline()
                        if not line:
                            stdin_active = False
                        else:
                            raw_text = line.strip()
                            if raw_text:
                                message_item = ("keyboard", raw_text, active_settings["engine"], active_settings["voice"])
                except Exception:
                    stdin_active = False

            if not message_item:
                time.sleep(0.01)
                continue

            source = message_item[0]
            text = message_item[1]
            engine = message_item[2] if len(message_item) > 2 else active_settings["engine"]
            voice = message_item[3] if len(message_item) > 3 else active_settings["voice"]

            if text.lower() in ["/exit", "exit", "quit"]:
                print("\nSampai jumpa!")
                player_global.stop()
                os._exit(0)

            if text == "/clear":
                history = [{"role": "system", "content": system_prompt}]
                player_global.clear()
                latest_chat["user"] = ""
                latest_chat["agent"] = ""
                latest_chat["is_streaming"] = False
                print("\n[Info] Riwayat percakapan telah dibersihkan.\n")
                continue

            # Proteksi Gema di Loop Utama
            last_agent_text = ""
            for msg in reversed(history):
                if msg.get("role") == "assistant" and msg.get("content"):
                    last_agent_text = msg["content"]
                    break

            if source == "voice" and is_echo_of_recent_agent(text, last_agent_text):
                print(f"\n\033[33m[🛡️ Anti-Loop Filter] Mengabaikan gema speaker: \"{text}\"\033[0m\n")
                continue

            agent_busy = True
            latest_chat["user"] = text
            latest_chat["source"] = source
            latest_chat["agent"] = ""
            latest_chat["is_streaming"] = True
            latest_chat["timestamp"] = time.time()

            # Cetak status bar & kotak prompt persis seperti text.png
            print_terminal_header(active_settings["model"])
            print_prompt_box(text, source=source)

            history.append({"role": "user", "content": text})

            def on_token_callback(tok: str):
                latest_chat["agent"] += tok

            # Eksekusi LLM Streaming & TTS ke Terminal
            token_gen = llm_global.stream_chat(history, model=active_settings["model"])
            
            agent_response = syncer_global.process_stream(
                token_gen,
                engine=engine,
                voice=voice,
                prefix="\033[1;32mAgent : \033[0m",
                on_token=on_token_callback
            )

            history.append({"role": "assistant", "content": agent_response})
            latest_chat["agent"] = agent_response
            latest_chat["is_streaming"] = False
            print()

            # Tunggu hingga audio selesai diputar di speaker sebelum membuka kunci input suara
            if player_global:
                player_global.wait_until_done()
            time.sleep(0.6)  # Jeda pendinginan ruangan agar gema hilang

            agent_busy = False

        except KeyboardInterrupt:
            print("\nKeluar dari aplikasi...")
            break
        except Exception as e:
            agent_busy = False
            latest_chat["is_streaming"] = False
            print(f"\n[Error] {e}\n")

    if player_global:
        player_global.stop()

if __name__ == "__main__":
    main()
