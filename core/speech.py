import asyncio
import ctypes
import os
import queue
import re
import threading
import time
import pyttsx3

try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False

winmm = ctypes.windll.winmm
kernel32 = ctypes.windll.kernel32


def _get_short_path(path: str) -> str:
    """Converts long paths to Windows 8.3 short paths for reliable MCI playback."""
    buf = ctypes.create_unicode_buffer(300)
    kernel32.GetShortPathNameW(path, buf, 300)
    return buf.value if buf.value else path


class SpeechEngine:
    def __init__(self, voice_name: str = "en-GB-RyanNeural"):
        self.voice_name = voice_name
        self.speech_queue = queue.Queue()
        self.stop_event = threading.Event()
        self.lock = threading.Lock()
        self.temp_mp3 = os.path.abspath("jarvis_speech_temp.mp3")

        # Fallback pyttsx3 offline engine
        self.pyttsx3_engine = pyttsx3.init()
        self.pyttsx3_engine.setProperty("rate", 185)
        self.pyttsx3_engine.setProperty("volume", 1.0)
        self._configure_pyttsx3_voice()

        # Dedicated async worker thread
        self.worker = threading.Thread(target=self._speech_worker, daemon=True)
        self.worker.start()

    def _configure_pyttsx3_voice(self):
        try:
            voices = self.pyttsx3_engine.getProperty("voices")
            for v in voices:
                if any(x in v.name.lower() for x in ["david", "george", "mark", "ryan"]):
                    self.pyttsx3_engine.setProperty("voice", v.id)
                    break
        except Exception:
            pass

    def _clean_for_speech(self, text: str) -> str:
        # Prevent acronym spelling: 'J.A.R.V.I.S.' -> 'Jarvis'
        cleaned = re.sub(r"\bJ\.?A\.?R\.?V\.?I\.?S\.?\b", "Jarvis", text, flags=re.IGNORECASE)
        cleaned = re.sub(r"```.*?```", "", cleaned, flags=re.DOTALL)
        cleaned = re.sub(r"https?://\S+|www\.\S+", "web link", cleaned)
        cleaned = re.sub(r"[\*\_#`>\[\]]", "", cleaned)
        return cleaned.strip()

    def _play_native_mci(self, mp3_path: str):
        """Plays MP3 audio natively via Windows MCI (no pygame required)."""
        short_path = _get_short_path(mp3_path)
        winmm.mciSendStringW("close jarvis_voice", None, 0, None)

        open_cmd = f'open "{short_path}" type mpegvideo alias jarvis_voice'
        if winmm.mciSendStringW(open_cmd, None, 0, None) != 0:
            return False

        winmm.mciSendStringW("play jarvis_voice", None, 0, None)

        status_buf = ctypes.create_unicode_buffer(64)
        while True:
            if self.stop_event.is_set():
                winmm.mciSendStringW("stop jarvis_voice", None, 0, None)
                winmm.mciSendStringW("close jarvis_voice", None, 0, None)
                break

            winmm.mciSendStringW("status jarvis_voice mode", status_buf, 64, None)
            mode = status_buf.value.strip().lower()
            if mode in ("stopped", ""):
                winmm.mciSendStringW("close jarvis_voice", None, 0, None)
                break

            time.sleep(0.04)

        return True

    def _play_edge_tts(self, clean_text: str):
        try:
            communicate = edge_tts.Communicate(clean_text, self.voice_name)
            asyncio.run(communicate.save(self.temp_mp3))

            if self.stop_event.is_set():
                return

            if not self._play_native_mci(self.temp_mp3):
                self._play_pyttsx3(clean_text)

        except Exception:
            self._play_pyttsx3(clean_text)
        finally:
            if os.path.exists(self.temp_mp3):
                try:
                    os.remove(self.temp_mp3)
                except Exception:
                    pass

    def _play_pyttsx3(self, clean_text: str):
        try:
            with self.lock:
                self.pyttsx3_engine.say(clean_text)
                self.pyttsx3_engine.runAndWait()
        except Exception as e:
            print(f"[PYTTSX3 ERROR] {e}")

    def _speech_worker(self):
        while True:
            text = self.speech_queue.get()
            if text is None:
                break

            self.stop_event.clear()
            clean_text = self._clean_for_speech(text)

            if clean_text:
                if EDGE_TTS_AVAILABLE:
                    self._play_edge_tts(clean_text)
                else:
                    self._play_pyttsx3(clean_text)

            self.speech_queue.task_done()

    def speak(self, text: str):
        if not text:
            return
        self.speech_queue.put(text)

    def stop(self):
        """Immediately silences speech playback."""
        self.stop_event.set()
        winmm.mciSendStringW("stop jarvis_voice", None, 0, None)
        winmm.mciSendStringW("close jarvis_voice", None, 0, None)

        try:
            with self.lock:
                self.pyttsx3_engine.stop()
        except Exception:
            pass

        while not self.speech_queue.empty():
            try:
                self.speech_queue.get_nowait()
                self.speech_queue.task_done()
            except Exception:
                break