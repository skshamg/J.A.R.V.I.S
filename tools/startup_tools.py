import os
import subprocess


def set_windows_autostart(enable: bool = True) -> str:
    """Enables or disables J.A.R.V.I.S. booting silently in the background with Windows."""
    try:
        startup_dir = os.path.join(
            os.environ["APPDATA"],
            r"Microsoft\Windows\Start Menu\Programs\Startup"
        )
        shortcut_path = os.path.join(startup_dir, "JARVIS_Agent.lnk")
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        vbs_target = os.path.join(root_dir, "start_silent.vbs")

        if enable:
            vbs_cmd = (
                f'$ws = New-Object -ComObject WScript.Shell; '
                f'$s = $ws.CreateShortcut("{shortcut_path}"); '
                f'$s.TargetPath = "{vbs_target}"; '
                f'$s.WorkingDirectory = "{root_dir}"; '
                f'$s.WindowStyle = 7; '
                f'$s.Save()'
            )
            subprocess.run(["powershell", "-NoProfile", "-Command", vbs_cmd], check=True)
            return "Silent auto-start enabled. J.A.R.V.I.S. will boot directly into the System Tray."
        else:
            if os.path.exists(shortcut_path):
                os.remove(shortcut_path)
                return "Auto-start disabled. Removed from Windows Startup directory."
            return "Auto-start is already disabled."
    except Exception as e:
        return f"Failed to modify Windows startup state: {e}"