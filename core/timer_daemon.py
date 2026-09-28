import threading
import time
from typing import Callable, List, Tuple


class TimerDaemon:
    def __init__(self, alert_callback: Callable[[str], None]):
        self.alert_callback = alert_callback
        self.active_timers: List[Tuple[float, str]] = []
        self.lock = threading.Lock()
        self.running = True

        self.worker = threading.Thread(target=self._poll_loop, daemon=True)
        self.worker.start()

    def set_timer(self, seconds: int, note: str) -> str:
        """Schedules a non-blocking background alarm/timer."""
        trigger_at = time.time() + max(1, seconds)
        with self.lock:
            self.active_timers.append((trigger_at, note))

        minutes = seconds // 60
        secs = seconds % 60
        time_str = f"{minutes} minute(s)" if minutes > 0 else f"{secs} seconds"
        return f"Timer set for {time_str}: '{note}'."

    def _poll_loop(self):
        while self.running:
            now = time.time()
            triggered = []

            with self.lock:
                remaining = []
                for trigger_at, note in self.active_timers:
                    if now >= trigger_at:
                        triggered.append(note)
                    else:
                        remaining.append((trigger_at, note))
                self.active_timers = remaining

            for note in triggered:
                self.alert_callback(note)

            time.sleep(1.0)


# Global instance reference for the agent tool wrapper
_global_timer_daemon: TimerDaemon | None = None


def register_global_timer_daemon(daemon: TimerDaemon):
    global _global_timer_daemon
    _global_timer_daemon = daemon


def schedule_alarm_timer(duration_seconds: int, reminder_text: str = "Timer complete") -> str:
    """
    Schedules an autonomous background timer or reminder.
    Example: 120 seconds for 'Take pizza out of oven' or 300 seconds for 'Study break'.
    """
    global _global_timer_daemon
    if not _global_timer_daemon:
        return "Timer daemon is currently offline."
    return _global_timer_daemon.set_timer(duration_seconds, reminder_text)