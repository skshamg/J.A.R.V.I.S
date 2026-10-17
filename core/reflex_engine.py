import ctypes
import datetime
import os
import re
import subprocess
import threading
from typing import Optional

import psutil
from tools.media_tools import adjust_system_volume, control_media_playback
from tools.window_tools import manage_active_window


def try_instant_reflex(command: str) -> Optional[str]:
    """
    Evaluates spoken commands against deterministic local hardware/OS handlers.
    Returns spoken confirmation string if handled locally (0.04s latency),
    or None if the command requires the full Gemini autonomous brain.
    """
    cmd = command.lower().strip()

    # 0. NUCLEAR HARD SYSTEM SHUTDOWN
    if re.search(r"\b(shut\s*down|power\s*off|terminate|exit|go\s+offline|close\s+jarvis|sleep\s+now)\b", cmd):
        def _nuke():
            import time
            time.sleep(1.2)
            # Kill camera if running
            for proc in psutil.process_iter(['cmdline']):
                try:
                    cmdline = proc.info.get('cmdline')
                    if cmdline and any(k in ' '.join(cmdline) for k in ('vision_hands.py', 'hologram_overlay.py')):
                        proc.kill()
                except Exception:
                    pass
            os._exit(0) 

        threading.Thread(target=_nuke, daemon=True).start()
        return "Shutting down operations, sir."
    
    # 1. Volume Controls
    if re.search(r"\b(volume\s+up|increase\s+volume|louder|turn\s+it\s+up)\b", cmd):
        adjust_system_volume("up")
        return "Volume raised, sir."

    if re.search(r"\b(volume\s+down|decrease\s+volume|lower\s+the\s+volume|turn\s+it\s+down|quieter)\b", cmd):
        adjust_system_volume("down")
        return "Volume lowered, sir."

    if re.search(r"\b(mute\s+(system|audio|sound)?|unmute)\b", cmd):
        adjust_system_volume("mute")
        return "Audio toggled, sir."

    # 2. Media Playback Controls
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

    # 3. Workspace Window Controls
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

    # 4. App Launchers (Instant Subprocess Spawn)
    if re.search(r"\b(open|launch|start)\s+(google\s+)?chrome\b", cmd):
        subprocess.Popen(["cmd", "/c", "start", "chrome"], shell=True)
        return "Opening Chrome, sir."

    if re.search(r"\b(open|launch|start)\s+(code|vs\s*code|visual\s+studio\s+code)\b", cmd):
        subprocess.Popen(["cmd", "/c", "code"], shell=True)
        return "Launching VS Code."

    if re.search(r"\b(open|launch|start)\s+(file\s+explorer|files|my\s+computer)\b", cmd):
        subprocess.Popen(["explorer"], shell=True)
        return "Opening File Explorer."

    if re.search(r"\b(open|launch|start)\s+task\s+manager\b", cmd):
        subprocess.Popen(["taskmgr"], shell=True)
        return "Task Manager opened."

    if re.search(r"\b(open|launch|start)\s+notepad\b", cmd):
        subprocess.Popen(["notepad"], shell=True)
        return "Notepad opened."

    # 5. System Security & Hardware Vitals
    if re.search(r"\b(lock\s+(pc|laptop|computer|windows|screen))\b", cmd):
        ctypes.windll.user32.LockWorkStation()
        return "Workstation locked, sir."

    if re.search(r"\b(battery\s+(status|level|percentage)|how\s+much\s+battery)\b", cmd):
        battery = psutil.sensors_battery()
        if battery:
            percent = int(battery.percent)
            plugged = "plugged in" if battery.power_plugged else "on battery power"
            return f"Battery is at {percent}%, {plugged}."
        return "Battery telemetry unavailable, sir."

    # 6. Temporal Local Reflexes
    if re.search(r"\b(what\s+time\s+is\s+it|current\s+time|tell\s+me\s+the\s+time)\b", cmd):
        now = datetime.datetime.now().strftime("%I:%M %p")
        return f"It is currently {now}, sir."

    if re.search(r"\b(what('s|\s+is)\s+today'?s\s+date|current\s+date)\b", cmd):
        today = datetime.datetime.now().strftime("%A, %B %d, %Y")
        return f"Today is {today}, sir."

    # 7. Mark-4 Hand Tracking (Local offline camera execution)
    if re.search(r"\b(open|launch|enable|start|activate|turn\s+on)\s+(hand\s+tracking|air\s*mouse|gestures)\b|\b(air\s*mouse\s+on)\b", cmd):
        import sys
        script_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "core", "vision_hands.py")
        subprocess.Popen([sys.executable, script_path])
        return "Air mouse protocols engaged, sir. Camera active."

    if re.search(r"\b(close|disable|stop|deactivate|turn\s+off|kill)\s+(hand\s+tracking|air\s*mouse|gestures)\b|\b(air\s*mouse\s+off)\b", cmd):
        for proc in psutil.process_iter(['cmdline']):
            try:
                cmdline = proc.info.get('cmdline')
                if cmdline and any('vision_hands.py' in arg for arg in cmdline):
                    proc.kill()
            except Exception:
                pass
        return "Air mouse protocols disabled. Camera released."

    # Not an instant reflex -> delegate to Gemini
    return None