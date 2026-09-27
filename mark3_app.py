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


class HotkeySignalBridge(QObject):
    """
    Thread-safe bridge between the low-level Windows 'keyboard' hook
    and PyQt6's main GUI event loop. Prevents all OS thread deadlocks.
    """
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

        self.trigger_mode = None
        self.abort_requested = False
        self.last_ambient_tick = time.time()

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
        self.update_subs.emit("SYSTEM", "Mission interrupted by operator.")

    def run(self):
        self.update_hud.emit("INITIALIZING")
        self.update_subs.emit("SYSTEM", "Calibrating Mark-III neural core...")

        self.speaker = SpeechEngine()
        self.ears = EarEngine()
        self.wake_detector = WakeWordDetector()
        self.ambient_sensor = AmbientMonitor()

        self.agent_loop = AutonomousAgentLoop(
            step_callback=lambda tag, msg: self.update_subs.emit(tag, msg)
        )

        time.sleep(0.5)
        self.update_hud.emit("ONLINE")
        self.update_subs.emit("J.A.R.V.I.S.", "Mark Three initialized. Full autonomy armed.")
        SoundFX.chime_wake()
        self.speaker.speak("Mark Three systems online. Ready, sir.")

        while self.running:
            # 1. Standby & Ambient Checks
            if not self.trigger_mode:
                if (time.time() - self.last_ambient_tick) > 6.0:
                    self.last_ambient_tick = time.time()
                    alert_msg = self.ambient_sensor.check_vitals()
                    if alert_msg:
                        self.summon_hud.emit()
                        self.update_hud.emit("ALERT")
                        self.update_subs.emit("VITALS", alert_msg)
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

            # 2. Listening Phase
            if current_mode == "VISION":
                self.update_hud.emit("VISION ACTIVE")
                self.update_subs.emit("SYSTEM", "Optical sensors aligned. Listening...")
            else:
                self.update_hud.emit("LISTENING")
                self.update_subs.emit("SYSTEM", "Listening for mission parameters...")

            spoken_goal = self.ears.listen_smart(max_duration=35, silence_tolerance=3.0)

            if self.abort_requested:
                continue

            if not spoken_goal:
                self.update_hud.emit("ONLINE")
                self.update_subs.emit("SYSTEM", "No command registered. Resuming standby.")
                continue

            self.update_subs.emit("YOU", spoken_goal)

            if spoken_goal.lower() in ["exit", "quit", "shutdown", "abort"]:
                SoundFX.chime_abort()
                self.update_hud.emit("STANDBY")
                self.update_subs.emit("J.A.R.V.I.S.", "Shutting down Mark Three. Goodbye, sir.")
                self.speaker.speak("Shutting down. Goodbye, sir.")
                self.running = False
                break

            # 3. Autonomous Execution Phase
            SoundFX.chime_thinking()
            self.update_hud.emit("PROCESSING")

            final_summary = self.agent_loop.execute_mission(spoken_goal, max_steps=6)

            if self.abort_requested:
                continue

            # 4. Spoken Synthesis
            self.update_hud.emit("SPEAKING")
            self.update_subs.emit("J.A.R.V.I.S.", final_summary)
            self.speaker.speak(final_summary)

            if not self.abort_requested:
                self.update_hud.emit("ONLINE")
            time.sleep(0.2)


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # Keeps tray alive even when HUD is hidden

    hud = JarvisHUD()
    hud.show()

    tray = JarvisSystemTray(hud)
    daemon = Mark3CoreDaemon()

    bridge = HotkeySignalBridge()

    # Route all external thread events through Qt's safe signal queue
    bridge.trigger_voice_sig.connect(daemon.trigger_voice)
    bridge.trigger_vision_sig.connect(daemon.trigger_vision)
    bridge.toggle_hud_sig.connect(tray.toggle_hud_visibility)
    bridge.interrupt_sig.connect(daemon.interrupt)

    daemon.update_hud.connect(hud.set_agent_state)
    daemon.update_subs.connect(hud.set_subtitles)
    daemon.summon_hud.connect(lambda: hud.show() if not hud.isVisible() else None)

    hud.reactor_triggered.connect(daemon.trigger_voice)

    # Hook Keyboard cleanly into the Qt bridge
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