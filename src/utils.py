"""
Modulo utilità per Advanced File Mover
"""
import os
import sys
import ctypes
import subprocess
from pathlib import Path
from typing import Tuple, Optional


def is_admin() -> bool:
    """Verifica se il programma è eseguito come amministratore"""
    try:
        return ctypes.windll.shell.IsUserAnAdmin()
    except:
        return False


def get_drive_info(path: str) -> Tuple[float, float, float]:
    """
    Ottiene info spazio su disco
    
    Returns:
        Tuple di (total, used, free) in bytes
    """
    try:
        drive = os.path.splitdrive(path)[0]
        if not drive:
            drive = os.path.dirname(path)
        
        import shutil
        total, used, free = shutil.disk_usage(drive)
        return total, used, free
    except Exception as e:
        print(f"Errore lettura info disco: {e}")
        return 0, 0, 0


def format_bytes(bytes_val: float) -> str:
    """Formatta bytes in formato leggibile"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_val < 1024.0:
            return f"{bytes_val:.2f} {unit}"
        bytes_val /= 1024.0
    return f"{bytes_val:.2f} PB"


def format_time(seconds: float) -> str:
    """Formatta secondi in formato leggibile"""
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{int(minutes)}m {int(seconds % 60)}s"
    else:
        hours = seconds / 3600
        mins = (seconds % 3600) / 60
        return f"{int(hours)}h {int(mins)}m"


def is_path_accessible(path: str) -> bool:
    """Verifica se il percorso è accessibile"""
    return os.path.exists(path) and os.access(path, os.R_OK)


def is_path_writable(path: str) -> bool:
    """Verifica se il percorso è scrivibile"""
    return os.access(path, os.W_OK)


def get_file_size(path: str) -> int:
    """Ottiene dimensione file o cartella"""
    try:
        if os.path.isfile(path):
            return os.path.getsize(path)
        else:
            total_size = 0
            for dirpath, dirnames, filenames in os.walk(path):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    try:
                        total_size += os.path.getsize(filepath)
                    except:
                        pass
            return total_size
    except:
        return 0


def create_directory_if_not_exists(path: str) -> bool:
    """Crea directory se non esiste"""
    try:
        os.makedirs(path, exist_ok=True)
        return True
    except Exception as e:
        print(f"Errore creazione directory: {e}")
        return False


def get_command_output(command: str) -> str:
    """Esegue comando e ritorna output"""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.stdout.strip()
    except:
        return ""


def enable_long_paths():
    """Abilita supporto long paths in Windows"""
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                            r'SYSTEM\CurrentControlSet\Control\FileSystem')
        winreg.SetValueEx(key, 'LongPathsEnabled', 0, winreg.REG_DWORD, 1)
        winreg.CloseKey(key)
        return True
    except:
        return False
