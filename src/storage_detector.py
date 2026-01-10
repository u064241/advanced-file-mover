"""
Storage Hardware Detector - Rileva il tipo di storage e ottimizza i parametri

Windows 11+: Usa PowerShell (wmic è deprecato)
Linux: Analizza /sys/block/ e df
macOS: Usa diskutil
"""

import os
import sys
import re
import platform
from pathlib import Path


class StorageDetector:
    """Rileva il tipo di storage (SSD, NVMe, USB, NAS) e ne determina le caratteristiche"""
    
    # Tipologie di storage
    STORAGE_TYPES = {
        'RAMDRIVE': {'name': 'RamDrive', 'speed': 'Estrema (RAM)', 'buffer_mb': 8, 'threads': 16, 'priority': 10},
        'NVME': {'name': 'NVMe', 'speed': 'Ultra-veloce', 'buffer_mb': 256, 'threads': 12, 'priority': 5},
        'SSD': {'name': 'SSD', 'speed': 'Veloce', 'buffer_mb': 128, 'threads': 8, 'priority': 4},
        'USB': {'name': 'USB/External', 'speed': 'Moderato', 'buffer_mb': 64, 'threads': 4, 'priority': 2},
        'NAS': {'name': 'NAS/Network', 'speed': 'Lento', 'buffer_mb': 32, 'threads': 2, 'priority': 1},
        'HDD': {'name': 'HDD', 'speed': 'Lento', 'buffer_mb': 80, 'threads': 2, 'priority': 1},
    }
    
    def __init__(self, ramdrive_manager=None):
        self.storage_cache = {}
        self.ramdrive_manager = ramdrive_manager
        
        # Se fornito RamDriveManager, usa i suoi metodi per rilevamento veloce
        if self.ramdrive_manager:
            self.ramdrive_letter = self.ramdrive_manager.get_ramdrive_letter()
        else:
            self.ramdrive_letter = None
    
    def get_storage_type(self, path):
        """Rileva il tipo di storage per un percorso dato"""
        if not path:
            return self.STORAGE_TYPES['SSD']  # Default
        
        # Normalizza il percorso
        path = str(path).upper()
        
        # Usa cache per drive letter invece che path completo (più efficiente)
        drive_letter = os.path.splitdrive(path)[0]
        if not drive_letter and path.startswith('\\\\'):
            drive_letter = 'UNC'  # Network path
        
        if drive_letter in self.storage_cache:
            return self.storage_cache[drive_letter]
        
        storage_type = self._detect_storage_type(path)
        self.storage_cache[drive_letter] = storage_type
        
        return storage_type
    
    def _detect_storage_type(self, path):
        """Logica di rilevamento del tipo di storage"""
        
        # Estrai lettera drive per ricerca cache
        drive_letter = os.path.splitdrive(path)[0]
        if drive_letter and len(drive_letter) >= 1:
            drive_letter = drive_letter[0].upper()
            
            # Se abbiamo RamDriveManager, usa il suo metodo veloce
            if self.ramdrive_manager:
                storage_type_str = self.ramdrive_manager.get_storage_type(path)
                
                # Mappa il tipo restituito al dizionario STORAGE_TYPES
                type_map = {
                    'ram': 'RAMDRIVE',
                    'nvme': 'NVME',
                    'ssd': 'SSD',
                    'usb': 'USB',
                    'nas': 'NAS',
                    'hdd': 'HDD',
                }
                
                type_key = type_map.get(storage_type_str, 'HDD')
                return self.STORAGE_TYPES[type_key]
        
        # RamDrive (priorità massima) - fallback se RamDriveManager non disponibile
        if self.ramdrive_letter and path.startswith(self.ramdrive_letter.upper() + ':'):
            return self.STORAGE_TYPES['RAMDRIVE']
        
        # Network/NAS (percorsi UNC)
        if path.startswith('\\\\') or '://' in path:
            return self.STORAGE_TYPES['NAS']
        
        # Windows
        if platform.system() == 'Windows':
            return self._detect_windows(path)
        
        # Linux
        elif platform.system() == 'Linux':
            return self._detect_linux(path)
        
        # macOS
        elif platform.system() == 'Darwin':
            return self._detect_macos(path)
        
        # Default
        return self.STORAGE_TYPES['SSD']
    
    def _detect_windows(self, path):
        """Rileva il tipo di storage su Windows usando QueryDosDevice (veloce, accurato)"""
        try:
            # Estrai la lettera drive
            drive_letter = path[0] if len(path) > 0 else 'C'
            
            # PRIMA PRIORITA': Usa ramdrive_manager se disponibile (QueryDosDevice + cache)
            if self.ramdrive_manager:
                try:
                    # scan_all_drives() usa QueryDosDevice per classificazione accurata
                    all_drives = self.ramdrive_manager.scan_all_drives()
                    
                    if drive_letter in all_drives:
                        storage_type_str = all_drives[drive_letter]
                        
                        # Mappa il tipo restituito al dizionario STORAGE_TYPES
                        type_map = {
                            'ram': 'RAMDRIVE',
                            'nvme': 'NVME',
                            'ssd': 'SSD',
                            'usb': 'USB',
                            'nas': 'NAS',
                            'hdd': 'HDD',
                        }
                        
                        type_key = type_map.get(storage_type_str, 'HDD')
                        return self.STORAGE_TYPES[type_key]
                except:
                    pass
            
            # FALLBACK: PowerShell Get-Volume se RamDriveManager non disponibile
            try:
                import subprocess
                
                # PowerShell command per ottenere il drive type (moderno, non deprecato)
                ps_command = f'Get-Volume -DriveLetter {drive_letter} | Select-Object DriveType | ConvertTo-Json'
                
                result = subprocess.run(
                    ['powershell', '-NoProfile', '-Command', ps_command],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    creationflags=0x08000000 if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0  # CREATE_NO_WINDOW
                )
                
                if result.returncode == 0:
                    output = result.stdout.upper()
                    
                    # DriveType: 1=Removable, 2=Fixed, 3=Network, 4=CDRom, 5=RamDisk
                    if '"Fixed"' in output or 'FIXED' in output:
                        # Fixed drive - controlla se SSD o HDD
                        return self._detect_ssd_or_hdd_windows(drive_letter)
                    elif '"Removable"' in output or 'REMOVABLE' in output:
                        return self.STORAGE_TYPES['USB']
                    elif '"Network"' in output or 'NETWORK' in output:
                        return self.STORAGE_TYPES['NAS']
            except:
                pass
        except:
            pass
        
        # Default: SSD
        return self.STORAGE_TYPES['SSD']
    
    def _detect_ssd_or_hdd_windows(self, drive_letter):
        """Distingue tra SSD, NVMe e HDD su Windows usando PowerShell"""
        try:
            import subprocess
            
            # Usa PowerShell per rilevare il tipo di disco (più moderno di wmic deprecato)
            ps_command = (
                "Get-PhysicalDisk | Select-Object -Property FriendlyName, MediaType | "
                "ConvertTo-Json -Compress"
            )
            
            result = subprocess.run(
                ['powershell', '-NoProfile', '-Command', ps_command],
                capture_output=True,
                text=True,
                timeout=5,
                creationflags=0x08000000 if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0  # CREATE_NO_WINDOW
            )
            
            if result.returncode == 0:
                output = result.stdout.upper()
                
                if 'NVME' in output or 'NVME' in output:
                    return self.STORAGE_TYPES['NVME']
                elif 'SSD' in output:
                    return self.STORAGE_TYPES['SSD']
                elif 'HDD' in output:
                    return self.STORAGE_TYPES['HDD']
        except:
            pass
        
        # Se PowerShell fallisce, prova il metodo alternativo con volumi
        try:
            import subprocess
            
            # Alternativa: usa Get-Volume per il drive letter
            ps_command = f'Get-Volume -DriveLetter {drive_letter} | Select-Object FileSystemType | ConvertTo-Json'
            
            result = subprocess.run(
                ['powershell', '-NoProfile', '-Command', ps_command],
                capture_output=True,
                text=True,
                timeout=5,
                creationflags=0x08000000 if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0  # CREATE_NO_WINDOW
            )
            
            if result.returncode == 0 and 'NTFS' in result.stdout.upper():
                # È un NTFS - potrebbe essere SSD di default
                return self.STORAGE_TYPES['SSD']
        except:
            pass
        
        # Default: SSD
        return self.STORAGE_TYPES['SSD']
    
    def _detect_linux(self, path):
        """Rileva il tipo di storage su Linux"""
        try:
            import subprocess
            
            # Ottieni il device mount
            result = subprocess.run(
                ['df', path],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                if len(lines) > 1:
                    device = lines[1].split()[0]
                    
                    # Controlla il device
                    if 'nvme' in device.lower():
                        return self.STORAGE_TYPES['NVME']
                    elif 'sda' in device.lower() or 'sdb' in device.lower():
                        # Controlla se SSD
                        try:
                            result = subprocess.run(
                                ['cat', f'/sys/block/{device.split("/")[-1]}/queue/rotational'],
                                capture_output=True,
                                text=True,
                                timeout=5
                            )
                            if result.returncode == 0 and '0' in result.stdout:
                                return self.STORAGE_TYPES['SSD']
                            else:
                                return self.STORAGE_TYPES['HDD']
                        except:
                            return self.STORAGE_TYPES['SSD']
                    elif 'usb' in device.lower():
                        return self.STORAGE_TYPES['USB']
        except:
            pass
        
        return self.STORAGE_TYPES['SSD']
    
    def _detect_macos(self, path):
        """Rileva il tipo di storage su macOS"""
        try:
            import subprocess
            
            result = subprocess.run(
                ['diskutil', 'info', path],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                output = result.stdout.upper()
                
                if 'SSD' in output or 'SOLID STATE' in output:
                    return self.STORAGE_TYPES['SSD']
                elif 'EXTERNAL' in output or 'USB' in output:
                    return self.STORAGE_TYPES['USB']
        except:
            pass
        
        return self.STORAGE_TYPES['SSD']
    
    def get_optimal_settings(self, source_path, dest_path):
        """
        Calcola i parametri ottimali basati sui percorsi
        Ritorna: {'buffer_mb': int, 'threads': int, 'source_type': str, 'dest_type': str}
        """
        source_type = self.get_storage_type(source_path)
        dest_type = self.get_storage_type(dest_path)
        
        # RAMDRIVE ha priorità massima - se uno dei due è ramdrive, usa i suoi parametri
        source_priority = source_type['priority']
        dest_priority = dest_type['priority']
        
        # Usa il tipo CON PRIORITÀ PIÙ ALTA (ramdrive=10, altri<=5)
        limiting_type = source_type if source_priority >= dest_priority else dest_type
        
        return {
            'buffer_mb': limiting_type['buffer_mb'],
            'threads': limiting_type['threads'],
            'source_type': source_type['name'],
            'dest_type': dest_type['name'],
            'speed_class': limiting_type['speed'],
            'info': f"Copia ottimizzata per {limiting_type['name']} ({limiting_type['speed']})"
        }
    
    def get_storage_info_text(self, path):
        """Ritorna una descrizione testuale del tipo di storage"""
        storage_type = self.get_storage_type(path)
        return f"{storage_type['name']} ({storage_type['speed']})"


def main():
    """Test dello storage detector"""
    detector = StorageDetector()
    
    # Test con percorsi comuni
    test_paths = [
        'C:/',  # Drive principale Windows
        'D:/',  # Drive secondario
        '\\\\192.168.1.1\\share',  # NAS
    ]
    
    print("\n" + "="*60)
    print(" Storage Hardware Detector")
    print("="*60 + "\n")
    
    for path in test_paths:
        print(f"Percorso: {path}")
        info = detector.get_storage_type(path)
        print(f"  Tipo: {info['name']}")
        print(f"  Velocità: {info['speed']}")
        print(f"  Buffer consigliato: {info['buffer_mb']} MB")
        print(f"  Thread consigliati: {info['threads']}")
        print()


if __name__ == '__main__':
    main()
