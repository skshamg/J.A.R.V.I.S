import time
import pyautogui

pyautogui.FAILSAFE = True


def manage_active_window(action: str) -> str:
    """
    Manages open application windows on the desktop.
    Supported actions:
    - 'minimize_all': Clears the desktop and shows background.
    - 'snap_left': Snaps active window to the left half of the display.
    - 'snap_right': Snaps active window to the right half of the display.
    - 'maximize': Maximizes active window.
    - 'close': Closes the active foreground window.
    - 'switch': Switches to the next active application (Alt+Tab).
    """
    act = action.lower().strip()
    try:
        if act in ["minimize_all", "show_desktop"]:
            pyautogui.hotkey("win", "d")
            return "Toggled show desktop (minimized all windows)."
        elif act == "snap_left":
            pyautogui.hotkey("win", "left")
            return "Snapped active window to the left."
        elif act == "snap_right":
            pyautogui.hotkey("win", "right")
            return "Snapped active window to the right."
        elif act == "maximize":
            pyautogui.hotkey("win", "up")
            return "Maximized active window."
        elif act == "close":
            pyautogui.hotkey("alt", "f4")
            return "Sent close command to active window."
        elif act == "switch":
            pyautogui.hotkey("alt", "tab")
            time.sleep(0.1)
            return "Switched active foreground window."
        return f"Unknown window management command: '{action}'."
    except Exception as e:
        return f"Window management action failed: {e}"