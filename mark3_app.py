import os
import sys
import time
import keyboard

os.environ["QT_LOGGING_RULES"] = "qt.qpa.*=false"

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QThread, QObject, pyqtSignal

from hud.hud_window import JarvisHUD
from hud.tray_manager import JarvisSystemTray
from core.agent_loop import AutonomousAgentLoop
from core.speech import SpeechEngine
from core.ears import EarEngine
from core.wake_word import WakeWordDetector
from core.ambient_monitor import AmbientMonitor
from core.audio_fx import SoundFX
from core.timer_daemon import TimerDaemon, register_global_timer_daemon


class HotkeySignalBridge(QObject):
    trigger_voice_sig = pyqtSignal()
    trigger_vision_sig = pyqtSignal()
    toggle_hud_sig = pyqtSignal()
    interrupt_sig = pyqtSignal()


class Mark3CoreDaemon(QThread):
    update_hud = pyqtSignal(str)
    update_subs = pyqtSignal(str, str)
    summon_hud = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.running = True
        self.speaker = None
        self.ears = None
        self.wake_detector = None
        self.ambient_sensor = None
        self.agent_loop = None
        self.timer_daemon = None

        self.trigger_mode = None
        self.abort_requested = False
        self.last_ambient_tick = time.time()
        self.reboot_requested = False

    def trigger_voice(self):
        if not self.trigger_mode:
            self.summon_hud.emit()
            SoundFX.chime_wake()
            self.trigger_mode = "VOICE"

    def trigger_vision(self):
        if not self.trigger_mode:
            self.summon_hud.emit()
            SoundFX.chime_vision()
            self.trigger_mode = "VISION"

    def interrupt(self):
        self.abort_requested = True
        self.trigger_mode = None
        SoundFX.chime_abort()
        if self.speaker:
            self.speaker.stop()
        self.update_hud.emit("ONLINE")
        self.update_subs.emit("J.A.R.V.I.S.", "Standing by, sir.")

    def on_timer_alert(self, reminder_note: str):
        """Dispatched when a background timer expires."""
        self.summon_hud.emit()
        self.update_hud.emit("ALERT")
        msg = f"Timer complete: {reminder_note}"
        self.update_subs.emit("ALERT", msg)
        SoundFX.chime_wake()
        if self.speaker:
            self.speaker.speak(f"Sir, your timer for {reminder_note} has expired.")
        self.update_hud.emit("ONLINE")

    def run(self):
        self.update_hud.emit("INITIALIZING")
        self.update_subs.emit("J.A.R.V.I.S.", "Calibrating systems...")

        self.speaker = SpeechEngine()
        self.ears = EarEngine()
        self.wake_detector = WakeWordDetector()
        self.ambient_sensor = AmbientMonitor()
        self.agent_loop = AutonomousAgentLoop()

        # Initialize background timer daemon
        self.timer_daemon = TimerDaemon(alert_callback=self.on_timer_alert)
        register_global_timer_daemon(self.timer_daemon)

        time.sleep(0.4)
        self.update_hud.emit("ONLINE")
        self.update_subs.emit("J.A.R.V.I.S.", "Systems online and fully operational, sir.")
        SoundFX.chime_wake()
        self.speaker.speak("Systems nominal, sir. Standing by.")

        while self.running:
            if not self.trigger_mode:
                if (time.time() - self.last_ambient_tick) > 6.0:
                    self.last_ambient_tick = time.time()
                    alert_msg = self.ambient_sensor.check_vitals()
                    if alert_msg:
                        self.summon_hud.emit()
                        self.update_hud.emit("ALERT")
                        self.update_subs.emit("J.A.R.V.I.S.", alert_msg)
                        SoundFX.chime_abort()
                        self.speaker.speak(alert_msg)
                        self.update_hud.emit("ONLINE")

                if self.wake_detector.poll_for_wake_phrase():
                    self.trigger_voice()
                else:
                    time.sleep(0.04)
                    continue

            self.abort_requested = False
            current_mode = self.trigger_mode
            self.trigger_mode = None

            if current_mode == "VISION":
                self.update_hud.emit("VISION ACTIVE")
            else:
                self.update_hud.emit("LISTENING")

            spoken_goal = self.ears.listen_smart(max_duration=20, silence_tolerance=1.5)

            if self.abort_requested:
                continue

            if not spoken_goal:
                self.update_hud.emit("ONLINE")
                continue

            self.update_subs.emit("YOU", spoken_goal)

            # Voice command to reboot daemon via run.bat (Exit Code 42)
            if any(kw in spoken_goal.lower() for kw in ["reboot", "restart core", "restart system"]):
                SoundFX.chime_abort()
                self.update_hud.emit("STANDBY")
                self.update_subs.emit("J.A.R.V.I.S.", "Rebooting systems now, sir.")
                self.speaker.speak("Rebooting systems now, sir.")
                self.reboot_requested = True
                self.running = False
                QApplication.instance().exit(42)
                break

            if spoken_goal.lower() in ["exit", "quit", "shutdown", "abort"]:
                SoundFX.chime_abort()
                self.update_hud.emit("STANDBY")
                self.update_subs.emit("J.A.R.V.I.S.", "Shutting down. Have a good day, sir.")
                self.speaker.speak("Shutting down. Have a good day, sir.")
                self.running = False
                QApplication.instance().quit()
                break

            SoundFX.chime_thinking()
            self.update_hud.emit("PROCESSING")

            final_summary = self.agent_loop.execute_mission(spoken_goal, max_steps=6)

            if self.abort_requested:
                continue

            self.update_hud.emit("SPEAKING")
            self.update_subs.emit("J.A.R.V.I.S.", final_summary)
            self.speaker.speak(final_summary)

            if not self.abort_requested:
                self.update_hud.emit("ONLINE")
            time.sleep(0.2)


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    hud = JarvisHUD()
    hud.show()

    tray = JarvisSystemTray(hud)
    daemon = Mark3CoreDaemon()

    bridge = HotkeySignalBridge()

    bridge.trigger_voice_sig.connect(daemon.trigger_voice)
    bridge.trigger_vision_sig.connect(daemon.trigger_vision)
    bridge.toggle_hud_sig.connect(tray.toggle_hud_visibility)
    bridge.interrupt_sig.connect(daemon.interrupt)

    daemon.update_hud.connect(hud.set_agent_state)
    daemon.update_subs.connect(hud.set_subtitles)
    daemon.summon_hud.connect(lambda: hud.show() if not hud.isVisible() else None)

    hud.reactor_triggered.connect(daemon.trigger_voice)

    try:
        keyboard.add_hotkey("ctrl+shift+space", bridge.trigger_voice_sig.emit)
        keyboard.add_hotkey("ctrl+shift+v", bridge.trigger_vision_sig.emit)
        keyboard.add_hotkey("ctrl+shift+h", bridge.toggle_hud_sig.emit)
        keyboard.add_hotkey("esc", bridge.interrupt_sig.emit)
    except Exception as e:
        print(f"[HOTKEY ERROR] {e}")

    daemon.start()

    exit_code = app.exec()
    daemon.running = False
    if daemon.wake_detector:
        daemon.wake_detector.close()
    keyboard.unhook_all()
    daemon.wait(1000)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()