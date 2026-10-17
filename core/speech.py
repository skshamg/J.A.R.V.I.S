import asyncio
import ctypes
import os
import queue
import re
import subprocess
import tempfile
import threading
import time
import uuid

try:
    import edge_tts
    HAS_EDGE_TTS = True
except ImportError:
    HAS_EDGE_TTS = False

try:
    import pyttsx3
    HAS_PYTTSX3 = True
except ImportError:
    HAS_PYTTSX3 = False

winmm = ctypes.windll.winmm
kernel32 = ctypes.windll.kernel32
ole32 = ctypes.windll.ole32


def _get_short_path(long_path: str) -> str:
    buf = ctypes.create_unicode_buffer(512)
    res = kernel32.GetShortPathNameW(long_path, buf, 512)
    return buf.value if res > 0 else long_path


class SpeechEngine:
    def __init__(self, voice_name: str = "en-GB-RyanNeural"):
        self.voice_name = voice_name
        self.speech_queue = queue.Queue()
        self.stop_event = threading.Event()
        self.lock = threading.Lock()
        self.temp_dir = tempfile.gettempdir()
        self.edge_offline_until = 0.0
        self.active_alias = None
        self.is_speaking = False

        self.worker_thread = threading.Thread(target=self._speech_worker, daemon=True)
        self.worker_thread.start()

    def _clean_for_speech(self, text: str) -> str:
        if not text:
            return ""
        cleaned = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
        cleaned = re.sub(r"[*_`#~>|]", "", cleaned)
        cleaned = re.sub(r"\bJ\.?\s*A\.?\s*R\.?\s*V\.?\s*I\.?\s*S\.?\b", "Jarvis", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\[JARVIS\]", "", cleaned, flags=re.IGNORECASE)
        return re.sub(r"\s+", " ", cleaned).strip()

    def _mci_send(self, command: str) -> tuple[int, str]:
        buf = ctypes.create_unicode_buffer(256)
        err = winmm.mciSendStringW(command, buf, 255, 0)
        return err, buf.value

    def _play_native_mci(self, filepath: str) -> bool:
        alias = f"jarvis_{uuid.uuid4().hex[:6]}"
        self.active_alias = alias
        safe_path = _get_short_path(filepath)

        self._mci_send(f"close {alias}")
        err, _ = self._mci_send(f'open "{safe_path}" type mpegvideo alias {alias}')
        if err != 0:
            err, _ = self._mci_send(f'open "{filepath}" type mpegvideo alias {alias}')
            if err != 0:
                return False

        try:
            err, _ = self._mci_send(f"play {alias}")
            if err != 0:
                return False

            while not self.stop_event.is_set():
                err, status = self._mci_send(f"status {alias} mode")
                if err != 0 or status.lower().strip() not in ("playing", "seeking"):
                    break
                time.sleep(0.03)
            return True
        finally:
            self._mci_send(f"stop {alias}")
            self._mci_send(f"close {alias}")
            self.active_alias = None

    def _play_edge_tts(self, text: str) -> bool:
        if not HAS_EDGE_TTS or time.time() < self.edge_offline_until:
            return False

        mp3_path = os.path.join(self.temp_dir, f"jarvis_tts_{uuid.uuid4().hex[:8]}.mp3")
        try:
            async def _generate():
                communicate = edge_tts.Communicate(text, self.voice_name, rate="+5%")
                await asyncio.wait_for(communicate.save(mp3_path), timeout=2.5)

            asyncio.run(_generate())
            if not os.path.exists(mp3_path) or os.path.getsize(mp3_path) == 0:
                return False

            if self.stop_event.is_set():
                return True

            return self._play_native_mci(mp3_path)
        except Exception:
            self.edge_offline_until = time.time() + 120.0
            return False
        finally:
            try:
                if os.path.exists(mp3_path):
                    os.remove(mp3_path)
            except Exception:
                pass

    def _play_pyttsx3(self, text: str) -> bool:
        if not HAS_PYTTSX3 or self.stop_event.is_set():
            return False
        try:
            engine = pyttsx3.init()
            voices = engine.getProperty("voices")
            for v in voices:
                if any(k in v.name.lower() for k in ("david", "george", "mark", "english")):
                    engine.setProperty("voice", v.id)
                    break
            engine.setProperty("rate", 190)
            engine.say(text)
            engine.runAndWait()
            engine.stop()
            return True
        except Exception:
            return False

    def _speech_worker(self):
        try:
            ole32.CoInitialize(None)
        except Exception:
            pass

        while True:
            text = self.speech_queue.get()
            if text is None:
                self.speech_queue.task_done()
                break

            cleaned = self._clean_for_speech(text)
            if cleaned and not self.stop_event.is_set():
                self.is_speaking = True
                with self.lock:
                    if not self._play_edge_tts(cleaned):
                        self._play_pyttsx3(cleaned)
                self.is_speaking = False

            self.speech_queue.task_done()

    def speak(self, text: str):
        if not text or not text.strip():
            return
        self.stop_event.clear()
        self.speech_queue.put(text)

    def stop(self):
        """Micro-second hard interrupt for barge-in."""
        self.stop_event.set()
        if self.active_alias:
            self._mci_send(f"stop {self.active_alias}")
            self._mci_send(f"close {self.active_alias}")
            self.active_alias = None

        while not self.speech_queue.empty():
            try:
                self.speech_queue.get_nowait()
                self.speech_queue.task_done()
            except queue.Empty:
                break
        self.is_speaking = False


_default_engine = None


def get_engine():
    global _default_engine
    if _default_engine is None:
        _default_engine = SpeechEngine()
    return _default_engine


def speak(text: str):
    get_engine().speak(text)


def stop_speaking():
    get_engine().stop()


def is_speaking() -> bool:
    return get_engine().is_speaking