"""
Audio Player Module for WSL & Windows Host.
Manages a background queue to play synthesized audio sequentially without blocking the terminal UI.
Includes process-level interruption (immediate cut-off/stop) and playback state tracking.
"""

import os
import subprocess
import threading
import queue
import time
import shutil

class AudioPlayer:
    def __init__(self, tmp_dir: str = None):
        if tmp_dir is None:
            tmp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tmp_audio")
        self.tmp_dir = tmp_dir
        os.makedirs(self.tmp_dir, exist_ok=True)
        self.audio_queue = queue.Queue()
        self._stop_event = threading.Event()
        self.current_process = None
        self._is_playing = False
        self._lock = threading.Lock()
        self._worker_thread = threading.Thread(target=self._playback_worker, daemon=True)
        self._worker_thread.start()

    def _to_windows_path(self, wsl_path: str) -> str:
        """Konversi path WSL (/mnt/d/...) menjadi path Windows (D:\\...)."""
        abs_path = os.path.abspath(wsl_path)
        if abs_path.startswith("/mnt/"):
            parts = abs_path.split("/")
            drive_letter = parts[2].upper()
            rest = "\\".join(parts[3:])
            return f"{drive_letter}:\\{rest}"
        clean_path = abs_path.replace("/", "\\")
        return f"\\\\wsl$\\Ubuntu{clean_path}"

    def _ensure_wav(self, file_path: str) -> str:
        """
        Pastikan format audio adalah WAV PCM 16-bit mono 24kHz.
        Format ini dijamin 100% kompatibel dan bersuara jernih di Windows Media.SoundPlayer.
        """
        target_name = f"play_{int(time.time()*1000)}_{os.path.splitext(os.path.basename(file_path))[0]}.wav"
        target_path = os.path.join(self.tmp_dir, target_name)
        
        # Selalu standardisasi via ffmpeg ke PCM 16-bit 24kHz mono
        cmd = [
            "ffmpeg", "-y", "-i", file_path,
            "-ac", "1",
            "-ar", "24000",
            "-c:a", "pcm_s16le",
            target_path
        ]
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if res.returncode == 0 and os.path.exists(target_path):
            return target_path
        return file_path

    def _playback_worker(self):
        """Worker background yang memutar audio dari antrean secara sekuensial."""
        while not self._stop_event.is_set():
            try:
                audio_file = self.audio_queue.get(timeout=0.15)
            except queue.Empty:
                with self._lock:
                    self._is_playing = False
                continue

            if audio_file is None:
                self.audio_queue.task_done()
                break

            with self._lock:
                self._is_playing = True

            target_wav = None
            try:
                target_wav = self._ensure_wav(audio_file)
                win_path = self._to_windows_path(target_wav)
                ps_cmd = f"(New-Object Media.SoundPlayer '{win_path}').PlaySync()"

                with self._lock:
                    self.current_process = subprocess.Popen(
                        ["powershell.exe", "-NoProfile", "-Command", ps_cmd],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )

                self.current_process.wait()
            except Exception as e:
                pass
            finally:
                with self._lock:
                    self.current_process = None
                self.audio_queue.task_done()
                # Bersihkan file temporer
                if target_wav and os.path.exists(target_wav) and target_wav != audio_file:
                    try:
                        os.remove(target_wav)
                    except Exception:
                        pass

        with self._lock:
            self._is_playing = False

    def is_playing(self) -> bool:
        """Cek apakah ada audio yang sedang berbunyi atau mengantre."""
        with self._lock:
            return self._is_playing or not self.audio_queue.empty() or self.current_process is not None

    def play(self, file_path: str):
        """Masukkan file audio ke antrean pemutaran (non-blocking)."""
        if file_path and os.path.exists(file_path):
            self.audio_queue.put(file_path)

    def wait_until_done(self):
        """Tunggu hingga semua antrean audio selesai diputar."""
        self.audio_queue.join()

    def clear(self):
        """Hentikan antrean dan matikan pemutaran audio saat ini seketika (Instant Cut-off)."""
        with self._lock:
            # Kosongkan antrean
            while not self.audio_queue.empty():
                try:
                    self.audio_queue.get_nowait()
                    self.audio_queue.task_done()
                except (queue.Empty, ValueError):
                    break

            # Kill proses powershell aktif seketika
            if self.current_process and self.current_process.poll() is None:
                try:
                    self.current_process.kill()
                except Exception:
                    pass
                self.current_process = None
            self._is_playing = False

    def stop(self):
        """Hentikan worker thread."""
        self.clear()
        self._stop_event.set()
        self.audio_queue.put(None)
