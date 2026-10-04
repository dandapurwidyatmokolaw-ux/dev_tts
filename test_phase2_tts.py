"""
Unit Test - Fase 2: Pengujian TTS Engine (Kokoro & Edge-TTS)
Menguji inisialisasi model, sintesis audio, dan mengukur latensi inferensi.
"""

import time
import os
from tts_engine import TTSEngine

def test_fase_2():
    print("=" * 60)
    print("FASE 2: TESTING TTS ENGINE (KOKORO & EDGE-TTS)")
    print("=" * 60)

    # 1. Inisialisasi Engine
    print("[1/3] Menginisialisasi TTSEngine...")
    t0 = time.time()
    tts = TTSEngine(default_engine="kokoro")
    init_time = time.time() - t0
    print(f"-> TTSEngine siap dalam {init_time:.2f} detik.")

    # 2. Test Kokoro TTS (Lokal GPU)
    text_kokoro = "Hello, this is a test of local Kokoro text to speech running on GPU."
    print(f"\n[2/3] Menguji Kokoro-82M (Lokal)...")
    print(f"Teks: \"{text_kokoro}\"")
    t1 = time.time()
    wav_path = tts.synthesize(text_kokoro, engine="kokoro", voice="af_sarah")
    latency_kokoro = time.time() - t1
    file_size_wav = os.path.getsize(wav_path) if os.path.exists(wav_path) else 0

    print(f"-> Hasil File: {wav_path} ({file_size_wav:,} bytes)")
    print(f"-> Latensi Kokoro: {latency_kokoro:.3f} detik")
    assert file_size_wav > 1000, "Kokoro audio output kosong!"

    # 3. Test Edge TTS (Bahasa Indonesia)
    text_edge = "Halo, ini adalah pengujian suara bahasa Indonesia menggunakan Edge TTS."
    print(f"\n[3/3] Menguji Edge-TTS (Bahasa Indonesia)...")
    print(f"Teks: \"{text_edge}\"")
    t2 = time.time()
    mp3_path = tts.synthesize(text_edge, engine="edge", voice="id-ID-ArdiNeural")
    latency_edge = time.time() - t2
    file_size_mp3 = os.path.getsize(mp3_path) if os.path.exists(mp3_path) else 0

    print(f"-> Hasil File: {mp3_path} ({file_size_mp3:,} bytes)")
    print(f"-> Latensi Edge-TTS: {latency_edge:.3f} detik")
    assert file_size_mp3 > 1000, "Edge TTS audio output kosong!"

    print("\n" + "=" * 60)
    print("STATUS FASE 2: 100% SUKSES TERVERIFIKASI!")
    print("=" * 60)

if __name__ == "__main__":
    test_fase_2()
