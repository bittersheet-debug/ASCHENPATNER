' Script peluncur background MEDIAPATNER BOT (Mode Tersembunyi / Tanpa Jendela Terminal)
Set WshShell = CreateObject("WScript.Shell")
strPath = WshShell.CurrentDirectory
WshShell.Run """" & strPath & "\run_permanent.bat""", 0, False
Set WshShell = Nothing
