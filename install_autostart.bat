@echo off
title Install Daily Routine Agent Autostart
set SCRIPT_DIR=%~dp0
set VBS_PATH=%SCRIPT_DIR%run_hidden.vbs
set STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
set SHORTCUT_VBS=%TEMP%\CreateShortcut.vbs

echo Creating Windows Startup shortcut...
echo Set oWS = WScript.CreateObject("WScript.Shell") > "%SHORTCUT_VBS%"
echo sLinkFile = "%STARTUP_DIR%\DailyRoutineAgent.lnk" >> "%SHORTCUT_VBS%"
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> "%SHORTCUT_VBS%"
echo oLink.TargetPath = "wscript.exe" >> "%SHORTCUT_VBS%"
echo oLink.Arguments = """%VBS_PATH%""" >> "%SHORTCUT_VBS%"
echo oLink.WorkingDirectory = "%SCRIPT_DIR%" >> "%SHORTCUT_VBS%"
echo oLink.Description = "Daily Routine Agentic System" >> "%SHORTCUT_VBS%"
echo oLink.Save >> "%SHORTCUT_VBS%"

cscript /nologo "%SHORTCUT_VBS%"
del "%SHORTCUT_VBS%"

echo.
echo ========================================================
echo  [SUCCESS] Daily Routine Agent is now set to AUTO-START!
echo  It will run automatically and silently in the background
echo  whenever your computer turns on.
echo ========================================================
echo.
pause
