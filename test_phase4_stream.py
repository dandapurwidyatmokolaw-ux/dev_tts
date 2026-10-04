"""
Unit Test - Fase 4: Pengujian LLM Streaming & Terminal Text Synchronizer
Menguji streaming LLM, penampilan teks kata-per-kata di terminal, dan sintesis audio paralel.
"""

import time
from tts_engine import TTSEngine
from audio_player import AudioPlayer
from llm_client import LLMClient
from stream_synchronizer import StreamSynchronizer

def test_fase_4():
    print("=" * 60)
    print("FASE 4: TESTING LLM STREAMING & TERMINAL SYNCHRONIZER")
    print("=" * 60)

    # 1. Inisialisasi komponen
    print("[1/3] Menginisialisasi komponen...")
    tts = TTSEngine(default_engine="kokoro")
    player = AudioPlayer()
    llm = LLMClient()
    syncer = StreamSynchronizer(tts, player)

    # 2. Kirim pesan prompt
    prompt = "Halo, jelaskan dalam 2 kalimat singkat apa itu kecerdasan buatan."
    messages = [
        {"role": "system", "content": "Kamu adalah asisten AI yang ramah dan to the point."},
        {"role": "user", "content": prompt}
    ]

    print("\n[2/3] Memulai percakapan...")
    print(f"User : {prompt}")

    t0 = time.time()
    token_gen = llm.stream_chat(messages)

    # 3. Proses streaming dengan sinkronisasi teks & audio
    full_text = syncer.process_stream(
        token_gen,
        engine="kokoro",
        voice="af_sarah",
        prefix="Agent: "
    )
    t_stream_done = time.time() - t0
    print(f"\n-> Teks streaming selesai dalam {t_stream_done:.2f} detik.")
    print(f"-> Total karakter respons: {len(full_text)}")
    assert len(full_text) > 10, "Respons LLM terlalu pendek atau gagal!"

    print("\n[3/3] Menunggu sisa pemutaran audio selesai...")
    player.wait_until_done()
    player.stop()

    print("\n" + "=" * 60)
    print("STATUS FASE 4: 100% SUKSES TERVERIFIKASI!")
    print("=" * 60)

if __name__ == "__main__":
    test_fase_4()
