# PRD: Terminal Voice & Text Conversational Chat System
**Dokumen Kebutuhan Produk & Desain Arsitektur (PRD v1.0.0)**
**Lokasi Proyek:** `/mnt/d/dev_tts/`

---

## 1. Latar Belakang & Tujuan
Sistem ini dirancang untuk menghadirkan asisten AI interaktif di terminal dengan spesifikasi utama:
1. **Lokal, Gratis, & Cepat (Ultra Low Latency):** Menggunakan model TTS open-weight **Kokoro-82M (ONNX)** dengan akselerasi GPU CUDA (RTX 3050) serta fallback ke **Edge TTS**.
2. **Sinkronisasi Teks & Suara di Terminal:** Teks percakapan (baik ketikan user maupun respons agent) **tetap tampil penuh di layar terminal** secara streaming real-time, sementara audio di-generate dan diputar di latar belakang secara asinkron.
3. **Interleaved Streaming:** Audio kalimat pertama mulai disintesis dan diputar tanpa harus menunggu LLM menyelesaikan seluruh paragraf jawaban.

---

## 2. Kebutuhan Fungsional (Functional Requirements)

### FR-1: Antarmuka Terminal Terlihat (Visible Terminal UI)
- Input percakapan user ditampilkan dengan format: `User : <pesan>`
- Output respons agent ditampilkan secara streaming: `Agent: <kata demi kata streaming>`
- Teks tidak boleh tertutup, terhapus, atau hilang saat audio sedang diputar.

### FR-2: Mesin Suara (Dual TTS Engine)
- **Engine Utama (Local Offline):** `Kokoro-82M ONNX`
  - Kecepatan: Realtime factor < 0.3x (memproses 8 detik suara dalam < 2 detik di GPU RTX 3050).
  - Voice preset: `af_sarah`, `af_bella`, `am_adam`, `bm_george`, dll.
  - 100% offline, tanpa kuota, tanpa API key.
- **Engine Alternatif (Online High-Quality ID):** `Edge-TTS`
  - Mendukung Bahasa Indonesia alami (`id-ID-ArdiNeural` / `id-ID-GadisNeural`).
  - Gratis tanpa API key.

### FR-3: Sub-Sistem Pemutaran Audio Asinkron (Async Audio Queue)
- Audio diproses dan diputar pada background thread / async task tanpa memblokir perputaran token teks terminal.
- Mendukung pemutaran audio di lingkungan WSL -> Windows Host (`powershell.exe Media.SoundPlayer` / `ffplay`).

### FR-4: Konektivitas LLM Streaming
- Terhubung langsung ke 9router lokal (`http://127.0.0.1:20128/v1`) atau endpoint OpenAI-compatible lainnya.
- Memproses output streaming token dan memecah kalimat berdasarkan tanda baca (`.`, `!`, `?`, `\n`) untuk dikirim ke TTS pipeline.

---

## 3. Rencana Fase Implementasi & Pengujian

### Fase 1: Spesifikasi PRD & Struktur Proyek
- Pembuatan PRD v1.0.0 (`PRD_voice_chat.md`).
- Struktur folder, virtualenv, dan manajemen model.

### Fase 2: Pengujian Mesin Suara Lokal (Kokoro & Edge-TTS)
- Setup weights `kokoro-v1.0.onnx` dan `voices-v1.0.bin`.
- Verifikasi CUDA Execution Provider pada GPU RTX 3050.
- Skrip unit test TTS (`test_tts_engine.py`) untuk mengukur latensi inferensi dan kualitas audio.

### Fase 3: Audio Playback Subsystem (WSL to Host Bridge)
- Modul pemutar audio (`audio_player.py`) yang mengelola antrean audio (audio queue) non-blocking.
- Uji coba pemutaran sekuensial multi-kalimat tanpa tumpang tindih.

### Fase 4: LLM Streaming & Terminal Text Synchronizer
- Modul integrasi LLM (`llm_client.py`) dengan 9router.
- Modul sentence chunker (`sentence_splitter.py`) yang memisahkan teks token sambil tetap mencetak ke layar terminal seketika (`stdout.flush()`).

### Fase 5: Aplikasi Chat Interaktif Penuh (`chat_terminal.py`)
- Penggabungan seluruh modul menjadi aplikasi CLI chat utuh.
- Opsi switch voice, mode tts (kokoro vs edge-tts).
- Verifikasi user text tetap muncul dan agent streaming bekerja lancar bersama audio.

### Fase 6: Validasi End-to-End & Dokumentasi Panduan Penggunaan
- Pengujian skenario percakapan multi-turn.
- Dokumentasi `README.md` dan checklist hasil tes per fase.
