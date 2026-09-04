Set objShell = CreateObject("WScript.Shell")
Set objFSO = CreateObject("Scripting.FileSystemObject")

appDir = objFSO.GetParentFolderName(WScript.ScriptFullName)
pythonExe = "python"
scriptPath = appDir & "\app.py"

' Start FastAPI server in background
objShell.Run "cmd /c start /min """ & pythonExe & """ """ & scriptPath & """", 0, False

' Wait 2 seconds for server to start
WScript.Sleep 2000

' Launch in Chrome app mode for dedicated window (no browser tabs/toolbar)
Dim chromePaths(3)
chromePaths(0) = "C:\Program Files\Google\Chrome\Application\chrome.exe"
chromePaths(1) = "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
chromePaths(2) = objShell.ExpandEnvironmentStrings("%LOCALAPPDATA%") & "\Google\Chrome\Application\chrome.exe"
chromePaths(3) = "C:\Program Files\Microsoft\Edge\Application\msedge.exe"

Dim launched
launched = False
Dim i
For i = 0 To 3
  If objFSO.FileExists(chromePaths(i)) Then
    objShell.Run """" & chromePaths(i) & """ --app=http://127.0.0.1:8000 --window-size=1200,800", 1, False
    launched = True
    Exit For
  End If
Next

' Fallback: open in default browser
If Not launched Then
  objShell.Run "explorer http://127.0.0.1:8000"
End If
