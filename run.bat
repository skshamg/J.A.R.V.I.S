@echo off
title J.A.R.V.I.S. // Mark-3 Core
cls

:LOOP
echo [DAEMON] Launching J.A.R.V.I.S. Mark-3...
py mark3_app.py
set EXIT_CODE=%ERRORLEVEL%

if %EXIT_CODE% equ 42 (
    echo [DAEMON] Reboot requested by core. Restarting in 1s...
    timeout /t 1 /nobreak >nul
    goto LOOP
)

echo [DAEMON] Process terminated cleanly with code %EXIT_CODE%.