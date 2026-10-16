import os
import platform
import shutil
import subprocess
import winreg
import psutil


def get_system_telemetry() -> str:
    """Returns real-time CPU, RAM, disk, and battery metrics."""
    try:
        cpu = psutil.cpu_percent(interval=0.2)
        ram = psutil.virtual_memory()
        battery = psutil.sensors_battery()
        bat_str = f"{int(battery.percent)}% ({'Charging' if battery.power_plugged else 'Discharging'})" if battery else "N/A"
        return (
            f"OS: {platform.system()} {platform.release()} | "
            f"CPU Usage: {cpu}% | "
            f"RAM Usage: {ram.percent}% ({round(ram.used / (1024**3), 1)}GB / {round(ram.total / (1024**3), 1)}GB) | "
            f"Battery: {bat_str}"
        )
    except Exception as e:
        return f"Telemetry error: {e}"


def launch_application(application_name: str) -> str:
    """
    Dynamically scans Windows PATH, Registry App Paths, Start Menu shortcuts,
    and Windows Store apps to launch any installed application. Never fakes a launch.
    """
    target = application_name.lower().strip()
    if not target:
        return "No application name provided, sir."

    # 1. Check direct system PATH executables (notepad, calc, code, taskmgr)
    path_exe = shutil.which(target)
    if path_exe:
        subprocess.Popen([path_exe], shell=True)
        return f"Launched {application_name}, sir."

    # 2. Scan Windows Registry (App Paths)
    reg_roots = [
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\App Paths"),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\App Paths"),
    ]
    for hive, subkey in reg_roots:
        try:
            with winreg.OpenKey(hive, subkey) as key:
                num_subkeys = winreg.QueryInfoKey(key)[0]
                for i in range(num_subkeys):
                    exe_key_name = winreg.EnumKey(key, i)
                    if target in exe_key_name.lower():
                        with winreg.OpenKey(key, exe_key_name) as app_key:
                            exe_path, _ = winreg.QueryValueEx(app_key, "")
                            exe_path = exe_path.strip('"')
                            if os.path.exists(exe_path):
                                subprocess.Popen([exe_path])
                                return f"Launched {application_name}, sir."
        except Exception:
            pass

    # 3. Dynamically scan all Windows Start Menu & Desktop shortcuts (.lnk)
    shortcut_dirs = [
        os.path.join(os.environ.get("ProgramData", r"C:\ProgramData"), r"Microsoft\Windows\Start Menu\Programs"),
        os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs"),
        os.path.join(os.environ.get("USERPROFILE", ""), "Desktop"),
    ]

    best_match = None
    for base_dir in shortcut_dirs:
        if not os.path.exists(base_dir):
            continue
        for root, _, files in os.walk(base_dir):
            for file in files:
                if file.lower().endswith(".lnk"):
                    shortcut_name = os.path.splitext(file)[0].lower()
                    if "uninstall" in shortcut_name:
                        continue
                    if shortcut_name == target:
                        os.startfile(os.path.join(root, file))
                        return f"Launched {application_name}, sir."
                    if target in shortcut_name and best_match is None:
                        best_match = os.path.join(root, file)

    if best_match:
        os.startfile(best_match)
        return f"Launched {application_name}, sir."

    # 4. Check Windows Store / UWP Apps (e.g., Telegram Desktop Store, WhatsApp, Spotify)
    try:
        ps_cmd = (
            f"$app = Get-StartApps | Where-Object {{ $_.Name -like '*{target}*' }} | Select-Object -First 1; "
            f"if ($app) {{ Start-Process ('shell:AppsFolder\\' + $app.AppID); Write-Output 'FOUND' }}"
        )
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_cmd],
            capture_output=True,
            text=True,
            timeout=3,
        )
        if "FOUND" in result.stdout:
            return f"Launched {application_name}, sir."
    except Exception:
        pass

    return f"Unable to find {application_name} installed on your system, sir."


def list_files_in_directory(directory_path: str = ".") -> str:
    """Lists all files and folders inside the specified directory path."""
    try:
        expanded = os.path.expanduser(directory_path)
        if not os.path.exists(expanded):
            return f"Directory '{directory_path}' does not exist."
        items = os.listdir(expanded)
        if not items:
            return f"Directory '{directory_path}' is empty."
        return "\n".join(items[:100])
    except Exception as e:
        return f"Failed to list directory: {e}"