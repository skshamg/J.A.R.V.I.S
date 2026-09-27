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
        ]

    def _normalize_text(self, raw_text: str) -> str:
        normalized = raw_text
        for pattern, replacement in self.phonetic_replacements:
            normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)
        return normalized

    def listen_smart(self, max_duration: int = 35, silence_tolerance: float = 3.0) -> str:
        """
        Dynamically captures audio allowing for complex, long thoughts.
        Tolerates up to 3.0 seconds of mid-sentence thinking pauses.
        """
        chunk_size = int(self.sample_rate * 0.2)
        recorded_frames = []

        speech_started = False
        silence_start_time = None
        start_time = time.time()
        threshold = 360  # Calibrated for ambient laptop microphones

        with sd.InputStream(samplerate=self.sample_rate, channels=1, dtype="int16") as stream:
            while (time.time() - start_time) < max_duration:
                data, _ = stream.read(chunk_size)
                audio_array = np.frombuffer(data, dtype=np.int16)
                volume = np.sqrt(np.mean(audio_array.astype(float) ** 2))

                recorded_frames.append(data)

                if volume > threshold:
                    speech_started = True
                    silence_start_time = None
                elif speech_started:
                    if silence_start_time is None:
                        silence_start_time = time.time()
                    elif (time.time() - silence_start_time) > silence_tolerance:
                        # User has concluded speaking
                        break
                elif (time.time() - start_time) > 5.5:
                    # No speech detected within the initial 5.5 seconds
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

            return self._normalize_text(raw_text.strip())
        except Exception:
            if os.path.exists(self.temp_wav):
                os.remove(self.temp_wav)
            return ""