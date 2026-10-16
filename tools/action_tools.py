import os
import subprocess
import time
import webbrowser
import pyautogui
import pyperclip

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.03


def click_screen(x: int, y: int, clicks: int = 1, button: str = "left") -> str:
    """Clicks the screen at the specified (x, y) coordinates."""
    try:
        pyautogui.click(x=x, y=y, clicks=clicks, button=button)
        return f"Clicked ({x}, {y}) with {button} button."
    except Exception as e:
        return f"Click failed: {e}"


def type_keyboard(text: str, press_enter: bool = False) -> str:
    """Types text into the currently focused window."""
    try:
        pyautogui.write(text, interval=0.01)
        if press_enter:
            pyautogui.press("enter")
        return "Typed text successfully."
    except Exception as e:
        return f"Typing failed: {e}"


def press_system_key(hotkey: str) -> str:
    """Presses a single key or hotkey combination (e.g., 'enter', 'ctrl+c', 'alt+tab')."""
    try:
        keys = [k.strip().lower() for k in hotkey.split("+")]
        if len(keys) > 1:
            pyautogui.hotkey(*keys)
        else:
            pyautogui.press(keys[0])
        return f"Pressed {hotkey}."
    except Exception as e:
        return f"Key press failed: {e}"


def open_web_url(url: str) -> str:
    """Opens a website URL in the default browser."""
    try:
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        webbrowser.open(url)
        return f"Opened {url}."
    except Exception as e:
        return f"Failed to open URL: {e}"


def paste_text(text: str, press_enter: bool = False) -> str:
    """Instantly pastes text into the active window using the system clipboard."""
    try:
        pyperclip.copy(text)
        time.sleep(0.05)
        pyautogui.hotkey("ctrl", "v")
        if press_enter:
            time.sleep(0.05)
            pyautogui.press("enter")
        return "Content pasted into active window."
    except Exception as e:
        return f"Paste failed: {e}"


def read_active_window_text() -> str:
    """Reads all text from the currently open document or editor window."""
    try:
        pyperclip.copy("")
        pyautogui.hotkey("ctrl", "a")
        time.sleep(0.08)
        pyautogui.hotkey("ctrl", "c")
        time.sleep(0.08)
        pyautogui.press("right")
        content = pyperclip.paste()
        return content if content else "Active window is empty or text could not be copied."
    except Exception as e:
        return f"Failed to read window text: {e}"


def replace_active_window_text(new_text: str) -> str:
    """Replaces all text in the currently active document window with new_text."""
    try:
        pyperclip.copy(new_text)
        pyautogui.hotkey("ctrl", "a")
        time.sleep(0.05)
        pyautogui.hotkey("ctrl", "v")
        return "Document updated in-place."
    except Exception as e:
        return f"Failed to replace window text: {e}"


def delete_text(count: int = 1, unit: str = "word") -> str:
    """Deletes characters, words, or lines in the active editor."""
    try:
        unit = unit.lower().strip()
        if unit == "line":
            for _ in range(count):
                pyautogui.press("end")
                pyautogui.hotkey("shift", "home")
                pyautogui.press("backspace")
        elif unit == "word":
            for _ in range(count):
                pyautogui.hotkey("ctrl", "backspace")
        else:
            for _ in range(count):
                pyautogui.press("backspace")
        return f"Deleted {count} {unit}(s)."
    except Exception as e:
        return f"Delete failed: {e}"


def create_notepad_note(title: str, content: str) -> str:
    """Saves a formatted note to the Desktop and opens it directly in Notepad."""
    try:
        safe_title = "".join(c if c.isalnum() or c in (" ", "_", "-") else "_" for c in title).strip()
        if not safe_title:
            safe_title = "jarvis_note"
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        file_path = os.path.join(desktop, f"{safe_title}.txt")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        subprocess.Popen(["notepad.exe", file_path])
        return f"Created and opened '{safe_title}.txt' in Notepad."
    except Exception as e:
        return f"Failed to create Notepad note: {e}"