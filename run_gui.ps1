# Script PowerShell per avviare la GUI con .venv312
# Uso: .\run_gui.ps1

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Avvia la GUI
& "C:\SOURCECODE\.venv312\Scripts\python.exe" "$ScriptDir\ui\gui_customtkinter.py"
