import subprocess


# Safety blacklist of destructive commands
BLACKLIST = ["rmdir /s", "del /f /s /q c:", "format", "diskpart"]


def run_powershell_command(command: str) -> str:
    """
    Executes a safe PowerShell command and returns the terminal output.
    Useful for inspecting system files, Git operations, process queries, and running scripts.
    """
    clean_cmd = command.strip()

    # Safety check
    if any(blocked in clean_cmd.lower() for blocked in BLACKLIST):
        return "Command rejected: High-risk system modification blocked by Mark-3 safety layer."

    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", clean_cmd],
            capture_output=True,
            text=True,
            timeout=15,
        )

        stdout = result.stdout.strip()
        stderr = result.stderr.strip()

        if stderr and not stdout:
            return f"Command Error:\n{stderr[:400]}"

        output = stdout if stdout else "Command executed successfully (no terminal output)."
        # Truncate output to prevent token saturation
        return output[:800]

    except subprocess.TimeoutExpired:
        return "Command aborted: Execution timed out after 15 seconds."
    except Exception as e:
        return f"Shell execution failed: {e}"