#!/usr/bin/env python3
"""
Terminal Voice & Text Conversational Chat Agent.
Lokasi: /mnt/d/dev_tts/chat_terminal.py

Fitur:
- Output teks User dan Agent selalu terlihat jelas di terminal secara streaming.
- Sintesis suara lokal ultra-cepat (Kokoro 82M GPU) atau Edge TTS (ID).
- Audio diputar di latar belakang secara asinkron tanpa lag.
- Menjaga konteks percakapan multi-turn.
- Perintah interaktif: /engine, /voice, /voices, /model, /mute, /clear, /exit.
"""

import sys
import os
import argparse

# Tambahkan direktori kerja ke sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tts_engine import TTSEngine
from audio_player import AudioPlayer
from llm_client import LLMClient
from stream_synchronizer import StreamSynchronizer

BANNER = """
================================================================================
           TERMINAL VOICE & TEXT CHAT AGENT (LOCAL FAST TTS)
================================================================================
* Teks User & Agent selalu tercetak streaming di layar terminal.
* Audio disintesis dan diputar secara asinkron via Kokoro GPU / Edge-TTS.
* Perintah khusus:
    /engine [kokoro|edge]  : Ganti mesin TTS
    /voice [nama_suara]    : Ganti suara (contoh: af_sarah, id-ID-ArdiNeural)
    /voices                : Tampilkan daftar suara yang tersedia
    /model [nama_model]    : Ganti model LLM di 9router
    /mute / /unmute        : Nonaktifkan / aktifkan suara audio
    /clear                 : Reset riwayat percakapan
    /exit                  : Keluar dari aplikasi
================================================================================
"""

def main():
    parser = argparse.ArgumentParser(description="Terminal Voice & Text Chat Agent")
    parser.add_argument("--engine", choices=["kokoro", "edge"], default="kokoro", help="Engine TTS default")
    parser.add_argument("--voice", default="af_sarah", help="Voice preset")
    parser.add_argument("--model", default="ag/gemini-3.8-flash-low", help="Model LLM 9router")
    args = parser.parse_args()

    print(BANNER)
    print("Memuat mesin suara dan konfigurasi...")

    current_engine = args.engine
    current_voice = args.voice
    current_model = args.model
    audio_enabled = True

    tts = TTSEngine(default_engine=current_engine)
    player = AudioPlayer()
    llm = LLMClient(default_model=current_model)
    syncer = StreamSynchronizer(tts, player)

    # Prompt sistem
    system_prompt = (
        "Kamu adalah asisten AI suara yang cerdas, ramah, dan ringkas. "
        "Jawab pertanyaan secara to-the-point dan jelas, hindari format markdown "
        "yang terlalu rumit seperti tabel besar karena jawabanmu akan dibacakan via suara."
    )

    history = [{"role": "system", "content": system_prompt}]

    print(f"\n[Status] Engine: {current_engine.upper()} | Voice: {current_voice} | Model: {current_model}")
    print("[Siap] Silakan ketik pesan Anda di bawah ini:\n")

    while True:
        try:
            if not sys.stdin.isatty():
                sys.stdout.write("\033[1;36mUser  : \033[0m")
                sys.stdout.flush()
                raw_line = sys.stdin.readline()
                if not raw_line:
                    break
                user_input = raw_line.strip()
                print(user_input)
            else:
                user_input = input("\033[1;36mUser  : \033[0m").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nKeluar dari aplikasi...")
            break

        if not user_input:
            continue

        # Handler perintah khusus
        if user_input.lower() in ["/exit", "exit", "quit", ":q"]:
            print("Sampai jumpa!")
            break

        if user_input.startswith("/engine"):
            parts = user_input.split()
            if len(parts) > 1 and parts[1].lower() in ["kokoro", "edge"]:
                current_engine = parts[1].lower()
                if current_engine == "edge" and current_voice == "af_sarah":
                    current_voice = "id-ID-ArdiNeural"
                elif current_engine == "kokoro" and current_voice == "id-ID-ArdiNeural":
                    current_voice = "af_sarah"
                print(f"[Info] Engine diganti ke: {current_engine} (Voice aktif: {current_voice})\n")
            else:
                print("[Info] Gunakan: /engine kokoro atau /engine edge\n")
            continue

        if user_input.strip() == "/voices":
            voices = tts.get_available_voices(current_engine)
            print(f"\n[Daftar Voice ({current_engine})]:")
            for i, v in enumerate(voices[:15], 1):
                print(f"  {i}. {v}")
            if len(voices) > 15:
                print(f"  ... dan {len(voices)-15} suara lainnya.")
            print()
            continue

        if user_input.startswith("/voice"):
            parts = user_input.split()
            if len(parts) > 1:
                current_voice = parts[1]
                print(f"[Info] Voice diganti ke: {current_voice}\n")
            else:
                print(f"[Info] Voice saat ini: {current_voice}. Gunakan /voices untuk melihat daftar.\n")
            continue

        if user_input.startswith("/model"):
            parts = user_input.split()
            if len(parts) > 1:
                current_model = parts[1]
                print(f"[Info] Model LLM diganti ke: {current_model}\n")
            else:
                print(f"[Info] Model LLM saat ini: {current_model}\n")
            continue

        if user_input == "/mute":
            audio_enabled = False
            player.clear()
            print("[Info] Suara audio dinonaktifkan (Mode teks saja).\n")
            continue

        if user_input == "/unmute":
            audio_enabled = True
            print("[Info] Suara audio diaktifkan kembali.\n")
            continue

        if user_input == "/clear":
            history = [{"role": "system", "content": system_prompt}]
            player.clear()
            print("[Info] Riwayat percakapan telah direset.\n")
            continue

        # Tambahkan ke riwayat
        history.append({"role": "user", "content": user_input})

        try:
            token_gen = llm.stream_chat(history, model=current_model)

            if audio_enabled:
                agent_response = syncer.process_stream(
                    token_gen,
                    engine=current_engine,
                    voice=current_voice,
                    prefix="\033[1;32mAgent : \033[0m"
                )
            else:
                # Mode mute teks murni
                sys.stdout.write("\033[1;32mAgent : \033[0m")
                agent_response = ""
                for token in token_gen:
                    agent_response += token
                    sys.stdout.write(token)
                    sys.stdout.flush()
                sys.stdout.write("\n")
                sys.stdout.flush()

            history.append({"role": "assistant", "content": agent_response})
            print()

        except Exception as e:
            print(f"\n[Error] Terjadi kesalahan: {e}\n")

    player.stop()

if __name__ == "__main__":
    main()
