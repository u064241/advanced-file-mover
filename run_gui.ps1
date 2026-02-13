# Script PowerShell per avviare la GUI con .venv
# Uso: .\run_gui.ps1

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Avvia la GUI
& "C:\SOURCECODE\.venv\Scripts\python.exe" "$ScriptDir\ui\gui_customtkinter.py"
