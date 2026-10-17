import threading
import time
import winsound


class SoundFXEngine:
    """Zero-dependency procedural acoustic engine for J.A.R.V.I.S."""

    @staticmethod
    def _play_async(fn, *args):
        threading.Thread(target=fn, args=args, daemon=True).start()

    @classmethod
    def ui_click(cls):
        """Crisp mechanical button click."""
        def _sound():
            winsound.Beep(1800, 18)
        cls._play_async(_sound)

    @classmethod
    def mode_lock(cls):
        """Ascending dual-tone futuristic lock chime."""
        def _sound():
            winsound.Beep(980, 45)
            winsound.Beep(1470, 70)
        cls._play_async(_sound)

    @classmethod
    def explode_warp(cls):
        """High-to-low magnetic displacement tone."""
        def _sound():
            for freq in (1200, 950, 720, 520):
                winsound.Beep(freq, 25)
        cls._play_async(_sound)

    @classmethod
    def reassemble_snap(cls):
        """Low-to-high magnetic snap tone."""
        def _sound():
            for freq in (520, 750, 1100, 1500):
                winsound.Beep(freq, 20)
        cls._play_async(_sound)

    @classmethod
    def gesture_whoosh(cls):
        """Subtle swept tone for workspace window minimization/swipes."""
        def _sound():
            winsound.Beep(650, 30)
            winsound.Beep(450, 40)
        cls._play_async(_sound)

    @classmethod
    def volume_tick(cls, direction="up"):
        """Tactile rotary volume detent click."""
        def _sound():
            freq = 2100 if direction == "up" else 1400
            winsound.Beep(freq, 12)
        cls._play_async(_sound)


# Global helper shortcuts
play_click = SoundFXEngine.ui_click
play_lock = SoundFXEngine.mode_lock
play_explode = SoundFXEngine.explode_warp
play_snap = SoundFXEngine.reassemble_snap
play_whoosh = SoundFXEngine.gesture_whoosh
play_vol_tick = SoundFXEngine.volume_tick