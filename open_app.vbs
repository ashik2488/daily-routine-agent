Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "run_hidden.vbs", 0, False
WScript.Sleep 500
WshShell.Run "http://127.0.0.1:8000", 1, False
Set WshShell = Nothing
