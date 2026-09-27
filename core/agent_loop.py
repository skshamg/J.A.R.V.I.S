import os
import sys
import time
from typing import Callable, Optional
from dotenv import load_dotenv
from google import genai
from google.genai import types

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from tools.sys_tools import get_system_telemetry, launch_application, list_files_in_directory
from tools.file_tools import write_file, read_file, append_to_file, search_files
from tools.action_tools import (
    create_notepad_note,
    paste_text,
    read_active_window_text,
    replace_active_window_text,
    delete_text,
    click_screen,
    press_system_key,
    open_web_url,
)
from tools.shell_tools import run_powershell_command
from core.memory import remember, recall, get_all_memories

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")


class AutonomousAgentLoop:
    def __init__(self, step_callback: Optional[Callable[[str, str], None]] = None):
        # Strict 10-second client timeout to kill 503 hanging freezes instantly
        self.client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(timeout=10000)
        )

        # Fastest sub-second models first
        self.model_pool = ["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-3.5-flash"]
        self.current_model_idx = 0
        self.active_model = self.model_pool[self.current_model_idx]
        self.step_callback = step_callback

        self.tools = [
            get_system_telemetry,
            create_notepad_note,
            launch_application,
            list_files_in_directory,
            run_powershell_command,
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
        ]

    def _notify(self, tag: str, message: str):
        if self.step_callback:
            self.step_callback(tag, message)
        print(f"[{tag}] {message}")

    def _build_system_instructions(self) -> str:
        return f"""
You are MARK-3 J.A.R.V.I.S., a high-speed autonomous desktop agent.

CRITICAL WORKFLOW RULES:
1. COMPOUND TASK CHAINING:
   - When asked to write a note, status log, or report in Notepad:
     * ALWAYS use `create_notepad_note(title, content)`. This macro automatically launches Notepad, handles window focus, and pastes the text in one shot.
     * NEVER just launch Notepad and stop. You must complete the writing action.
2. VERBAL RESPONSE:
   - Output a crisp 1-sentence confirmation once all actions are completed.

KNOWN MEMORIES:
{get_all_memories()}
"""

    def execute_mission(self, user_goal: str, max_steps: int = 6) -> str:
        self._notify("PLANNER", f"Analyzing mission: '{user_goal}'")

        attempts = 0
        while attempts < len(self.model_pool):
            try:
                self._notify("AGENT", f"Connecting via {self.active_model}...")

                chat = self.client.chats.create(
                    model=self.active_model,
                    config=types.GenerateContentConfig(
                        system_instruction=self._build_system_instructions(),
                        tools=self.tools,
                        temperature=0.1,
                    ),
                )

                response = chat.send_message(user_goal)

                if response.text:
                    self._notify("COMPLETE", "Mission objectives achieved.")
                    return response.text.strip()

                return "Mission executed successfully, sir."

            except Exception as e:
                err_str = str(e)
                attempts += 1
                self.current_model_idx = (self.current_model_idx + 1) % len(self.model_pool)
                self.active_model = self.model_pool[self.current_model_idx]
                self._notify("SYSTEM", f"Endpoint latency detected. Instantly failing over to {self.active_model}...")
                time.sleep(0.5)

        return "Mission aborted: All network models exceeded response timeout limits."


if __name__ == "__main__":
    print("Testing Ultra-Fast Agent Loop...")
    planner = AutonomousAgentLoop()
    res = planner.execute_mission(
        "Check telemetry, and if CPU load is normal, create a Notepad note with a brief status report."
    )
    print(f"\nFinal Verdict: {res}")