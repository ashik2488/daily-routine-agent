@echo off
title Daily Routine Agentic System
echo ====================================================
echo        ?? Starting Daily Routine Agentic System
echo ====================================================
echo.
echo Opening Web Dashboard at http://127.0.0.1:8000 ...
start http://127.0.0.1:8000
python -m uvicorn app:app --host 127.0.0.1 --port 8000
pause
