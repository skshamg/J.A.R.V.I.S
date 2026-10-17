# PROJECT J.A.R.V.I.S. // Autonomous Multimodal Desktop Agent

An evolving, multimodal desktop intelligence system built in Python and powered by Google Gemini Flash models. Engineered with an autonomous ReAct loop, localized persistent memory, spatial vision, OS-level actuation, ambient hardware monitoring, and a glassmorphic PyQt6 desktop HUD.

---

## Architectural Evolution: Mark-1 to Mark-4

| Capability | Mark-1 (`main.py`) | Mark-2 (`mark2_app.py`) | Mark-3 (`mark3_app.py`) | Mark-4 (`mark4_app.py`) |
| :--- | :--- | :--- | :--- | :--- |
| **Interface** | Terminal CLI prompt | Frameless PyQt6 HUD | System Tray Daemon + Auto-Summon HUD | Transparent Full-Screen Desktop Glass + Spatial HUD |
| **Execution Loop** | Single-turn Q&A | Single-action tool calling | Autonomous Multi-Step ReAct Planning | Decoupled ReAct Planner + Microsecond Local Reflex Engine |
| **Spatial Vision** | None | None | None | Offline MediaPipe Tasks Hand Tracking & 3D Spatial Rig |
| **Desktop Actuation** | None | Simulated typing | 0.05s Clipboard Macros (`clip.exe`) | Direct Win32 Cursor (`SetCursorPos`) + OS Telekinesis |
| **Spatial 3D Canvas** | None | None | None | 4D Tesseract, Exploding Cube, Arc Reactor & 3D Draw |
| **Voice & Barge-In** | Blocking TTS | Basic TTS playback | Edge-TTS with 2.5s network cutoff | Sub-10ms Voice & Flat-Palm Emergency Speech Barge-In |
| **Acoustic Feedback** | None | System bell | System chimes | Procedural zero-dependency synthesizer (`core/audio_fx.py`) |
| **OS Telekinesis** | None | Basic app launching | PowerShell & Start search | Two-Handed Desktop Wipe (`Win + D`) & Rotary Air Volume |

---

## Controls & Gestures

### Keyboard Hotkeys
- **Push-to-Talk:** Press `Ctrl + Shift + Space` (or click the Arc Reactor) to give vocal commands.
- **Optical Sweep (Vision):** Press `Ctrl + Shift + V` to inspect your active screen and speak your query.
- **Stealth Toggle:** Press `Ctrl + Shift + H` to instantly hide/summon the HUD to/from the Windows System Tray.
- **Emergency Abort:** Press `Esc` to immediately cut off speech playback and cancel running missions.
- **Hands-Free Wake Word:** Say `"Jarvis"` at any time to wake the agent from background standby.

### Mark-4 Spatial Gestures
- **Air Mouse Mode:** Point index finger to steer cursor; pinch index + thumb to click.
- **Mode Lock Toggle:** Hold a **Peace Sign ($\text{V-Sign}$)** for 1.0s until the HUD ring charges to toggle between Air Mouse and 3D Hologram mode.
- **3D Manipulation:** Pinch and drag in 3D mode to tumble objects in pitch, yaw, and roll.
- **Two-Handed Scale & Explode:** Pinch both hands simultaneously. Pull apart to scale up; pull past 320px to detonate the modular cube panels outward into an exploded view (latches on release). Push close together to snap shut.
- **Desktop Telekinesis (Wipe):** Spread both palms flat outward to minimize all windows and reveal the desktop (`Win + D`).
- **Rotary Air Volume Dial:** Raise index and middle fingers together and twirl in a circle to adjust system volume up or down with tactile audio ticks.
- **Emergency Gesture Barge-In:** Flash a flat open palm at the camera while J.A.R.V.I.S. is speaking to cut off speech instantly.

---

## Project Structure

```text
J.A.R.V.I.S/
├── core/
│   ├── agent_loop.py      # Resilient ReAct planner & multi-step executor
│   ├── ambient_monitor.py # Background hardware & battery anomaly detector
│   ├── audio_fx.py        # Procedural zero-dependency synthesizer (clicks, warps, snaps)
│   ├── brain.py           # Gemini multimodal brain & conversation core
│   ├── ears.py            # Dynamic acoustic floor, speech-to-text & voice barge-in
│   ├── hand_landmarker.task # Offline MediaPipe neural weights (8 MB)
│   ├── memory.py          # SQLite localized memory engine
│   ├── reflex_engine.py   # Sub-millisecond local offline reflex router
│   ├── speech.py          # Non-blocking neural TTS with 10ms micro-flush interrupt
│   ├── timer_daemon.py    # Background alarm and timer tracking daemon
│   ├── vision_hands.py    # Headless spatial engine & telekinesis gesture detector
│   └── wake_word.py       # Continuous circular ring-buffer wake-word engine
├── hud/
│   ├── hologram_overlay.py# Full-screen translucent PyQt6 glass overlay
│   ├── hud_window.py      # Glassmorphic PyQt6 HUD & 60 FPS Arc Reactor
│   ├── style.css          # QSS cyberpunk design system
│   └── tray_manager.py    # Windows Notification Area (System Tray) daemon
├── tools/
│   ├── action_tools.py    # Sub-second OS clipboard macros & in-place text editor
│   ├── file_tools.py      # File read, write, append, and search handlers
│   ├── shell_tools.py     # Safe PowerShell execution sandbox
│   ├── sys_tools.py       # Hardware telemetry & universal Start Menu search
│   └── vision_tools.py    # Display buffer capture pipeline
├── main.py                # Mark-1 terminal entry point
├── mark2_app.py           # Mark-2 visual HUD entry point
├── mark3_app.py           # Mark-3 autonomous system daemon
├── mark4_app.py           # Mark-4 spatial intelligence master daemon
├── requirements.txt       # Python environment dependencies
└── .gitignore             # Ignores .env and local databases