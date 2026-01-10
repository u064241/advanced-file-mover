"""
Modulo gestione RamDrive - Rilevamento multi-metodo con QueryDosDevice
Metodi: 1) QueryDosDevice (veloce, all drives), 2) Software noto, 3) WMI, 4) API Windows, 5) SetupAPI
"""
import os
import sys
import subprocess
import json
from typing import Optional, List, Tuple, Dict
from pathlib import Path
from ctypes import sizeof
from .utils import get_command_output, format_bytes


class RamDriveManager:
    """Gestisce RamDrive (imdisk, RAMDisk, etc.) con rilevamento robusto via QueryDosDevice"""
    
    def __init__(self):
        self.ramdrive_letter: Optional[str] = None
        self.detected_software = []
        self._detection_attempted = False
        self._all_drives_cache: Dict[str, str] = {}  # Cache: lettera -> tipo (ram, ssd, hdd, nvme, usb)
        self._drives_scanned = False
        self._classification_cache: Dict[str, str] = {}  # Cache per classificazione accurata (più lenta)
        
        # Carica cache persistente dai precedenti avvii
        self._load_persistent_cache()
        
        # Carica override manuale da config.json
        self._load_config_overrides()
        
        # NON eseguire rilevamento nel __init__ - troppo lento!
        # Verrà fatto lazy quando richiesto
    
    def _load_persistent_cache(self):
        """Carica la cache persistente di classificazione da file JSON"""
        try:
            cache_file = self._get_persistent_cache_path()
            if cache_file.exists():
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cached_data = json.load(f)

                classification = cached_data.get('classification', {})
                serials = cached_data.get('serials', {})

                # Invalida entry se la lettera punta a un volume diverso (drive letter changed)
                cleaned = {}
                for letter, stype in (classification or {}).items():
                    try:
                        letter_u = str(letter).upper().strip(':')
                        if letter_u and letter_u[0] in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
                            root = f"{letter_u[0]}:\\"
                            current_serial = self._get_volume_serial(root)
                            cached_serial = serials.get(letter_u) if isinstance(serials, dict) else None
                            if cached_serial is not None and current_serial is not None and int(cached_serial) != int(current_serial):
                                continue
                            cleaned[letter_u] = stype
                    except Exception:
                        continue

                self._classification_cache = cleaned
        except:
            pass
    
    def _save_persistent_cache(self):
        """Salva la cache persistente di classificazione su file JSON"""
        try:
            cache_file = self._get_persistent_cache_path()
            try:
                cache_file.parent.mkdir(parents=True, exist_ok=True)
            except Exception:
                pass

            serials = {}
            try:
                for letter in list(self._classification_cache.keys()):
                    letter_u = str(letter).upper().strip(':')
                    if not letter_u:
                        continue
                    root = f"{letter_u[0]}:\\"
                    s = self._get_volume_serial(root)
                    if s is not None:
                        serials[letter_u] = int(s)
            except Exception:
                serials = {}

            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump({'classification': self._classification_cache, 'serials': serials}, f, indent=2)
        except:
            pass

    def _get_persistent_cache_path(self) -> Path:
        """Percorso cache persistente (scrivibile anche in modalità EXE)."""
        try:
            local_appdata = Path(os.environ.get('LOCALAPPDATA', str(Path.home() / 'AppData' / 'Local')))
        except Exception:
            local_appdata = Path.home() / 'AppData' / 'Local'

        return local_appdata / 'AdvancedFileMover' / '.storage_cache.json'

    def _get_volume_serial(self, root_path: str):
        """Ritorna il serial del volume per invalidare cache quando cambia lettera."""
        try:
            import ctypes
            from ctypes import wintypes

            vol_name = ctypes.create_unicode_buffer(255)
            fs_name = ctypes.create_unicode_buffer(255)
            serial = wintypes.DWORD()
            max_comp = wintypes.DWORD()
            flags = wintypes.DWORD()

            ok = ctypes.windll.kernel32.GetVolumeInformationW(
                ctypes.c_wchar_p(str(root_path)),
                vol_name,
                255,
                ctypes.byref(serial),
                ctypes.byref(max_comp),
                ctypes.byref(flags),
                fs_name,
                255,
            )
            if ok:
                return int(serial.value)
        except Exception:
            pass
        return None
    
    def _load_config_overrides(self):
        """Carica override manuale della detection storage da config.json"""
        try:
            # Prima scelta: config utente (scrivibile) in LocalAppData
            try:
                local_appdata = Path(os.environ.get('LOCALAPPDATA', str(Path.home() / 'AppData' / 'Local')))
            except Exception:
                local_appdata = Path.home() / 'AppData' / 'Local'

            config_file = local_appdata / 'AdvancedFileMover' / 'config.json'

            # Fallback: config "bundled" vicino all'exe/progetto
            if not config_file.exists():
                if getattr(sys, 'frozen', False):
                    app_root = Path(sys.executable).parent
                else:
                    app_root = Path(__file__).parent.parent

                config_file = app_root / "config.json"
            
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    overrides = config.get('storage_type_override', {})
                    
                    # Carica gli override nella classification cache
                    for letter, storage_type in overrides.items():
                        # Salta il comment field
                        if letter != "comment" and storage_type in ["ram", "ssd", "hdd", "nvme", "usb", "nas"]:
                            self._classification_cache[letter] = storage_type
        except:
            pass
    
    def detect_ramdrive(self) -> bool:
        """Rileva se è disponibile un RamDrive (lazy, multi-metodo)"""
        if self._detection_attempted:
            # Se abbiamo già una lettera, verifica che sia ancora valida
            if self.ramdrive_letter and os.path.exists(f"{self.ramdrive_letter}:\\"):
                return True
            # Se non esiste più (o non valida), consenti nuova detection
            self.ramdrive_letter = None
            self.detected_software = []
            self._detection_attempted = False
        
        self._detection_attempted = True
        
        # PRIORITA': QueryDosDevice (velocissimo, affidabile, API nativa)
        if self._check_querydosdevice():
            return True
        
        # Metodo 2: API Windows (GetDriveTypeW - veloce)
        if self._check_windows_api_ramdrive():
            return True
        
        # Metodo 3: SoftPerfect RamDisk (specifico, veloce)
        if self._check_softperfect_ramdisk():
            return True
        
        # Metodo 4: Controlla software RamDrive noti
        if self._check_ramdrive_software():
            return True
        
        # Metodo 5: WMI per cercare dischi logici (medio)
        if self._check_wmi_ramdrive():
            return True
        
        # PowerShell è LENTO - usare solo come ultima risorsa, mai all'avvio
        # Metodo 6 e 7 commentate per non rallentare l'app
        # if self._check_powershell_ramdrive():
        #     return True
        # if self._check_powershell_physical():
        #     return True
        
        # Metodo 8: SetupAPI - enumerazione dispositivi storage
        if self._check_setupapi_devices():
            return True
        
        return False

    def refresh_ramdrive(self) -> bool:
        """Forza un refresh della detection RamDrive (utile se lettera/dimensione cambia a runtime)."""
        try:
            self.ramdrive_letter = None
            self.detected_software = []
            self._detection_attempted = False
        except Exception:
            pass
        return self.detect_ramdrive()
    
    def _check_ramdrive_software(self) -> bool:
        """Controlla software RamDrive installato"""
        # imdisk (spesso usato)
        if self._check_imdisk():
            self.detected_software.append('imdisk')
            return True
        
        # RAMDisk (SoftPerfect)
        if self._check_ramdisk():
            self.detected_software.append('RAMDisk')
            return True
        
        # ImDisk virtual Disk Driver
        if self._check_imdisk_driver():
            self.detected_software.append('ImDisk Driver')
            return True
        
        return False
    
    def _check_querydosdevice(self) -> bool:
        """Metodo QueryDosDevice (API Windows - più affidabile)"""
        try:
            import ctypes
            from ctypes import wintypes
            
            kernel32 = ctypes.windll.kernel32
            
            # Scansiona tutti i drive presenti
            for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
                if not os.path.exists(f"{letter}:\\"):
                    continue
                
                try:
                    # QueryDosDevice mostra il percorso del dispositivo sottostante
                    buffer = ctypes.create_unicode_buffer(1024)
                    res = kernel32.QueryDosDeviceW(f"{letter}:", buffer, 1024)
                    
                    if res == 0:
                        continue
                    
                    device_path = buffer.value.lower()
                    
                    # Cerca keyword nel device path
                    ram_keywords = ["ram", "imdisk", "softperfect", "osfmount", "virtual", "awealloc"]
                    
                    if any(kw in device_path for kw in ram_keywords):
                        self.ramdrive_letter = letter
                        self.detected_software.append(f'QueryDosDevice ({device_path[:50]})')
                        return True
                    
                    # Controlla anche volume info
                    vol_name = ctypes.create_unicode_buffer(255)
                    fs_name = ctypes.create_unicode_buffer(255)
                    serial = wintypes.DWORD()
                    max_comp = wintypes.DWORD()
                    flags = wintypes.DWORD()
                    
                    ok = kernel32.GetVolumeInformationW(
                        f"{letter}:\\",
                        vol_name, 255,
                        ctypes.byref(serial),
                        ctypes.byref(max_comp),
                        ctypes.byref(flags),
                        fs_name, 255
                    )
                    
                    if ok:
                        vol_label = vol_name.value.lower()
                        # Volume label suggerisce RAM?
                        if any(kw in vol_label for kw in ["ram", "temp", "volatile", "memory"]):
                            self.ramdrive_letter = letter
                            self.detected_software.append(f'Volume-Label ({vol_label})')
                            return True
                    
                    # Drive Type + path virtuale (senza harddisk)
                    dtype = kernel32.GetDriveTypeW(f"{letter}:\\")
                    if dtype == 3 and "volume" in device_path and "harddisk" not in device_path:
                        self.ramdrive_letter = letter
                        self.detected_software.append('Fixed-VirtualPath')
                        return True
                
                except:
                    continue
            
            return False
        except:
            return False
    
    def _check_imdisk(self) -> bool:
        """Controlla se imdisk è installato"""
        try:
            output = get_command_output("imdisk -l")
            if output and len(output) > 0:
                # Estrai lettera drive da output
                for line in output.split('\n'):
                    if 'Mount point' in line or 'letter' in line.lower():
                        # Prova a estrarre lettera
                        for char in line.upper():
                            if char in 'CDEFGHIJKLMNOPQRSTUVWXYZ':
                                self.ramdrive_letter = char
                                return True
            return False
        except:
            return False
    
    def _check_softperfect_ramdisk(self) -> bool:
        """Controlla SoftPerfect RamDisk (processo, driver, volumi)"""
        try:
            # Metodo 1: Cerca il processo RAMDisk.exe
            result = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq RAMDisk.exe"],
                capture_output=True,
                text=True,
                creationflags=0x08000000
            )
            
            if "RAMDisk.exe" not in result.stdout:
                return False
            
            # RAMDisk.exe è in esecuzione - scansiona TUTTI i drive per trovare il RamDisk
            import ctypes
            import shutil
            
            for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
                root = f"{letter}:\\"
                
                try:
                    if not os.path.exists(root):
                        continue
                    
                    # Controlla spazio e uso del drive
                    total, used, free = shutil.disk_usage(root)
                    
                    if total == 0:
                        continue
                    
                    usage_percent = (total - free) / total
                    size_mb = total / (1024 * 1024)
                    
                    # RamDisk: 
                    # - Poco usato (<10%)
                    # - Size 100MB - 100GB (tipico RamDisk)
                    if (usage_percent < 0.10 and 
                        100 <= size_mb <= 102400):
                        
                        # Leggi label per conferma
                        try:
                            vol_name = ctypes.create_string_buffer(255)
                            fs_name = ctypes.create_string_buffer(255)
                            
                            ctypes.windll.kernel32.GetVolumeInformationW(
                                ctypes.c_wchar_p(root),
                                vol_name, sizeof(vol_name),
                                None, None, None,
                                fs_name, sizeof(fs_name)
                            )
                            
                            label = vol_name.value.decode('utf-8', errors='ignore') if vol_name.value else ""
                        except:
                            label = ""
                        
                        # Se ha label RAM-like, è sicuramente RamDisk
                        # Altrimenti, con RAMDisk.exe in esecuzione e questo profilo, è comunque RamDisk
                        self.ramdrive_letter = letter
                        self.detected_software.append('SoftPerfect-RamDisk')
                        return True
                
                except:
                    continue
            
            return False
        except:
            return False
    
    def _check_ramdisk(self) -> bool:
        """Controlla se RAMDisk è installato"""
        try:
            result = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq RAMDisk.exe"],
                capture_output=True,
                text=True,
                creationflags=0x08000000  # CREATE_NO_WINDOW
            )
            return "RAMDisk.exe" in result.stdout
        except:
            return False
    
    def _check_imdisk_driver(self) -> bool:
        """Controlla se ImDisk Driver è disponibile"""
        try:
            output = get_command_output("sc query imdisk")
            return "RUNNING" in output or "STOPPED" in output
        except:
            return False
    
    def _check_wmi_ramdrive(self) -> bool:
        """Metodo WMI per rilevare RamDrive (Windows 10+)"""
        try:
            # Usa wmic per cercare dischi logici con characteristics di ramdrive
            result = subprocess.run(
                [
                    "wmic", "logicaldisk",
                    "get", "Name,Description,DriveType,Size,FreeSpace",
                    "/format:csv"
                ],
                capture_output=True,
                text=True,
                timeout=5,
                creationflags=0x08000000  # CREATE_NO_WINDOW
            )
            
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                for line in lines:
                    if not line.strip():
                        continue
                    
                    parts = [p.strip() for p in line.split(',')]
                    if len(parts) >= 5:
                        name = parts[1].strip('"')  # es. "C:"
                        description = parts[2].strip('"') if len(parts) > 2 else ""
                        
                        # Cerca keyword nel description
                        if any(keyword in description.upper() for keyword in ['RAM', 'MEMORY', 'VIRTUAL']):
                            if name and name[0] in 'CDEFGHIJKLMNOPQRSTUVWXYZ':
                                self.ramdrive_letter = name[0]
                                self.detected_software.append('WMI-detected')
                                return True
            
            return False
        except:
            return False
    
    def _check_powershell_ramdrive(self) -> bool:
        """Metodo PowerShell Get-Volume (nascosto)"""
        try:
            # Comando PowerShell nascosto per Get-Volume
            ps_cmd = (
                "Get-Volume | Where-Object {$_ -and $_.DriveLetter -and "
                "($_.DriveType -eq 'Ram' -or $_.DriveType -eq 6 -or "
                "$_.Description -match 'RAM|Memory|Virtual' -or $_.FileSystemLabel -match 'RAM')} | "
                "Select-Object -ExpandProperty DriveLetter"
            )
            
            result = subprocess.run(
                ["powershell.exe", "-NoProfile", "-Command", ps_cmd],
                capture_output=True,
                text=True,
                timeout=5,
                creationflags=0x08000000 | 0x00000200  # CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP
            )
            
            if result.returncode == 0 and result.stdout.strip():
                letter = result.stdout.strip()[0].upper()
                if letter in 'CDEFGHIJKLMNOPQRSTUVWXYZ':
                    self.ramdrive_letter = letter
                    self.detected_software.append('PowerShell-detected')
                    return True
            
            return False
        except:
            return False

    def _check_powershell_physical(self) -> bool:
        """Metodo PowerShell Get-PhysicalDisk per BusType/Name"""
        try:
            ps_cmd = (
                "Get-PhysicalDisk | Where-Object {$_ -and "
                "( $_.BusType -eq 'RAM' -or $_.BusType -eq 6 -or "
                "$_.FriendlyName -match 'ram|imdisk|soft|erd|amd|amd64' -or "
                "$_.Model -match 'ram|imdisk|soft|erd' -or $_.SerialNumber -match 'ram' )} | "
                "Select-Object -ExpandProperty DeviceId"
            )

            result = subprocess.run(
                ["powershell.exe", "-NoProfile", "-Command", ps_cmd],
                capture_output=True,
                text=True,
                timeout=5,
                creationflags=0x08000000 | 0x00000200
            )

            if result.returncode == 0 and result.stdout.strip():
                # Una volta identificato un PhysicalDisk RAM, mappa i LogicalDisk sullo stesso device
                device_id = result.stdout.strip().splitlines()[0].strip()
                map_cmd = (
                    f"$d='{device_id}'; "
                    "Get-CimInstance Win32_LogicalDiskToPartition | ForEach-Object { "
                    "$p = $_.Antecedent.DeviceID; $l = $_.Dependent.DeviceID; "
                    "if ($p -match 'Disk #' -and $p -match $d) { $l } }"
                )

                map_res = subprocess.run(
                    ["powershell.exe", "-NoProfile", "-Command", map_cmd],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    creationflags=0x08000000 | 0x00000200
                )

                if map_res.returncode == 0 and map_res.stdout.strip():
                    # Prendi la prima lettera logica associata
                    logical = map_res.stdout.strip().splitlines()[0].strip()
                    if logical and logical[0].upper() in 'CDEFGHIJKLMNOPQRSTUVWXYZ':
                        self.ramdrive_letter = logical[0].upper()
                        self.detected_software.append('PowerShell-Physical')
                        return True

            return False
        except:
            return False
    
    def _check_setupapi_devices(self) -> bool:
        """Metodo SetupAPI (SetupDiGetClassDevs, SetupDiEnumDeviceInfo, SetupDiGetDeviceRegistryProperty)"""
        try:
            import ctypes
            from ctypes import c_char_p, c_void_p, c_ulong, POINTER, Structure, byref, sizeof
            
            # Costanti
            DIGCF_PRESENT = 0x00000002
            SPDRP_FRIENDLYNAME = 12
            SPDRP_DESCRIPTION = 0
            SPDRP_BUSTYPE = 23
            MAX_PATH = 260
            
            # GUID per Storage devices
            STORAGE_DEVICE_GUID = (0x53F56307, 0xB6BF, 0x11D0, (0x94, 0xF2, 0x00, 0xA0, 0xC9, 0x1E, 0xFB, 0x8B))
            
            # Strutture
            class SP_DEVINFO_DATA(Structure):
                pass
            SP_DEVINFO_DATA._fields_ = [
                ("cbSize", c_ulong),
                ("ClassGuid", ctypes.c_char * 16),
                ("DevInst", c_ulong),
                ("Reserved", c_ulong)
            ]
            
            # API calls
            setupapi = ctypes.windll.setupapi
            SetupDiGetClassDevs = setupapi.SetupDiGetClassDevsW
            SetupDiGetClassDevs.argtypes = [c_char_p, c_char_p, c_void_p, c_ulong]
            SetupDiGetClassDevs.restype = c_void_p
            
            SetupDiEnumDeviceInfo = setupapi.SetupDiEnumDeviceInfo
            SetupDiEnumDeviceInfo.argtypes = [c_void_p, c_ulong, POINTER(SP_DEVINFO_DATA)]
            SetupDiEnumDeviceInfo.restype = ctypes.c_bool
            
            SetupDiGetDeviceRegistryProperty = setupapi.SetupDiGetDeviceRegistryPropertyW
            SetupDiGetDeviceRegistryProperty.argtypes = [c_void_p, POINTER(SP_DEVINFO_DATA), c_ulong, POINTER(c_ulong), c_char_p, c_ulong, POINTER(c_ulong)]
            SetupDiGetDeviceRegistryProperty.restype = ctypes.c_bool
            
            SetupDiDestroyDeviceInfoList = setupapi.SetupDiDestroyDeviceInfoList
            SetupDiDestroyDeviceInfoList.argtypes = [c_void_p]
            SetupDiDestroyDeviceInfoList.restype = ctypes.c_bool
            
            # Crea GUID per storage
            class GUID(Structure):
                pass
            GUID._fields_ = [("Data1", c_ulong), ("Data2", ctypes.c_short), ("Data3", ctypes.c_short), ("Data4", ctypes.c_byte * 8)]
            
            guid = GUID()
            guid.Data1 = STORAGE_DEVICE_GUID[0]
            guid.Data2 = STORAGE_DEVICE_GUID[1]
            guid.Data3 = STORAGE_DEVICE_GUID[2]
            for i, b in enumerate(STORAGE_DEVICE_GUID[3]):
                guid.Data4[i] = b
            
            # Get device list
            hDevInfo = SetupDiGetClassDevs(None, None, None, DIGCF_PRESENT)
            if not hDevInfo or hDevInfo == -1:
                return False
            
            try:
                devinfo = SP_DEVINFO_DATA()
                devinfo.cbSize = sizeof(SP_DEVINFO_DATA)
                index = 0
                
                while SetupDiEnumDeviceInfo(hDevInfo, index, byref(devinfo)):
                    # Leggi FriendlyName
                    friendly_name = ctypes.create_string_buffer(MAX_PATH)
                    needed = c_ulong()
                    
                    if SetupDiGetDeviceRegistryProperty(
                        hDevInfo, byref(devinfo), SPDRP_FRIENDLYNAME,
                        None, friendly_name, MAX_PATH, byref(needed)
                    ):
                        name = friendly_name.value.decode('utf-8', errors='ignore')
                        if any(kw in name.upper() for kw in ['RAM', 'IMDISK', 'MEMORY']):
                            # Trovato device RAM, prova ad estrarre lettera
                            if '(' in name and ')' in name:
                                letter = name[name.rfind('(') + 1:name.rfind(')')].strip().upper()
                                if letter in 'CDEFGHIJKLMNOPQRSTUVWXYZ':
                                    self.ramdrive_letter = letter
                                    self.detected_software.append('SetupAPI')
                                    return True
                    
                    index += 1
                
                return False
            finally:
                SetupDiDestroyDeviceInfoList(hDevInfo)
        except Exception as e:
            return False
    
    def _check_windows_api_ramdrive(self) -> bool:
        """Metodo API Windows nativa (ctypes) - check multi-criteri"""
        try:
            import ctypes
            GetDriveTypeW = ctypes.windll.kernel32.GetDriveTypeW
            GetLogicalDrives = ctypes.windll.kernel32.GetLogicalDrives
            DRIVE_RAMDISK = 6

            mask = GetLogicalDrives()

            # Passata 1: GetDriveTypeW su tutte le lettere presenti nel bitmask
            for i in range(26):
                if not (mask & (1 << i)):
                    continue
                letter = chr(ord('A') + i)
                root = f"{letter}:\\"

                try:
                    dtype = GetDriveTypeW(ctypes.c_wchar_p(root))
                    if dtype == DRIVE_RAMDISK:
                        self.ramdrive_letter = letter
                        self.detected_software.append('API-GetDriveType')
                        return True
                except:
                    pass

            # Passata 2: controllo spazio/uso su tutte le lettere presenti
            for i in range(26):
                if not (mask & (1 << i)):
                    continue
                letter = chr(ord('A') + i)
                root = f"{letter}:\\"

                try:
                    free_bytes = ctypes.c_ulonglong(0)
                    total_bytes = ctypes.c_ulonglong(0)

                    result = ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                        root,
                        ctypes.byref(free_bytes),
                        ctypes.byref(total_bytes),
                        None
                    )

                    if result == 0:
                        continue

                    free = free_bytes.value
                    total = total_bytes.value

                    if total > 0:
                        usage_percent = (total - free) / total
                        if (usage_percent < 0.1 and
                            100 * 1024 * 1024 <= total <= 100 * 1024 * 1024 * 1024):

                            self.ramdrive_letter = letter
                            self.detected_software.append(f'API-detected ({format_bytes(total)})')
                            return True
                except:
                    continue

            return False
        except:
            return False
    
    def get_ramdrive_letter(self) -> Optional[str]:
        """Ritorna lettera drive RamDrive se disponibile"""
        if self.ramdrive_letter:
            return self.ramdrive_letter
        
        # Trigger lazy detection se non fatto
        if not self._detection_attempted:
            self.detect_ramdrive()
        
        return self.ramdrive_letter
    
    def get_ramdrive_free_space(self) -> Tuple[int, int]:
        """Ritorna (free, total) in bytes per RamDrive"""
        letter = self.get_ramdrive_letter()
        if not letter:
            return 0, 0
        
        try:
            import shutil
            total, used, free = shutil.disk_usage(f"{letter}:\\")
            return free, total
        except:
            return 0, 0
    
    def is_ramdrive_available(self) -> bool:
        """Verifica disponibilità RamDrive"""
        return self.get_ramdrive_letter() is not None
    
    def get_ramdrive_info(self) -> dict:
        """Ritorna info RamDrive"""
        letter = self.get_ramdrive_letter()
        if not letter:
            return {
                'available': False,
                'software': []
            }
        
        free, total = self.get_ramdrive_free_space()
        
        return {
            'available': True,
            'letter': letter,
            'total': total,
            'free': free,
            'used': total - free,
            'software': self.detected_software,
            'total_formatted': format_bytes(total),
            'free_formatted': format_bytes(free)
        }
    
    def scan_all_drives(self) -> Dict[str, str]:
        """Scansiona TUTTI i drive con QueryDosDevice e classifica per tipo di storage"""
        if self._drives_scanned:
            return self._all_drives_cache
        
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            
            # Scansiona tutti i drive presenti
            for letter in 'CDEFGHIJKLMNOPQRSTUVWXYZ':  # Salta A e B (floppy)
                if not os.path.exists(f"{letter}:\\"):
                    continue
                
                try:
                    # QueryDosDevice mostra il percorso del dispositivo sottostante
                    buffer = ctypes.create_unicode_buffer(1024)
                    res = kernel32.QueryDosDeviceW(f"{letter}:", buffer, 1024)
                    
                    if res == 0:
                        continue
                    
                    device_path = buffer.value.lower()
                    
                    # Classifica per tipo di storage in base al device path
                    storage_type = self._classify_storage_by_path(device_path, letter)
                    self._all_drives_cache[letter] = storage_type
                
                except Exception as e:
                    continue
            
            self._drives_scanned = True
            return self._all_drives_cache
        except:
            return {}
    
    def _classify_storage_by_path(self, device_path: str, letter: str) -> str:
        """Classifica il tipo di storage dal device path QueryDosDevice + GetDriveType (NON PowerShell - troppo lento)"""
        device_path_lower = device_path.lower()
        
        # === PRIMO CHECK: Volume label per accuratezza (veloce, non-sincrono) ===
        # Questo è prioritario perché è il nome "umano" del volume
        try:
            import ctypes
            vol_name = ctypes.create_unicode_buffer(255)
            fs_name = ctypes.create_unicode_buffer(255)
            
            ok = ctypes.windll.kernel32.GetVolumeInformationW(
                f"{letter}:\\",
                vol_name, 255,
                None, None, None,
                fs_name, 255
            )
            
            if ok:
                vol_label = vol_name.value.lower() if vol_name.value else ""
                
                # Check volume label per keywords specifici - PRIORITARIO
                if any(kw in vol_label for kw in ["ram", "imdisk", "ramdisk", "ram-disk", "memory"]):
                    return "ram"
                
                if any(kw in vol_label for kw in ["nvme", "nvm express"]):
                    return "nvme"
                
                if any(kw in vol_label for kw in ["usb", "sandisk", "kingston", "removable"]):
                    return "usb"
        except:
            pass
        
        # === SECONDO CHECK: RamDrive keywords nel device path ===
        if any(kw in device_path_lower for kw in ["ram", "imdisk", "softperfect", "osfmount", "awealloc", "virtual"]):
            return "ram"
        
        # Se device path è \Device\XXXXXXXX (numero hex puro), probabilmente RAM disk
        # Questo pattern è specifico di RAM drives come imdisk con numeri di device ID
        import re
        if re.match(r'^\\device\\[0-9a-f]+$', device_path_lower.strip()):
            return "ram"
        
        # NVME keywords (device manufacturer, non model number)
        if any(kw in device_path_lower for kw in ["nvme", "nvm express"]):
            return "nvme"
        
        # SSD keywords
        if any(kw in device_path_lower for kw in ["ssd", "solid state"]):
            return "ssd"
        
        # USB (chiavette, dischi esterni)
        if any(kw in device_path_lower for kw in ["usbstor", "usb", "removable"]):
            return "usb"
        
        # NAS/Network
        if any(kw in device_path_lower for kw in ["network", "webdav", "mup", "lanman"]):
            return "nas"
        
        # HDD specifici (brand/model, NON "harddisk" generico)
        if any(kw in device_path_lower for kw in ["seagate", "western digital", "wd", "hitachi", "toshiba"]):
            return "hdd"
        
        # === FASE 2: Se device_path è generico (\device\harddiskvolume), usa GetDriveType ===
        # Questo distingue USB (REMOVABLE) da NVME/SSD/HDD (FIXED)
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            
            drive_type = kernel32.GetDriveTypeW(f"{letter}:\\")
            
            # DRIVE_REMOVABLE = 2 (USB, memory card, floppy)
            if drive_type == 2:
                return "usb"
            
            # DRIVE_FIXED = 3 (HDD, SSD, NVMe, RamDrive)
            # Fallback: controlla se è un disco removibile (alcune USB sono reportate come FIXED)
            # usando il volume label o altri metodi
            if drive_type == 3:
                # Ulteriore controllo: alcuni USB hanno "removable" nel volume label
                try:
                    vol_name = ctypes.create_unicode_buffer(255)
                    fs_name = ctypes.create_unicode_buffer(255)
                    
                    ok = ctypes.windll.kernel32.GetVolumeInformationW(
                        f"{letter}:\\",
                        vol_name, 255,
                        None, None, None,
                        fs_name, 255
                    )
                    
                    if ok and vol_name.value:
                        vol_label = vol_name.value.lower()
                        # Se volume contiene keywords USB
                        if any(kw in vol_label for kw in ["usb", "removable", "sandisk", "kingston", "transcend", "crucial"]):
                            return "usb"
                        # Se volume contiene keywords NVME
                        if any(kw in vol_label for kw in ["nvme", "nvm", "m.2", "pcie", "intel"]):
                            return "nvme"
                        # Se volume contiene keywords SSD
                        if any(kw in vol_label for kw in ["ssd", "samsung", "samsung 970"]):
                            return "ssd"
                except:
                    pass
                
                # Fallback veloce: assume SSD per FIXED drives
                # PowerShell lazy potrebbe refinarla a NVME se disponibile
                return "ssd"
        except:
            pass
        
        # Default: assume HDD se non riconosciuto
        return "hdd"
    
    def _detect_nvme_ssd_hdd_lazy(self, letter: str) -> str:
        """Rilevamento accurato BusType usando PowerShell 7
        Legge BusType + FriendlyName via Get-Disk - timeout LUNGO ma accettabile in background thread.
        Per RAID, controlla FriendlyName per distinguere NVME RAID da SSD RAID."""
        try:
            import subprocess
            
            # Nota: PowerShell 7 da Python ha overhead di startup significativo (~5-6s)
            # Poiché questo è in background thread, 10 secondi è accettabile
            
            # Query sia BusType che FriendlyName
            ps_cmd = (
                f"$disk = Get-Volume -DriveLetter {letter} -ErrorAction Stop | Get-Partition | Get-Disk; "
                f"@{{BusType=$disk.BusType; FriendlyName=$disk.FriendlyName}} | ConvertTo-Json"
            )
            
            result = subprocess.run(
                ["pwsh", "-NoProfile", "-Command", ps_cmd],
                capture_output=True,
                text=True,
                timeout=10.0,  # 10 secondi per timeout PowerShell
                creationflags=0x08000000
            )
            
            if result.returncode == 0 and result.stdout.strip():
                try:
                    import json
                    disk_info = json.loads(result.stdout.strip())
                    bus_type = disk_info.get('BusType', '').lower()
                    friendly_name = disk_info.get('FriendlyName', '').lower()
                except:
                    return None
                
                # Mappa BusType -> storage type
                if bus_type == 'nvme':
                    return 'nvme'
                elif bus_type == 'usb':
                    return 'usb'
                elif bus_type in ['ata', 'sata', 'atapi']:
                    return 'ssd'
                elif bus_type == 'scsi':
                    return 'ssd'
                elif bus_type == 'raid':
                    # Per RAID, controlla FriendlyName per sapere il tipo sottostante
                    # Se non contiene keyword SSD, assume NVME (perché Intel RAID su questo sistema è NVME)
                    if any(kw in friendly_name for kw in ['ssd', 'sata', 'seagate', 'western', 'wd', 'hitachi']):
                        return 'ssd'  # SSD RAID
                    else:
                        return 'nvme'  # Default RAID non-SSD -> NVME RAID
                elif bus_type == 'virtual':
                    return 'ram'
                else:
                    if 'raid' in bus_type:
                        return 'ssd'
                    return None
            
            return None
            
        except subprocess.TimeoutExpired:
            # Accetta timeout gracefully - prova di nuovo prossima volta
            return None
        except FileNotFoundError:
            return None
        except Exception as e:
            return None
    
    def _detect_raid_underlying_storage_lazy(self, letter: str) -> str:
        """Controlla il FriendlyName del disco RAID per distinguere NVME RAID da SSD RAID"""
        try:
            import subprocess
            
            ps_cmd = (
                f"Get-Volume -DriveLetter {letter} | Get-Partition | Get-Disk | "
                "Select-Object -ExpandProperty FriendlyName"
            )
            
            result = subprocess.run(
                ["powershell.exe", "-NoProfile", "-Command", ps_cmd],
                capture_output=True,
                text=True,
                timeout=5,  # Timeout LUNGO per RAID detection
                creationflags=0x08000000
            )
            
            if result.returncode == 0:
                friendly_name = result.stdout.strip().lower()
                
                # Controlla FriendlyName per keywords NVME
                if any(kw in friendly_name for kw in ['nvme', 'nvm', 'pcie', 'm.2', 'intel']):
                    return 'nvme'
                # Altrimenti assume SSD
                return 'ssd'
        except:
            pass
        
        # Fallback: assume SSD per RAID sconosciuto
        return 'ssd'
    
    def get_storage_type(self, path: str) -> str:
        """Ritorna il tipo di storage per un path (ram, ssd, hdd, nvme, usb, nas)
        Usa cache lazy per evitare PowerShell durante scan_all_drives()"""
        if not path:
            return "hdd"
        
        # Estrai lettera drive
        letter = os.path.splitdrive(path)[0].upper()
        if not letter or len(letter) < 1:
            return "hdd"
        
        letter = letter[0]
        
        # PRIMA: Controlla cache di classificazione accurata
        if letter in self._classification_cache:
            return self._classification_cache[letter]
        
        # SECONDA: Ottieni classificazione veloce (QueryDosDevice - senza PowerShell)
        drives = self.scan_all_drives()
        base_type = drives.get(letter, "hdd")
        
        # TERZA: Se è SSD/HDD generico, prova PowerShell lazy per accuratezza (NVME vs SSD)
        # Ma NON bloccante - se fallisce, usa il valore base
        if base_type in ["ssd", "hdd"]:
            try:
                accurate_type = self._detect_nvme_ssd_hdd_lazy(letter)
                if accurate_type:  # Solo se PowerShell ritorna un valore
                    self._classification_cache[letter] = accurate_type
                    return accurate_type
            except:
                pass
        
        # Salva nella cache il tipo base
        self._classification_cache[letter] = base_type
        return base_type

    def _extract_drive_letter(self, path: str) -> Optional[str]:
        try:
            drive = os.path.splitdrive(path)[0]
            if not drive:
                return None
            letter = drive[0].upper()
            if letter < 'A' or letter > 'Z':
                return None
            return letter
        except Exception:
            return None

    def _refresh_base_type_for_letter(self, letter: str) -> Optional[str]:
        """Aggiorna la cache veloce per una singola lettera usando QueryDosDevice."""
        try:
            letter = (letter or '').upper()[:1]
            if not letter or not os.path.exists(f"{letter}:\\"):
                return None

            import ctypes
            kernel32 = ctypes.windll.kernel32
            buffer = ctypes.create_unicode_buffer(1024)
            res = kernel32.QueryDosDeviceW(f"{letter}:", buffer, 1024)
            if res == 0:
                return None

            device_path = buffer.value.lower()
            storage_type = self._classify_storage_by_path(device_path, letter)
            self._all_drives_cache[letter] = storage_type
            return storage_type
        except Exception:
            return None

    def refresh_storage_type_for_letter(self, letter: str, force: bool = False) -> Optional[str]:
        """Forza (o assicura) un refresh accurato SOLO per un drive.

        - Se force=False e il drive è già nella cache accurata, non fa nulla.
        - Se manca o force=True: aggiorna base (QueryDosDevice) + prova detection accurata (PowerShell) e salva cache persistente.
        """
        try:
            letter = (letter or '').upper()[:1]
            if not letter:
                return None

            if (not force) and (letter in self._classification_cache):
                return self._classification_cache.get(letter)

            # Aggiorna cache veloce per quel drive (senza PowerShell)
            base_type = self._refresh_base_type_for_letter(letter)
            if not base_type:
                # Fallback: se non scansionato, prova a popolare la cache
                try:
                    self.scan_all_drives()
                except Exception:
                    pass
                base_type = self._all_drives_cache.get(letter, 'hdd')

            # Prova detection accurata (potenzialmente lenta) SOLO per questo drive
            accurate_type = None
            if base_type in ['ssd', 'hdd']:
                try:
                    accurate_type = self._detect_nvme_ssd_hdd_lazy(letter)
                except Exception:
                    accurate_type = None

            self._classification_cache[letter] = accurate_type or base_type

            try:
                self._save_persistent_cache()
            except Exception:
                pass

            return self._classification_cache.get(letter)
        except Exception:
            return None

    def refresh_storage_type(self, path: str, force: bool = False) -> Optional[str]:
        """Refresh accurato per il drive di un path."""
        letter = self._extract_drive_letter(path)
        if not letter:
            return None
        return self.refresh_storage_type_for_letter(letter, force=force)
