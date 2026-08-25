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
    lp = long_path(path)
    return os.path.exists(lp) and os.access(lp, os.R_OK)


def is_path_writable(path: str) -> bool:
    """Verifica se il percorso è scrivibile"""
    return os.access(long_path(path), os.W_OK)


def get_file_size(path: str) -> int:
    """Ottiene dimensione file o cartella"""
    try:
        lp = long_path(path)
        if os.path.isfile(lp):
            return os.path.getsize(lp)
        else:
            total_size = 0
            for dirpath, dirnames, filenames in os.walk(lp):
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
        os.makedirs(long_path(path), exist_ok=True)
        return True
    except Exception as e:
        print(f"Errore creazione directory: {e}")
        return False


def get_filesystem_type(path: str) -> str:
    """Ritorna il tipo di filesystem (es. 'FAT32', 'NTFS', 'exFAT') della destinazione, '' se non determinabile."""
    if os.name != 'nt':
        return ''
    try:
        drive = os.path.splitdrive(path)[0]
        if not drive:
            return ''
        root = drive + '\\'
        fs_name = ctypes.create_unicode_buffer(260)
        ok = ctypes.windll.kernel32.GetVolumeInformationW(
            ctypes.c_wchar_p(root),
            None, 0, None, None, None,
            fs_name, 260
        )
        return fs_name.value if ok else ''
    except Exception:
        return ''


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


def long_path(path: str) -> str:
    """
    Aggiunge il prefisso \\\\?\\ per supportare path > 260 caratteri su Windows.
    Su sistemi non-Windows restituisce il path invariato.
    Gestisce correttamente path UNC (\\\\server\\share → \\\\?\\UNC\\server\\share).
    """
    if os.name != 'nt' or not path:
        return path
    # Normalizza e rendi assoluto
    path = os.path.abspath(path)
    # Già prefissato
    if path.startswith('\\\\?\\'):
        return path
    # UNC path (\\server\share)
    if path.startswith('\\\\'):
        return '\\\\?\\UNC\\' + path[2:]
    return '\\\\?\\' + path


def strip_long_path_prefix(path: str) -> str:
    """
    Rimuove il prefisso \\\\?\\ dal path per visualizzazione/UI.
    Utile quando il path deve essere mostrato all'utente.
    """
    if not path:
        return path
    if path.startswith('\\\\?\\UNC\\'):
        return '\\\\' + path[8:]
    if path.startswith('\\\\?\\'):
        return path[4:]
    return path


def enable_long_paths():
    """Abilita supporto long paths in Windows (richiede privilegi amministratore)"""
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                            r'SYSTEM\CurrentControlSet\Control\FileSystem')
        winreg.SetValueEx(key, 'LongPathsEnabled', 0, winreg.REG_DWORD, 1)
        winreg.CloseKey(key)
        return True
    except:
        return False
