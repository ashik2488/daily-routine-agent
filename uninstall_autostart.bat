@echo off
title Uninstall Daily Routine Agent Autostart
set STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
set SHORTCUT_PATH=%STARTUP_DIR%\DailyRoutineAgent.lnk

if exist "%SHORTCUT_PATH%" (
    del "%SHORTCUT_PATH%"
    echo [SUCCESS] Removed Daily Routine Agent from Windows Startup.
) else (
    echo [INFO] Startup shortcut was not found.
)
pause
