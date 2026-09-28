import os
import subprocess
import time
import webbrowser
import pyautogui

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.05


def create_notepad_note(title: str, content: str) -> str:
    """
    Creates a formatted text file on your Windows Desktop (outside the project repo)
    and opens it cleanly in Notepad without cluttering VS Code.
    """
    try:
        # Route to C:\Users\<You>\Desktop\Jarvis_Notes
        notes_dir = os.path.join(os.path.expanduser("~"), "Desktop", "Jarvis_Notes")
        os.makedirs(notes_dir, exist_ok=True)

        clean_title = "".join(c for c in title if c.isalnum() or c in (" ", "_", "-")).strip()
        if not clean_title:
            clean_title = "status_note"
        file_path = os.path.join(notes_dir, f"{clean_title}.txt")

        payload = f"{title.upper()}\n{'=' * len(title)}\n\n{content}\n"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(payload)

        # Open Notepad natively with the file pre-loaded
        subprocess.Popen(["notepad.exe", file_path])
        return f"Successfully created note '{clean_title}.txt' on Desktop and opened in Notepad."
    except Exception as e:
        return f"Failed to create note in Notepad: {e}"


def paste_text(text: str, press_enter: bool = False) -> str:
    """Instantly injects text into the focused window using the Windows clipboard."""
    try:
        process = subprocess.Popen(["clip"], stdin=subprocess.PIPE, close_fds=True)
        process.communicate(input=text.encode("utf-16"))

        time.sleep(0.08)
        pyautogui.hotkey("ctrl", "v")

        if press_enter:
            pyautogui.press("enter")

        return f"Successfully pasted {len(text)} characters into active window."
    except Exception as e:
        return f"Failed to paste text: {e}"


def read_active_window_text() -> str:
    """Selects and reads all text currently open in the focused window."""
    try:
        subprocess.run(["powershell", "-NoProfile", "-Command", "Clear-Clipboard"], check=True)

        pyautogui.hotkey("ctrl", "a")
        time.sleep(0.08)
        pyautogui.hotkey("ctrl", "c")
        time.sleep(0.08)
        pyautogui.press("right")

        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", "Get-Clipboard"],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        content = result.stdout.strip()
        return content if content else "Active window contains no text."
    except Exception as e:
        return f"Failed to read active window text: {e}"


def replace_active_window_text(new_text: str) -> str:
    """Replaces all text in the active document with new_text in 0.1 seconds."""
    try:
        pyautogui.hotkey("ctrl", "a")
        time.sleep(0.05)
        return paste_text(new_text)
    except Exception as e:
        return f"Failed to replace active text: {e}"


def delete_text(count: int = 1, unit: str = "word") -> str:
    """Deletes small chunks of text ('char', 'word', 'line')."""
    try:
        if unit == "line":
            pyautogui.hotkey("shift", "home")
            pyautogui.press("backspace")
            return "Deleted current line."
        elif unit == "word":
            for _ in range(count):
                pyautogui.hotkey("ctrl", "backspace")
            return f"Deleted {count} word(s)."
        else:
            for _ in range(count):
                pyautogui.press("backspace")
            return f"Deleted {count} character(s)."
    except Exception as e:
        return f"Failed to delete text: {e}"


def click_screen(x: int, y: int, clicks: int = 1, button: str = "left") -> str:
    """Moves cursor to coordinate (x, y) and clicks."""
    try:
        pyautogui.click(x=x, y=y, clicks=clicks, button=button)
        return f"Clicked at ({x}, {y})."
    except Exception as e:
        return f"Failed to click: {e}"


def press_system_key(hotkey: str) -> str:
    """Presses key combinations ('ctrl+s', 'ctrl+z', 'alt+f4', 'enter')."""
    try:
        keys = [k.strip().lower() for k in hotkey.split("+")]
        if len(keys) == 1:
            pyautogui.press(keys[0])
        else:
            pyautogui.hotkey(*keys)
        return f"Pressed '{hotkey}'."
    except Exception as e:
        return f"Failed to press key: {e}"


def open_web_url(url: str) -> str:
    """Opens a website directly in the default browser."""
    try:
        if not url.startswith("http://") and not url.startswith("https://"):
            url = "https://" + url
        webbrowser.open(url)
        return f"Opened {url}."
    except Exception as e:
        return f"Failed to open URL: {e}"