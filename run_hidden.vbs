Set WshShell = CreateObject("WScript.Shell")
Set objFSO = CreateObject("Scripting.FileSystemObject")
appDir = objFSO.GetParentFolderName(WScript.ScriptFullName)
pythonwExe = "C:\Users\USER\AppData\Local\Programs\Python\Python311\pythonw.exe"
If Not objFSO.FileExists(pythonwExe) Then
  pythonwExe = "pythonw.exe"
End If
WshShell.Run """" & pythonwExe & """ """ & appDir & "\app.py""", 0, False
Set WshShell = Nothing
