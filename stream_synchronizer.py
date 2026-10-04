"""
Stream Synchronizer Module.
Handles:
1. Instant terminal rendering (token-by-token stdout stream).
2. Sentence-boundary detection.
3. Asynchronous TTS synthesis & background audio queuing.
"""

import sys
import re
import concurrent.futures
from typing import Callable, Generator

# Karakter pemisah kalimat umum
SENTENCE_SPLIT_REGEX = re.compile(r'([.?!:\n]+(?:\s+|$))')

def clean_text_for_tts(text: str) -> str:
    """Bersihkan karakter markdown agar TTS membaca dengan natural."""
    # Hapus bold/italic markers (*, _, ~)
    text = re.sub(r'[*_~`#>]', '', text)
    # Hapus link markdown [text](url) -> text
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    # Hapus whitespace berlebih
    text = re.sub(r'\s+', ' ', text).strip()
    return text

class StreamSynchronizer:
    def __init__(self, tts_engine, audio_player, max_workers: int = 2):
        self.tts = tts_engine
        self.player = audio_player
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)

    def _synthesize_and_enqueue(self, sentence: str, engine: str, voice: str):
        clean_sentence = clean_text_for_tts(sentence)
        if not clean_sentence or len(clean_sentence) < 2:
            return
        try:
            audio_path = self.tts.synthesize(clean_sentence, engine=engine, voice=voice)
            if audio_path:
                self.player.play(audio_path)
        except Exception as e:
            # TTS failure should never crash the conversation
            pass

    def process_stream(
        self,
        token_generator: Generator[str, None, None],
        engine: str = "kokoro",
        voice: str = None,
        prefix: str = "Agent: ",
        on_token: Callable[[str], None] = None
    ) -> str:
        """
        Memproses token stream dari LLM:
        - Mencetak token ke terminal secara real-time.
        - Memotong per kalimat dan mengirim ke TTS worker secara asinkron.
        - Mengembalikan teks respons lengkap.
        """
        # Cetak prefix (misal: "Agent: ")
        if prefix:
            sys.stdout.write(prefix)
            sys.stdout.flush()

        full_response = ""
        current_buffer = ""
        futures = []

        for token in token_generator:
            full_response += token
            current_buffer += token

            # 1. Cetak seketika ke terminal
            if on_token:
                on_token(token)
            else:
                sys.stdout.write(token)
                sys.stdout.flush()

            # 2. Deteksi pemisah kalimat
            # Jika ada tanda baca pemisah atau newline
            matches = list(SENTENCE_SPLIT_REGEX.finditer(current_buffer))
            if matches:
                # Ambil sampai akhir match terakhir
                last_end = matches[-1].end()
                sentence = current_buffer[:last_end].strip()
                current_buffer = current_buffer[last_end:]

                if len(sentence) >= 3:
                    f = self.executor.submit(self._synthesize_and_enqueue, sentence, engine, voice)
                    futures.append(f)

        # 3. Proses sisa buffer terakhir jika ada
        if current_buffer.strip():
            f = self.executor.submit(self._synthesize_and_enqueue, current_buffer.strip(), engine, voice)
            futures.append(f)

        # 4. Tunggu SEMUA task sintesis selesai memasukkan audio ke AudioPlayer antrean
        if futures:
            concurrent.futures.wait(futures)

        sys.stdout.write("\n")
        sys.stdout.flush()

        return full_response
