Set oShell = CreateObject("WScript.Shell")
Dim batPath
batPath = Replace(WScript.ScriptFullName, "iniciar_backend_oculto.vbs", "iniciar_backend_servico.bat")
oShell.Run "cmd /c """ & batPath & """", 0, False
