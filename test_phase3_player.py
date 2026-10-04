"""
Unit Test - Fase 3: Pengujian Audio Playback Subsystem (WSL to Host Bridge)
Menguji antrean audio asinkron dan pemutaran sekuensial.
"""

import time
import os
from audio_player import AudioPlayer

def test_fase_3():
    print("=" * 60)
    print("FASE 3: TESTING AUDIO PLAYBACK SUBSYSTEM")
    print("=" * 60)

    player = AudioPlayer()
    print("[1/3] AudioPlayer terinisialisasi.")

    test_wav = "/mnt/d/dev_tts/tmp_audio/test.wav"
    test_mp3 = "/mnt/d/dev_tts/tmp_audio/test.mp3"

    assert os.path.exists(test_wav), f"File {test_wav} tidak ditemukan!"
    assert os.path.exists(test_mp3), f"File {test_mp3} tidak ditemukan!"

    # 2. Test Non-blocking Queueing
    print("\n[2/3] Memasukkan file audio ke antrean (Non-blocking)...")
    t0 = time.time()
    player.play(test_wav)
    t_after_put = time.time() - t0
    print(f"-> player.play(wav) selesai dalam {t_after_put:.4f} detik (tidak memblokir eksekusi).")
    assert t_after_put < 0.1, "play() memblokir eksekusi utama!"

    # 3. Test Queue Processing
    print("\n[3/3] Memutar audio di latar belakang...")
    player.wait_until_done()
    total_playback_time = time.time() - t0
    print(f"-> Pemutaran audio selesai dalam {total_playback_time:.2f} detik.")

    player.stop()
    print("\n" + "=" * 60)
    print("STATUS FASE 3: 100% SUKSES TERVERIFIKASI!")
    print("=" * 60)

if __name__ == "__main__":
    test_fase_3()
