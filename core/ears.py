import os
import re
import time
import wave
import numpy as np
import sounddevice as sd
import speech_recognition as sr


class EarEngine:
    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self.recognizer = sr.Recognizer()
        self.temp_wav = os.path.abspath("mark2_ear_buffer.wav")

        self.phonetic_replacements = [
            (r"\bmark\s+(to|too|two)\b", "Mark-2"),
            (r"\bmark\s+(one|won)\b", "Mark-1"),
            (r"\b(service|javis|jervis|charvis)\b", "Jarvis"),
            # Phonetic fix: Maps misheard exit cues directly to "abort"
            (r"^\s*(about|a boat|aboard|board|a board)\s*$", "abort"),
            (r"\b(shut down|turn off)\b", "shutdown"),
        ]

    def _normalize_text(self, raw_text: str) -> str:
        normalized = raw_text.strip()
        for pattern, replacement in self.phonetic_replacements:
            normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)
        return normalized

    def _filter_and_get_energy(self, pcm_chunk: np.ndarray) -> float:
        floats = pcm_chunk.astype(float)
        filtered = np.diff(floats, prepend=floats[0])
        return float(np.sqrt(np.mean(filtered**2)))

    def listen_smart(self, max_duration: int = 25, silence_tolerance: float = 2.2) -> str:
        chunk_size = int(self.sample_rate * 0.1)
        recorded_frames = []

        speech_started = False
        silence_start_time = None
        start_time = time.time()

        with sd.InputStream(samplerate=self.sample_rate, channels=1, dtype="int16") as stream:
            init_energies = []
            for _ in range(3):
                data, _ = stream.read(chunk_size)
                arr = np.frombuffer(data, dtype=np.int16)
                init_energies.append(self._filter_and_get_energy(arr))
                recorded_frames.append(data)

            baseline_noise = max(35.0, float(np.mean(init_energies)))
            speech_trigger = baseline_noise * 1.6 + 20.0

            while (time.time() - start_time) < max_duration:
                data, _ = stream.read(chunk_size)
                arr = np.frombuffer(data, dtype=np.int16)
                energy = self._filter_and_get_energy(arr)

                recorded_frames.append(data)

                if energy > speech_trigger:
                    speech_started = True
                    silence_start_time = None
                elif speech_started:
                    if silence_start_time is None:
                        silence_start_time = time.time()
                    elif (time.time() - silence_start_time) >= silence_tolerance:
                        break
                elif (time.time() - start_time) > 5.0:
                    return ""

        if not recorded_frames or not speech_started:
            return ""

        with wave.open(self.temp_wav, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self.sample_rate)
            wf.writeframes(b"".join(recorded_frames))

        try:
            with sr.AudioFile(self.temp_wav) as source:
                audio = self.recognizer.record(source)

            raw_text = self.recognizer.recognize_google(audio, language="en-IN")

            if os.path.exists(self.temp_wav):
                os.remove(self.temp_wav)

            return self._normalize_text(raw_text)
        except Exception:
            if os.path.exists(self.temp_wav):
                os.remove(self.temp_wav)
            return ""