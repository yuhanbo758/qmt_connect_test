
Set objShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
currentDir = fso.GetParentFolderName(WScript.ScriptFullName)
scriptPath = currentDir & "\qmt_download_and_connect_test.py"
objShell.Run "cmd /c python """ & scriptPath & """", 0, True
