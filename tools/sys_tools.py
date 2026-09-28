import os
import psutil
import subprocess


def get_system_telemetry() -> str:
    """Retrieves CPU utilization, memory consumption, disk usage, and battery telemetry."""
    try:
        cpu = psutil.cpu_percent(interval=0.1)
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        bat = psutil.sensors_battery()
        bat_info = (
            f"{bat.percent}% ({'Plugged In' if bat.power_plugged else 'On Battery'})"
            if bat
            else "Desktop AC"
        )

        return (
            f"CPU Utilization: {cpu}%\n"
            f"RAM Usage: {ram.percent}% (Used: {round(ram.used / (1024**3), 1)}GB / Total: {round(ram.total / (1024**3), 1)}GB)\n"
            f"Primary Disk: {disk.percent}% used\n"
            f"Power Status: {bat_info}"
        )
    except Exception as e:
        return f"Failed to retrieve system telemetry: {e}"


def launch_application(app_name: str) -> str:
    """Launches a desktop application by name or executable."""
    try:
        app_map = {
            "notepad": "notepad.exe",
            "calc": "calc.exe",
            "calculator": "calc.exe",
            "chrome": "chrome.exe",
            "edge": "msedge.exe",
            "terminal": "wt.exe",
            "powershell": "powershell.exe",
            "cmd": "cmd.exe",
            "explorer": "explorer.exe",
        }
        target = app_map.get(app_name.lower().strip(), app_name.strip())
        subprocess.Popen(target, shell=True)
        return f"Successfully initiated launch sequence for '{app_name}'."
    except Exception as e:
        try:
            os.system(f"start {app_name}")
            return f"Dispatched start command for '{app_name}'."
        except Exception as ex:
            return f"Failed to launch application '{app_name}': {ex}"


def list_files_in_directory(path: str = ".") -> str:
    """Lists files and folders inside the specified directory path."""
    try:
        target_path = os.path.abspath(path)
        if not os.path.exists(target_path):
            return f"Path does not exist: {target_path}"

        items = os.listdir(target_path)
        if not items:
            return f"Directory '{target_path}' is empty."

        summary = [f"Contents of {target_path}:"]
        for item in items[:25]:
            full = os.path.join(target_path, item)
            kind = "[DIR]" if os.path.isdir(full) else "[FILE]"
            summary.append(f"  {kind} {item}")

        if len(items) > 25:
            summary.append(f"  ...and {len(items) - 25} more items.")
        return "\n".join(summary)
    except Exception as e:
        return f"Failed to list directory contents: {e}"