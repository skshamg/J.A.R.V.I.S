import os
import sys
import time
from dotenv import load_dotenv
from google import genai
from google.genai import types

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from tools.sys_tools import get_system_telemetry, launch_application, list_files_in_directory
from tools.file_tools import write_file, read_file, append_to_file, search_files
from tools.action_tools import (
    paste_text,
    read_active_window_text,
    replace_active_window_text,
    delete_text,
    click_screen,
    press_system_key,
    open_web_url,
)
from tools.vision_tools import capture_screen_part
from core.memory import remember, recall, get_all_memories

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("GEMINI_API_KEY missing from .env file!")


def build_system_prompt() -> str:
    known_memories = get_all_memories()
    return f"""
You are MARK-II (J.A.R.V.I.S.), an autonomous desktop assistant.

DOCUMENT & APP AUTOMATION RULES:
1. EDITING OPEN DOCUMENTS:
   - When asked to delete, edit, or rewrite parts of an open document (like Notepad):
     * NEVER launch a new Notepad or write a separate file on disk.
     * Call `read_active_window_text` to inspect the current document.
     * Modify the text in your thoughts (e.g. remove the conclusion or fix paragraphs).
     * Call `replace_active_window_text` with the updated text to edit it in-place instantly.
2. CREATING NEW CONTENT:
   - Use `paste_text` to paste long structured reports into open windows in 0.05 seconds.
3. OPENING APPS:
   - Call `launch_application` with the app name (e.g., 'vn editor', 'capcut', 'notepad'). The launcher dynamically searches all installed Windows apps. Do NOT open browser download links unless explicitly told to download an installer.

SPOKEN VOICE CONVERSATION:
- Spoken responses MUST be concise (1 to 2 short sentences).
- Never read out long reports or code blocks aloud. Confirm completion briefly.

KNOWN USER PREFERENCES:
{known_memories}
"""


class Mark1Brain:
    def __init__(self):
        self.client = genai.Client(api_key=api_key)
        self.model_pool = ["gemini-3.5-flash-lite", "gemini-3.8-flash", "gemini-3.5-flash"]
        self.current_model_idx = 0
        self.active_model = self.model_pool[self.current_model_idx]
        self._setup_chat()

    def _get_config(self):
        return types.GenerateContentConfig(
            system_instruction=build_system_prompt(),
            tools=[
                get_system_telemetry,
                launch_application,
                list_files_in_directory,
                write_file,
                read_file,
                append_to_file,
                search_files,
                paste_text,
                read_active_window_text,
                replace_active_window_text,
                delete_text,
                click_screen,
                press_system_key,
                open_web_url,
                remember,
                recall,
            ],
            temperature=0.2,
        )

    def _setup_chat(self):
        self.chat = self.client.chats.create(
            model=self.active_model,
            config=self._get_config(),
        )

    def _prune_heavy_history(self):
        """
        Strips large image blobs and massive payloads from the chat history
        so every subsequent request completes in 1-2 seconds instead of minutes.
        """
        try:
            history = self.chat.get_history()
            # Keep only the last 6 conversational turns to maintain speed
            if len(history) > 6:
                trimmed = history[-6:]
                # Clean any raw binary image parts from older turns
                for content in trimmed:
                    content.parts = [
                        p for p in content.parts
                        if not hasattr(p, "inline_data") or p.inline_data is None
                    ]
                self._setup_chat()
                # Re-seed the pruned conversational context
                for item in trimmed:
                    self.chat._history.append(item)
        except Exception:
            pass

    def talk(self, user_input: str, force_vision: bool = False) -> str:
        vision_triggers = [
            "screen", "look", "see", "code", "window", "display",
            "diagram", "read this", "inspect"
        ]
        needs_vision = force_vision or any(trigger in user_input.lower() for trigger in vision_triggers)

        contents = [user_input]
        if needs_vision:
            try:
                screen_part = capture_screen_part()
                contents.append(screen_part)
            except Exception as e:
                print(f"[VISION WARNING] Screen capture bypassed: {e}")

        # Prune bloated turns before sending
        self._prune_heavy_history()

        attempts = 0
        while attempts < len(self.model_pool):
            try:
                response = self.chat.send_message(contents)
                return response.text.strip()
            except Exception as e:
                err_str = str(e)
                if "503" in err_str or "UNAVAILABLE" in err_str or "429" in err_str:
                    attempts += 1
                    self.current_model_idx = (self.current_model_idx + 1) % len(self.model_pool)
                    self.active_model = self.model_pool[self.current_model_idx]
                    print(f"\n[SYSTEM ALERT: Switching core to {self.active_model}...]")
                    self._setup_chat()
                    time.sleep(1)
                else:
                    return f"System alert: Communication pipeline encountered an error: {e}"

        return "System alert: Endpoints busy. Standing by."