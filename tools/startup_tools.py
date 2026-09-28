import os
import subprocess


def set_windows_autostart(enable: bool = True) -> str:
    """
    Enables or disables J.A.R.V.I.S. starting automatically in the background
    whenever your Windows laptop boots up.
    """
    try:
        startup_dir = os.path.join(
            os.environ["APPDATA"],
            r"Microsoft\Windows\Start Menu\Programs\Startup"
        )
        shortcut_path = os.path.join(startup_dir, "JARVIS_Agent.lnk")
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        bat_target = os.path.join(root_dir, "run.bat")

        if enable:
            # Generate VBScript one-liner to craft a proper Windows .lnk shortcut
            vbs_cmd = (
                f'$ws = New-Object -ComObject WScript.Shell; '
                f'$s = $ws.CreateShortcut("{shortcut_path}"); '
                f'$s.TargetPath = "{bat_target}"; '
                f'$s.WorkingDirectory = "{root_dir}"; '
                f'$s.WindowStyle = 7; '  # Minimized window
                f'$s.Save()'
            )
            subprocess.run(["powershell", "-NoProfile", "-Command", vbs_cmd], check=True)
            return "Auto-start enabled. J.A.R.V.I.S. will now boot silently with Windows."
        else:
            if os.path.exists(shortcut_path):
                os.remove(shortcut_path)
                return "Auto-start disabled. Removed from Windows Startup directory."
            return "Auto-start is already disabled."
    except Exception as e:
        return f"Failed to modify Windows startup state: {e}"