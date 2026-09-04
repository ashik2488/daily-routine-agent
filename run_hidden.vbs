Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "python -m uvicorn app:app --host 127.0.0.1 --port 8000", 0, False
Set WshShell = Nothing
