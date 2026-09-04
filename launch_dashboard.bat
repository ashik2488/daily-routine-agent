@echo off
start "" "%~dp0run_hidden.vbs"
timeout /t 1 /nobreak >nul
start http://127.0.0.1:8000
