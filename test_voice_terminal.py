"""
Test Verifikasi Integrasi: Web Mic Controller -> Terminal Text Chat & TTS
"""

import subprocess
import os
import time
import urllib.request
import json
import re

def strip_ansi(text: str) -> str:
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)

def test_voice_terminal_integration():
    print("=" * 60)
    print("TEST INTEGRASI: WEB MIC CONTROLLER -> TERMINAL CHAT")
    print("=" * 60)

    # Jalankan voice_terminal_app.py dengan -u dan PORT=7865
    env = os.environ.copy()
    env["PORT"] = "7865"
    proc = subprocess.Popen(
        ["/mnt/d/dev_tts/.venv/bin/python", "-u", "/mnt/d/dev_tts/voice_terminal_app.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=env,
        text=True
    )

    print("[1/4] Menunggu Web Controller aktif...")
    web_ready = False
    for attempt in range(30):
        time.sleep(1)
        try:
            res = urllib.request.urlopen("http://127.0.0.1:7865/api/config", timeout=2)
            if res.status == 200:
                web_ready = True
                print(f"-> Web Controller aktif pada detik ke-{attempt + 1}!")
                break
        except Exception:
            pass

    assert web_ready, "Web Controller gagal aktif!"

    print("[2/4] Menunggu inisialisasi TTS AI selesai...")
    ai_ready = False
    for attempt in range(30):
        time.sleep(1)
        try:
            res = urllib.request.urlopen("http://127.0.0.1:7865/api/status", timeout=1)
            data = json.loads(res.read().decode())
            if data.get("ready"):
                ai_ready = True
                print(f"-> AI & TTS Engine siap pada detik ke-{attempt + 1}!")
                break
        except Exception:
            pass

    assert ai_ready, "AI TTS gagal siap dalam 30 detik!"

    # 3. Simulasikan ucapan suara masuk dari Web Mic (STT masuk)
    print("\n[3/4] Menyimulasikan ucapan suara masuk dari Web Mic...")
    speech_payload = {
        "text": "Halo, tes suara satu dua tiga. Siapa kamu?",
        "engine": "kokoro",
        "voice": "af_sarah"
    }
    req = urllib.request.Request(
        "http://127.0.0.1:7865/api/submit-speech",
        data=json.dumps(speech_payload).encode(),
        headers={"Content-Type": "application/json"}
    )
    urllib.request.urlopen(req)
    print("-> Ucapan suara terkirim dari Web Mic ke Terminal!")

    # Beri waktu LLM menjawab dan mencetak ke terminal
    time.sleep(8)

    # 4. Kirim perintah exit ke terminal stdin
    print("\n[4/4] Menghentikan sesi...")
    proc.stdin.write("exit\n")
    proc.stdin.flush()

    stdout_output, _ = proc.communicate(timeout=10)
    clean_output = strip_ansi(stdout_output)

    print("\n--- [HASIL LOG TERMINAL YANG MUNCUL DI LAYAR] ---")
    print(clean_output)
    print("-------------------------------------------------")

    # Verifikasi bahwa ucapan masuk sebagai teks di terminal
    assert "Suara Masuk" in clean_output, "Label suara masuk tidak muncul di terminal!"
    assert "Halo, tes suara satu dua tiga" in clean_output, "Teks suara user tidak tercetak di terminal!"
    assert "Agent :" in clean_output, "Jawaban Agent tidak tercetak di terminal!"
    assert "Sampai jumpa!" in clean_output, "Keluar tidak bersih!"

    print("\n" + "=" * 60)
    print("STATUS: 100% SUKSES TERVERIFIKASI!")
    print("Suara dari Web Mic berhasil masuk sebagai teks di terminal!")
    print("=" * 60)

if __name__ == "__main__":
    test_voice_terminal_integration()
