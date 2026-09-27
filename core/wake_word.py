import collections
import os
import time
import wave
import numpy as np
import sounddevice as sd
import speech_recognition as sr


class WakeWordDetector:
    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self.recognizer = sr.Recognizer()
        self.temp_wav = os.path.abspath("wake_buffer.wav")

        self.keywords = [
            "jarvis", "javis", "jervis", "jarves", "service", 
            "charvis", "mark", "hey mark", "mark 3", "wake up"
        ]

        # 2.2-second circular rolling buffer (keeps audio alive with zero blind spots)
        self.buffer_len = int(sample_rate * 2.2)
        self.audio_ring = collections.deque(maxlen=self.buffer_len)

        # Baseline noise calibration
        self.ambient_energy = 50
        self.is_listening = False
        self.stream = None
        self._init_stream()

    def _audio_callback(self, indata, frames, time_info, status):
        """Continuously feeds the circular buffer in real time."""
        self.audio_ring.extend(indata.flatten())

    def _init_stream(self):
        try:
            self.stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype="int16",
                callback=self._audio_callback,
                blocksize=int(self.sample_rate * 0.1),
            )
            self.stream.start()

            # Calibrate room noise over 0.4 seconds
            time.sleep(0.4)
            if len(self.audio_ring) > 0:
                recent = np.array(self.audio_ring, dtype=float)
                self.ambient_energy = max(35, int(np.sqrt(np.mean(recent**2))))
        except Exception as e:
            print(f"[WAKE ERROR] Stream init failed: {e}")

    def poll_for_wake_phrase(self) -> bool:
        """
        Inspects the continuous audio buffer without shutting off the mic.
        """
        if len(self.audio_ring) < self.buffer_len:
            return False

        # Grab a snapshot of the last 2.2 seconds of audio
        audio_snapshot = np.array(self.audio_ring, dtype=np.int16)
        current_rms = np.sqrt(np.mean(audio_snapshot[-int(self.sample_rate * 0.8):].astype(float) ** 2))

        # Dynamic trigger: voice must rise above room ambient noise
        trigger_threshold = max(110, self.ambient_energy * 1.7)
        if current_rms < trigger_threshold:
            return False

        # Write snapshot buffer for transcription
        with wave.open(self.temp_wav, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self.sample_rate)
            wf.writeframes(audio_snapshot.tobytes())

        try:
            with sr.AudioFile(self.temp_wav) as source:
                audio = self.recognizer.record(source)

            # Query Indian-English model
            text = self.recognizer.recognize_google(audio, language="en-IN").lower()

            if os.path.exists(self.temp_wav):
                os.remove(self.temp_wav)

            if any(kw in text for kw in self.keywords):
                # Clear buffer so it doesn't double-trigger
                self.audio_ring.clear()
                return True

            return False
        except Exception:
            if os.path.exists(self.temp_wav):
                os.remove(self.temp_wav)
            return False

    def close(self):
        if self.stream:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception:
                pass