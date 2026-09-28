import subprocess
import pyautogui

pyautogui.FAILSAFE = True


def control_media_playback(action: str) -> str:
    """
    Controls background media players (Spotify, YouTube, media players).
    Supported actions: 'play', 'pause', 'play_pause', 'next', 'previous'.
    """
    action = action.lower().strip()
    try:
        if action in ["play", "pause", "play_pause"]:
            pyautogui.press("playpause")
            return "Toggled media playback."
        elif action in ["next", "skip"]:
            pyautogui.press("nexttrack")
            return "Skipped to next track."
        elif action in ["previous", "prev", "back"]:
            pyautogui.press("prevtrack")
            return "Jumped to previous track."
        return f"Unknown media action: '{action}'."
    except Exception as e:
        return f"Media control error: {e}"


def adjust_system_volume(level_action: str) -> str:
    """
    Adjusts system audio output.
    Supported actions: 'up' (raises volume), 'down' (lowers volume), 'mute' (toggles mute).
    """
    act = level_action.lower().strip()
    try:
        if act == "up":
            for _ in range(5):
                pyautogui.press("volumeup")
            return "System volume increased by 10%."
        elif act == "down":
            for _ in range(5):
                pyautogui.press("volumedown")
            return "System volume decreased by 10%."
        elif act in ["mute", "unmute"]:
            pyautogui.press("volumemute")
            return "Toggled system mute."
        return f"Unknown volume action: '{level_action}'."
    except Exception as e:
        return f"Volume control failed: {e}"


def set_display_brightness(level_percent: int) -> str:
    """Sets laptop display brightness (0 to 100 percent) via Windows CIM."""
    try:
        level = max(0, min(100, int(level_percent)))
        ps_cmd = (
            f"(Get-WmiObject -Namespace root/wmi -Class WmiMonitorBrightnessMethods)"
            f".WmiSetBrightness(1, {level})"
        )
        subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], check=True)
        return f"Display brightness set to {level}%."
    except Exception as e:
        return f"Failed to adjust screen brightness: {e}"