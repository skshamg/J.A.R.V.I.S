import os
import subprocess
import psutil


def get_system_telemetry() -> str:
    """Returns real-time hardware telemetry: CPU, RAM, and Battery status."""
    try:
        cpu = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory()
        battery = psutil.sensors_battery()

        bat_str = f"{battery.percent}%" if battery else "AC Desktop"
        plugged = f", Plugged In: {battery.power_plugged}" if battery else ""

        return (
            f"Hardware Status:\n"
            f"- CPU Load: {cpu}%\n"
            f"- Memory Used: {mem.percent}% ({round(mem.used / (1024**3), 2)} GB / {round(mem.total / (1024**3), 2)} GB)\n"
            f"- Battery: {bat_str}{plugged}"
        )
    except Exception as e:
        return f"Telemetry read error: {e}"


def launch_application(app_name: str) -> str:
    """
    Universally finds and launches any installed app on Windows 11
    (including Windows Store apps, VN Editor, CapCut, browsers, and tools).
    """
    clean_name = app_name.strip().lower()

    # 1. Fast path for standard built-ins
    quick_map = {
        "notepad": "notepad.exe",
        "calculator": "calc.exe",
        "calc": "calc.exe",
        "chrome": "chrome.exe",
        "terminal": "wt.exe",
        "cmd": "cmd.exe",
        "explorer": "explorer.exe",
        "task manager": "taskmgr.exe",
        "settings": "ms-settings:",
    }

    if clean_name in quick_map:
        target = quick_map[clean_name]
        try:
            os.system(f"start {target}")
            return f"Launched {clean_name}."
        except Exception:
            pass

    # 2. Deep Windows Start Menu Query (Finds VN, CapCut, Steam, etc.)
    ps_command = f"""
    $apps = Get-StartApps
    $match = $apps | Where-Object {{ $_.Name -like '*{clean_name}*' }} | Select-Object -First 1
    if ($match) {{
        Start-Process "shell:AppsFolder\\$($match.AppID)"
        Write-Output "LAUNCHED:$($match.Name)"
    }} else {{
        Write-Output "NOT_FOUND"
    }}
    """
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_command],
            capture_output=True,
            text=True,
            timeout=5,
        )
        out = result.stdout.strip()
        if "LAUNCHED:" in out:
            found_name = out.replace("LAUNCHED:", "")
            return f"Successfully located and launched '{found_name}'."
        else:
            return f"Could not find an installed application matching '{app_name}' in Windows."
    except Exception as e:
        return f"Failed to launch {app_name}: {e}"


def list_files_in_directory(path: str = ".") -> str:
    """Lists files and folders in a specified directory path."""
    try:
        abs_path = os.path.abspath(path)
        if not os.path.exists(abs_path):
            return f"Path does not exist: {abs_path}"

        items = os.listdir(abs_path)
        if not items:
            return f"Directory {abs_path} is empty."

        return f"Contents of {abs_path}:\n" + "\n".join([f"- {i}" for i in items[:30]])
    except Exception as e:
        return f"Directory read error: {e}"