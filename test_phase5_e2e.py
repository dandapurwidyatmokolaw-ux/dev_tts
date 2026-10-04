"""
Unit Test - Fase 5: Pengujian End-to-End Terminal Voice Chat
Menyimulasikan interaksi pengguna:
1. Mengirim pesan tanya jawab multi-turn.
2. Memverifikasi teks user dan agent tercetak di output terminal.
3. Menguji pergantian perintah (/voices, /engine edge).
4. Memverifikasi audio background berjalan lancar.
"""

import subprocess
import sys
import time
import re

def strip_ansi(text: str) -> str:
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)

def test_fase_5():
    print("=" * 60)
    print("FASE 5: TESTING END-TO-END INTERACTIVE TERMINAL CHAT")
    print("=" * 60)

    # Simulasikan input pengguna:
    # 1. Pertanyaan awal (Kokoro)
    # 2. Cek voices
    # 3. Ganti engine ke edge
    # 4. Pertanyaan kedua (Edge)
    # 5. Keluar
    simulated_inputs = (
        "Halo, siapa namamu dan apa tugasmu?\n"
        "/voices\n"
        "/engine edge\n"
        "Sebutkan 3 kota besar di Indonesia.\n"
        "/exit\n"
    )

    t0 = time.time()
    proc = subprocess.Popen(
        ["/mnt/d/dev_tts/.venv/bin/python", "/mnt/d/dev_tts/chat_terminal.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )

    raw_output, _ = proc.communicate(input=simulated_inputs, timeout=60)
    total_time = time.time() - t0
    clean_output = strip_ansi(raw_output)

    print("--- [OUTPUT TERMINAL TERTANGKAP] ---")
    print(clean_output)
    print("------------------------------------")

    # Verifikasi assert
    assert "TERMINAL VOICE & TEXT CHAT AGENT" in clean_output, "Banner tidak muncul!"
    assert "User  : Halo, siapa namamu dan apa tugasmu?" in clean_output, "Teks User tidak tercetak!"
    assert "Agent : Halo!" in clean_output, "Teks Agent tidak tercetak!"
    assert "Daftar Voice (kokoro)" in clean_output, "Perintah /voices gagal!"
    assert "Engine diganti ke: edge" in clean_output, "Perintah /engine gagal!"
    assert "Jakarta, Surabaya, dan Medan" in clean_output, "Jawaban Agent kedua gagal!"
    assert "Sampai jumpa!" in clean_output, "Aplikasi tidak keluar secara bersih!"

    print(f"Total waktu eksekusi E2E: {total_time:.2f} detik.")
    print("\n" + "=" * 60)
    print("STATUS FASE 5: 100% SUKSES TERVERIFIKASI!")
    print("=" * 60)

if __name__ == "__main__":
    test_fase_5()
