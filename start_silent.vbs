Set WshShell = CreateObject("WScript.Shell")
' WindowStyle 0 = Completely hidden, zero console flash
WshShell.Run "pythonw mark3_app.py", 0, False