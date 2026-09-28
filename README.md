# PROJECT J.A.R.V.I.S. // Autonomous Multimodal Desktop Agent

An evolving, multimodal desktop intelligence system built in Python and powered by Google Gemini Flash models. Engineered with an autonomous ReAct loop, localized persistent memory, spatial vision, OS-level actuation, ambient hardware monitoring, and a glassmorphic PyQt6 desktop HUD.

---

## Architectural Evolution: Mark-1 to Mark-3

| Capability | Mark-1 (`main.py`) | Mark-2 (`mark2_app.py`) | Mark-3 (`mark3_app.py`) |
| :--- | :--- | :--- | :--- |
| **Interface** | Terminal CLI prompt | Frameless PyQt6 HUD | System Tray Daemon + Auto-Summon HUD |
| **Execution Loop** | Single-turn Q&A | Single-action tool calling | Autonomous Multi-Step ReAct Planning |
| **Actuation Speed** | N/A | Slow typing simulation | 0.05s Native Clipboard Macros (`clip.exe`) |
| **In-Place Editing** | File overwriting | Basic clipboard paste | In-place window read/rewrite + macro tools |
| **Input Channels** | Keyboard text | Push-to-Talk & Wake Word | Adaptive audio ring-buffer & low-latency STT |
| **Screen Vision** | None | Full-screen visual sweep | Ephemeral vision buffer with memory pruning |
| **OS Integration** | Basic file I/O | App launch & window typing | PowerShell sandbox + Universal Start search |
| **Background State** | Process stops on exit | Always visible window | Silent tray resident + Ambient vitals monitor |

---

## Controls & Hotkeys

- **Push-to-Talk:** Press `Ctrl + Shift + Space` (or click the Arc Reactor) to give vocal commands.
- **Optical Sweep (Vision):** Press `Ctrl + Shift + V` to inspect your active screen and speak your query.
- **Stealth Toggle:** Press `Ctrl + Shift + H` to instantly hide/summon the HUD to/from the Windows System Tray.
- **Emergency Abort:** Press `Esc` to immediately cut off speech playback and cancel running missions.
- **Hands-Free Wake Word:** Say `"Jarvis"` at any time to wake the agent from background standby.

---

## Project Structure

```text
J.A.R.V.I.S/
├── core/
│   ├── agent_loop.py      # Resilient ReAct planner & multi-step executor
│   ├── ambient_monitor.py # Background hardware & battery anomaly detector
│   ├── audio_fx.py        # Native zero-dependency UI chimes
│   ├── brain.py           # Gemini multimodal brain & conversation core
│   ├── ears.py            # Dynamic acoustic floor & speech-to-text pipeline
│   ├── memory.py          # SQLite localized memory engine
│   ├── speech.py          # Non-blocking neural TTS & audio sanitizer
│   └── wake_word.py       # Continuous circular ring-buffer wake-word engine
├── hud/
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
├── mark3_app.py           # Mark-3 autonomous system daemon (Master)
├── requirements.txt       # Python environment dependencies
└── .gitignore             # Ignores .env and local databases

Launch:

For Mark-3 (Autonomous System Tray Daemon):

python mark3_app.py
For Mark-2 (Visual Desktop HUD):

python mark2_app.py
For Mark-1 (Lightweight CLI):

python main.py