import datetime
import re
from typing import Optional

from tools.media_tools import control_media_playback, adjust_system_volume
from tools.window_tools import manage_active_window


def try_instant_reflex(command: str) -> Optional[str]:
    """
    Evaluates spoken command for direct OS/hardware reflexes.
    Returns spoken confirmation string if handled locally (0.05s latency),
    or None if the command requires the full Gemini autonomous brain.
    """
    cmd = command.lower().strip()

    # 1. Volume Reflexes
    if re.search(r"\b(volume\s+up|increase\s+volume|louder|turn\s+it\s+up)\b", cmd):
        adjust_system_volume("up")
        return "Volume raised, sir."

    if re.search(r"\b(volume\s+down|decrease\s+volume|lower\s+the\s+volume|turn\s+it\s+down|quieter)\b", cmd):
        adjust_system_volume("down")
        return "Volume lowered, sir."

    if re.search(r"\b(mute\s+(system|audio|sound)?|unmute)\b", cmd):
        adjust_system_volume("mute")
        return "Audio toggled, sir."

    # 2. Media Playback Reflexes
    if re.search(r"\b(pause(\s+music)?|stop\s+playback|pause\s+video)\b", cmd):
        control_media_playback("pause")
        return "Media paused."

    if re.search(r"\b(play(\s+music)?|resume(\s+playback)?)\b", cmd):
        control_media_playback("play")
        return "Media resumed."

    if re.search(r"\b(next\s+(track|song)|skip(\s+this)?)\b", cmd):
        control_media_playback("next")
        return "Track skipped."

    if re.search(r"\b(previous\s+(track|song)|go\s+back)\b", cmd):
        control_media_playback("previous")
        return "Previous track."

    # 3. Workspace Window Reflexes
    if re.search(r"\b(show\s+desktop|minimize\s+all(\s+windows)?|clear\s+screen)\b", cmd):
        manage_active_window("minimize_all")
        return "Desktop cleared, sir."

    if re.search(r"\b(snap\s+(this\s+window\s+)?left)\b", cmd):
        manage_active_window("snap_left")
        return "Window snapped left."

    if re.search(r"\b(snap\s+(this\s+window\s+)?right)\b", cmd):
        manage_active_window("snap_right")
        return "Window snapped right."

    if re.search(r"\b(close\s+(this\s+)?window|exit\s+app)\b", cmd):
        manage_active_window("close")
        return "Window closed."

    # 4. Temporal Local Reflexes
    if re.search(r"\b(what\s+time\s+is\s+it|current\s+time|tell\s+me\s+the\s+time)\b", cmd):
        now = datetime.datetime.now().strftime("%I:%M %p")
        return f"It is currently {now}, sir."

    if re.search(r"\b(what('s|\s+is)\s+today'?s\s+date|current\s+date)\b", cmd):
        today = datetime.datetime.now().strftime("%A, %B %d, %Y")
        return f"Today is {today}, sir."

    # Not an instant reflex -> delegate to Gemini
    return None