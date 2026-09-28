import collections
import queue
import re
import threading
import time
import numpy as np
import sounddevice as sd
import speech_recognition as sr


class WakeWordDetector:
    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self.chunk_size = int(self.sample_rate * 0.08)  # 80ms chunks
        self.recognizer = sr.Recognizer()
        
        self.running = True
        self.paused = False
        self.wake_detected = False
        self.lock = threading.Lock()

        # Asynchronous processing queue so HTTP calls never freeze the mic
        self.verify_queue = queue.Queue(maxsize=3)

        # 1. Start background recognition worker
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()

        # 2. Start non-blocking audio capture stream
        self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.capture_thread.start()

        print("[WAKE ENGINE] Asynchronous VAD Phoneme Engine online.")

    def pause(self):
        """Yields mic control exclusively to Ears during active conversation."""
        with self.lock:
            self.paused = True

    def resume(self):
        """Re-arms background listening when returning to standby."""
        with self.lock:
            self.paused = False
            self.wake_detected = False

    def _filter_energy(self, pcm_chunk: np.ndarray) -> float:
        """High-pass filter: kills low-frequency fan drone, humming, and desk rumble."""
        floats = pcm_chunk.astype(float)
        filtered = np.diff(floats, prepend=floats[0])
        return float(np.sqrt(np.mean(filtered**2)))

    def _worker_loop(self):
        """Background thread: verifies wake word without blocking mic ingestion."""
        # Common phonetic transcriptions of "Jarvis" across accents
        targets = [
            r"\bjarvis\b",
            r"\bjavis\b",
            r"\bjervis\b",
            r"\bservice\b",
            r"\bcharvis\b",
            r"\btravis\b",
            r"\bhey\s+jarvis\b",
            r"\bhi\s+jarvis\b",
        ]

        while self.running:
            try:
                audio_bytes = self.verify_queue.get(timeout=0.5)
            except queue.Empty:
                continue

            try:
                audio_data = sr.AudioData(audio_bytes, self.sample_rate, 2)
                text = self.recognizer.recognize_google(audio_data, language="en-IN")
                clean = text.lower().strip()

                for pat in targets:
                    if re.search(pat, clean):
                        print(f"[WAKE HIT] Verified wake phrase: '{clean}'")
                        with self.lock:
                            self.wake_detected = True
                        break
            except Exception:
                # Discard non-speech, hums, or noise bursts cleanly
                pass
            finally:
                self.verify_queue.task_done()

    def _capture_loop(self):
        """Continuous mic ingestion loop with dynamic VAD and pre-roll padding."""
        ring_buffer = collections.deque(maxlen=6)  # 480ms pre-roll to catch the start of speech
        current_utterance = []
        is_speaking = False
        silence_chunks = 0
        baseline_energy = 40.0

        try:
            with sd.InputStream(samplerate=self.sample_rate, channels=1, dtype="int16") as stream:
                while self.running:
                    if self.paused:
                        time.sleep(0.08)
                        ring_buffer.clear()
                        current_utterance.clear()
                        is_speaking = False
                        continue

                    data, _ = stream.read(self.chunk_size)
                    arr = np.frombuffer(data, dtype=np.int16)
                    energy = self._filter_energy(arr)

                    # Dynamic ambient noise floor tracking
                    baseline_energy = baseline_energy * 0.95 + energy * 0.05
                    trigger_threshold = max(110.0, baseline_energy * 2.0)

                    if not is_speaking:
                        ring_buffer.append(data)
                        if energy > trigger_threshold:
                            # Speech detected: stitch the pre-roll so the first syllable isn't cut off
                            is_speaking = True
                            current_utterance = list(ring_buffer)
                            silence_chunks = 0
                    else:
                        current_utterance.append(data)

                        if energy < trigger_threshold:
                            silence_chunks += 1
                        else:
                            silence_chunks = 0

                        # Natural sentence pause: 400ms (5 chunks) of silence OR 1.8s max word length
                        if silence_chunks >= 5 or len(current_utterance) >= 23:
                            # Only process clips that are at least 0.5s long (prevents keyclick triggers)
                            if len(current_utterance) >= 7:
                                full_clip = b"".join(current_utterance)
                                if not self.verify_queue.full():
                                    self.verify_queue.put_nowait(full_clip)

                            current_utterance.clear()
                            is_speaking = False
                            silence_chunks = 0

        except Exception as e:
            print(f"[WAKE CAPTURE ERROR] {e}")

    def poll_for_wake_phrase(self) -> bool:
        """Instant non-blocking poll checked by the daemon main loop."""
        with self.lock:
            if self.wake_detected:
                self.wake_detected = False
                return True
        return False

    def close(self):
        self.running = False