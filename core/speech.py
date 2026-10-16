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
    """Converts a Windows path with spaces into an 8.3 short path if supported."""
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
        self.temp_mp3 = os.path.join(self.temp_dir, "jarvis_speech_temp.mp3")

        self.worker_thread = threading.Thread(target=self._speech_worker, daemon=True)
        self.worker_thread.start()

    def _clean_for_speech(self, text: str) -> str:
        """Removes markdown formatting and forces natural pronunciation of Jarvis."""
        if not text:
            return ""
        cleaned = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
        cleaned = re.sub(r"[*_`#~>|]", "", cleaned)
        cleaned = re.sub(r"\bJ\.?\s*A\.?\s*R\.?\s*V\.?\s*I\.?\s*S\.?\b", "Jarvis", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\[JARVIS\]", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

    def _mci_send(self, command: str) -> tuple[int, str]:
        """Sends a command to Windows Media Control Interface and returns (error_code, response)."""
        buf = ctypes.create_unicode_buffer(256)
        err = winmm.mciSendStringW(command, buf, 255, 0)
        return err, buf.value

    def _play_native_mci(self, filepath: str) -> bool:
        """Plays an MP3 file using native Windows winmm.dll. Returns True if successful."""
        alias = f"jarvis_{uuid.uuid4().hex[:6]}"
        safe_path = _get_short_path(filepath)

        self._mci_send(f"close {alias}")
        err, _ = self._mci_send(f'open "{safe_path}" type mpegvideo alias {alias}')
        if err != 0:
            # Retry with raw path in quotes
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
                time.sleep(0.04)
            return True
        finally:
            self._mci_send(f"stop {alias}")
            self._mci_send(f"close {alias}")

    def _play_edge_tts(self, text: str) -> bool:
        """Generates neural speech via Edge-TTS into the system temp folder and plays it."""
        if not HAS_EDGE_TTS:
            return False

        mp3_path = os.path.join(self.temp_dir, f"jarvis_tts_{uuid.uuid4().hex[:8]}.mp3")
        try:
            async def _generate():
                communicate = edge_tts.Communicate(text, self.voice_name, rate="+5%")
                await communicate.save(mp3_path)

            asyncio.run(_generate())

            if not os.path.exists(mp3_path) or os.path.getsize(mp3_path) == 0:
                return False

            if self.stop_event.is_set():
                return True

            return self._play_native_mci(mp3_path)
        except Exception as e:
            print(f"[TTS Edge Fallback Notice]: {e}")
            return False
        finally:
            try:
                if os.path.exists(mp3_path):
                    os.remove(mp3_path)
            except Exception:
                pass

    def _configure_pyttsx3_voice(self, engine):
        """Selects the best English voice available in local SAPI5."""
        try:
            voices = engine.getProperty("voices")
            for v in voices:
                if any(k in v.name.lower() for k in ("david", "george", "hazel", "mark", "english")):
                    engine.setProperty("voice", v.id)
                    break
            engine.setProperty("rate", 185)
            engine.setProperty("volume", 1.0)
        except Exception:
            pass

    def _play_pyttsx3(self, text: str) -> bool:
        """Offline fallback using pyttsx3 with COM initialized."""
        if not HAS_PYTTSX3 or self.stop_event.is_set():
            return False
        try:
            engine = pyttsx3.init()
            self._configure_pyttsx3_voice(engine)
            engine.say(text)
            engine.runAndWait()
            engine.stop()
            return True
        except Exception as e:
            print(f"[TTS pyttsx3 Fallback Notice]: {e}")
            return False

    def _play_sapi_native(self, text: str):
        """Ultimate bulletproof fallback using direct Windows SAPI.SpVoice."""
        if self.stop_event.is_set():
            return
        try:
            safe_text = text.replace("'", "").replace('"', "")
            ps_cmd = (
                f"$v = New-Object -ComObject SAPI.SpVoice; "
                f"$v.Rate = 1; "
                f"$v.Speak('{safe_text}') | Out-Null"
            )
            subprocess.run(
                ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps_cmd],
                timeout=20,
            )
        except Exception as e:
            print(f"[TTS Native SAPI Error]: {e}")

    def _speech_worker(self):
        """Background daemon thread with Windows COM initialized for audio codecs."""
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
                with self.lock:
                    # Tier 1: Edge-TTS Neural Voice -> Tier 2: pyttsx3 -> Tier 3: Windows Native SAPI
                    if not self._play_edge_tts(cleaned):
                        if not self._play_pyttsx3(cleaned):
                            self._play_sapi_native(cleaned)

            self.speech_queue.task_done()

    def speak(self, text: str):
        """Queues text to be spoken asynchronously."""
        if not text or not text.strip():
            return
        self.stop_event.clear()
        self.speech_queue.put(text)

    def stop(self):
        """Immediately interrupts ongoing speech and flushes the speech queue."""
        self.stop_event.set()
        while not self.speech_queue.empty():
            try:
                self.speech_queue.get_nowait()
                self.speech_queue.task_done()
            except queue.Empty:
                break


# Module-level helper instance in case any script imports speak() directly
_default_engine = None


def speak(text: str):
    global _default_engine
    if _default_engine is None:
        _default_engine = SpeechEngine()
    _default_engine.speak(text)


def stop_speaking():
    global _default_engine
    if _default_engine is not None:
        _default_engine.stop()