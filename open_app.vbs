Set objShell = CreateObject("WScript.Shell")
Set objFSO = CreateObject("Scripting.FileSystemObject")

appDir = objFSO.GetParentFolderName(WScript.ScriptFullName)
scriptPath = appDir & "\app.py"

' Find pythonw.exe to run silently without opening any IDE or command prompt
pythonwExe = "C:\Users\USER\AppData\Local\Programs\Python\Python311\pythonw.exe"
If Not objFSO.FileExists(pythonwExe) Then
  pythonwExe = "pythonw.exe"
End If

' Start FastAPI backend silently in background using pythonw.exe
objShell.Run """" & pythonwExe & """ """ & scriptPath & """", 0, False

' Brief pause to allow server to be ready
WScript.Sleep 1500

' Launch dedicated Chrome/Edge app window
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
