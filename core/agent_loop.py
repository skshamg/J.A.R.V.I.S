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
from tools.web_tools import web_search, read_web_page
from tools.vision_tools import click_element_on_screen
from tools.startup_tools import set_windows_autostart
from tools.media_tools import control_media_playback, adjust_system_volume, set_display_brightness
from tools.window_tools import manage_active_window
from core.timer_daemon import schedule_alarm_timer
from core.memory import remember, recall, get_all_memories

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")


class AutonomousAgentLoop:
    def __init__(self, step_callback: Optional[Callable[[str, str], None]] = None):
        self.client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(timeout=25000)
        )

        self.model_pool = ["gemini-3.8-flash", "gemini-3.5-flash-lite", "gemini-3.5-flash"]
        self.current_model_idx = 0
        self.active_model = self.model_pool[self.current_model_idx]
        self.step_callback = step_callback

        self.tools = [
            get_system_telemetry,
            create_notepad_note,
            web_search,
            read_web_page,
            click_element_on_screen,
            control_media_playback,
            adjust_system_volume,
            set_display_brightness,
            manage_active_window,
            schedule_alarm_timer,
            set_windows_autostart,
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

    def _log_terminal(self, tag: str, message: str):
        print(f"[{tag}] {message}")

    def _build_system_instructions(self) -> str:
        return f"""
You are J.A.R.V.I.S., an autonomous high-speed desktop agent.

TOOL WORKFLOW GUIDELINES:
1. MEDIA & HARDWARE:
   - For playback control (play, pause, next track): call `control_media_playback(action)`.
   - For audio volume: call `adjust_system_volume(level_action)`.
   - For screen brightness: call `set_display_brightness(level_percent)`.
2. WINDOW MANAGEMENT:
   - For workspace window snapping or clearing: call `manage_active_window(action)`.
3. TIMERS & REMINDERS:
   - When asked to set a timer or alarm: convert duration to total seconds and call `schedule_alarm_timer(duration_seconds, reminder_text)`.
4. AUTO-START:
   - To make J.A.R.V.I.S. run on boot: call `set_windows_autostart(True)`.
5. VISUAL GROUNDING & WEB:
   - To click buttons on screen: call `click_element_on_screen(element_description)`.
   - To search data: call `web_search(query)`.
   - To write notes: ALWAYS call `create_notepad_note(title, content)`.
6. BREVITY:
   - Always confirm completed physical actions with a crisp 1-sentence reply.

KNOWN USER PREFERENCES:
{get_all_memories()}
"""

    def execute_mission(self, user_goal: str, max_steps: int = 6) -> str:
        self._log_terminal("MISSION START", user_goal)

        attempts = 0
        while attempts < len(self.model_pool):
            try:
                self._log_terminal("NEURAL ROUTE", f"Connecting via {self.active_model}...")

                chat = self.client.chats.create(
                    model=self.active_model,
                    config=types.GenerateContentConfig(
                        system_instruction=self._build_system_instructions(),
                        tools=self.tools,
                        temperature=0.2,
                    ),
                )

                response = chat.send_message(user_goal)

                if response.text:
                    self._log_terminal("COMPLETE", "Objectives cleared.")
                    return response.text.strip()

                return "Task completed successfully, sir."

            except Exception as e:
                self._log_terminal("INTERNAL FAILOVER", f"{self.active_model} encountered: {e}")
                attempts += 1
                self.current_model_idx = (self.current_model_idx + 1) % len(self.model_pool)
                self.active_model = self.model_pool[self.current_model_idx]
                time.sleep(0.4)

        return "I encountered network resistance reaching the servers, sir. Standing by."