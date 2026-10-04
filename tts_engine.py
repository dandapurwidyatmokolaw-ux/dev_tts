"""
TTS Engine Module for Terminal Voice Chat.
Supports:
1. Edge-TTS (Natural Indonesian / English, online, free, zero-latency)
2. Local Kokoro-82M ONNX (GPU CUDA accelerated, ultra-fast, offline)
3. F5-TTS (Flow-matching diffusion transformer, natural voice cloning on GPU)
"""

import os
import sys
import glob
import ctypes
import tempfile
import asyncio
import numpy as np
import soundfile as sf

# 1. Bootstrap NVIDIA CUDA libraries if available in site-packages
def _bootstrap_cuda_libs():
    base_venv = os.path.dirname(os.path.dirname(sys.executable))
    nvidia_dir = os.path.join(base_venv, "lib", "python3.11", "site-packages", "nvidia")
    if os.path.exists(nvidia_dir):
        for lib_dir in glob.glob(f"{nvidia_dir}/*/lib"):
            if lib_dir not in os.environ.get("LD_LIBRARY_PATH", ""):
                os.environ["LD_LIBRARY_PATH"] = lib_dir + ":" + os.environ.get("LD_LIBRARY_PATH", "")
            for so in glob.glob(f"{lib_dir}/*.so*"):
                try:
                    ctypes.CDLL(so)
                except Exception:
                    pass

_bootstrap_cuda_libs()

try:
    import kokoro_onnx.session
    kokoro_onnx.session.resolve_providers = lambda: ["CUDAExecutionProvider", "CPUExecutionProvider"]
    from kokoro_onnx import Kokoro
    KOKORO_AVAILABLE = True
except ImportError:
    KOKORO_AVAILABLE = False

try:
    import edge_tts
    EDGE_AVAILABLE = True
except ImportError:
    EDGE_AVAILABLE = False

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

F5_VOICE_PRESETS = {
    "f5_gadis": {
        "label": "Gadis (F5 Voice Clone - Wanita ID)",
        "ref_file": os.path.join(BASE_DIR, "voices_f5", "id_gadis.wav"),
        "ref_text": "Halo, saya adalah asisten kecerdasan buatan interaktif. Saya siap membantu Anda kapan saja."
    },
    "f5_ardi": {
        "label": "Ardi (F5 Voice Clone - Pria ID)",
        "ref_file": os.path.join(BASE_DIR, "voices_f5", "id_ardi.wav"),
        "ref_text": "Selamat datang di sistem percakapan suara terminal. Ada yang bisa saya bantu hari ini?"
    },
    "f5_jenny": {
        "label": "Jenny (F5 Voice Clone - English)",
        "ref_file": os.path.join(BASE_DIR, "voices_f5", "en_jenny.wav"),
        "ref_text": "Hello, I am your intelligent voice assistant, ready to help you with your daily tasks."
    }
}

class TTSEngine:
    def __init__(
        self,
        default_engine: str = "edge",
        kokoro_model_path: str = None,
        kokoro_voices_path: str = None,
        default_kokoro_voice: str = "af_sarah",
        default_edge_voice: str = "id-ID-GadisNeural",
        default_f5_voice: str = "f5_gadis"
    ):
        if kokoro_model_path is None:
            kokoro_model_path = os.path.join(BASE_DIR, "models", "kokoro-v1.0.onnx")
        if kokoro_voices_path is None:
            kokoro_voices_path = os.path.join(BASE_DIR, "models", "voices-v1.0.bin")
        self.default_engine = default_engine
        self.default_kokoro_voice = default_kokoro_voice
        self.default_edge_voice = default_edge_voice
        self.default_f5_voice = default_f5_voice
        self.kokoro = None
        self.f5 = None

        if default_engine == "kokoro" and KOKORO_AVAILABLE:
            if os.path.exists(kokoro_model_path) and os.path.exists(kokoro_voices_path):
                try:
                    self.kokoro = Kokoro(kokoro_model_path, kokoro_voices_path)
                    self.kokoro.create("Warmup.", voice=self.default_kokoro_voice)
                except Exception as e:
                    print(f"[TTS Warning] Gagal memuat Kokoro: {e}. Fallback ke edge-tts.")
                    self.default_engine = "edge"
            else:
                self.default_engine = "edge"

    def _ensure_f5_loaded(self):
        """Memuat model F5-TTS secara lazy ke GPU CUDA saat pertama kali dipanggil."""
        if self.f5 is not None:
            return True

        ckpt_path = os.path.join(BASE_DIR, "models", "F5TTS_v1_Base", "model_1250000.safetensors")
        vocab_path = os.path.join(BASE_DIR, "models", "F5TTS_v1_Base", "vocab.txt")

        if not os.path.exists(ckpt_path) or not os.path.exists(vocab_path):
            print("[F5-TTS Error] File model safetensors / vocab tidak ditemukan.")
            return False

        try:
            import torch
            import torchaudio

            # Patch torchaudio dengan soundfile agar kompatibel penuh
            def soundfile_load(filepath, *args, **kwargs):
                data, sr = sf.read(filepath, dtype='float32')
                tensor = torch.from_numpy(data)
                if tensor.ndim == 1:
                    tensor = tensor.unsqueeze(0)
                elif tensor.ndim == 2 and tensor.shape[0] > tensor.shape[1]:
                    tensor = tensor.T
                return tensor, sr

            def soundfile_save(filepath, src, sample_rate, *args, **kwargs):
                arr = src.detach().cpu().numpy()
                if arr.ndim == 2 and arr.shape[0] <= 2:
                    arr = arr.T
                sf.write(filepath, arr, sample_rate)

            torchaudio.load = soundfile_load
            torchaudio.save = soundfile_save

            os.environ["HF_HOME"] = os.path.join(BASE_DIR, "models", "huggingface")
            from f5_tts.api import F5TTS

            dev = "cuda" if torch.cuda.is_available() else "cpu"
            print(f"[TTS] Memuat bobot F5-TTS (SWivid/F5-TTS) ke perangkat {dev.upper()}...")
            self.f5 = F5TTS(
                model="F5TTS_v1_Base",
                ckpt_file=ckpt_path,
                vocab_file=vocab_path,
                device=dev,
                hf_cache_dir=os.path.join(BASE_DIR, "models", "huggingface")
            )
            print("[TTS] F5-TTS (SWivid/F5-TTS) berhasil dimuat dan siap digunakan!")
            return True
        except Exception as e:
            print(f"[TTS Error] Gagal inisialisasi F5-TTS: {e}. Fallback ke Edge-TTS.")
            return False

    def synthesize(self, text: str, engine: str = None, voice: str = None, output_path: str = None) -> str:
        """
        Sintesis teks menjadi file audio.
        Mengembalikan path file audio yang dihasilkan.
        """
        engine = engine or self.default_engine
        text = text.strip()
        if not text:
            return ""

        if engine == "f5":
            return self._synthesize_f5(text, voice=voice or self.default_f5_voice, output_path=output_path)
        elif engine == "kokoro" and self.kokoro:
            return self._synthesize_kokoro(text, voice=voice or self.default_kokoro_voice, output_path=output_path)
        else:
            return self._synthesize_edge(text, voice=voice or self.default_edge_voice, output_path=output_path)

    def _synthesize_f5(self, text: str, voice: str, output_path: str = None) -> str:
        if not self._ensure_f5_loaded():
            return self._synthesize_edge(text, voice=self.default_edge_voice, output_path=output_path)

        tmp_dir = os.path.join(BASE_DIR, "tmp_audio")
        os.makedirs(tmp_dir, exist_ok=True)
        if not output_path:
            fd, output_path = tempfile.mkstemp(suffix=".wav", prefix="f5_", dir=tmp_dir)
            os.close(fd)

        preset = F5_VOICE_PRESETS.get(voice, F5_VOICE_PRESETS["f5_gadis"])
        try:
            self.f5.infer(
                ref_file=preset["ref_file"],
                ref_text=preset["ref_text"],
                gen_text=text,
                file_wave=output_path,
                nfe_step=16,
                target_rms=0.1
            )
            return output_path
        except Exception as e:
            print(f"[F5-TTS Error] {e}. Fallback ke Edge-TTS.")
            return self._synthesize_edge(text, voice=self.default_edge_voice, output_path=output_path)

    def _synthesize_kokoro(self, text: str, voice: str, output_path: str = None) -> str:
        tmp_dir = os.path.join(BASE_DIR, "tmp_audio")
        os.makedirs(tmp_dir, exist_ok=True)
        if not output_path:
            fd, output_path = tempfile.mkstemp(suffix=".wav", prefix="kokoro_", dir=tmp_dir)
            os.close(fd)

        try:
            samples, sr = self.kokoro.create(text, voice=voice, speed=1.0, lang="en-us")
            sf.write(output_path, samples, sr)
            return output_path
        except Exception as e:
            if EDGE_AVAILABLE:
                return self._synthesize_edge(text, voice=self.default_edge_voice, output_path=output_path)
            raise e

    def _synthesize_edge(self, text: str, voice: str, output_path: str = None) -> str:
        tmp_dir = os.path.join(BASE_DIR, "tmp_audio")
        os.makedirs(tmp_dir, exist_ok=True)
        if not output_path:
            fd, output_path = tempfile.mkstemp(suffix=".mp3", prefix="edge_", dir=tmp_dir)
            os.close(fd)

        async def _run():
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(output_path)

        asyncio.run(_run())
        return output_path

    def get_available_voices(self, engine: str = None):
        engine = engine or self.default_engine
        if engine == "f5":
            return list(F5_VOICE_PRESETS.keys())
        elif engine == "kokoro":
            if self.kokoro:
                return self.kokoro.get_voices()
            return ["af_sarah", "af_bella", "af_alloy", "af_heart", "am_adam", "am_echo", "am_eric", "bm_george"]
        return ["id-ID-GadisNeural", "id-ID-ArdiNeural", "en-US-JennyNeural", "en-US-GuyNeural", "ja-JP-NanamiNeural"]
