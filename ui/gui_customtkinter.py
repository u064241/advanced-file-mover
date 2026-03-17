import sys
import os
import json
import threading
import platform
import concurrent.futures
import subprocess
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext

# Drag and Drop support
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    HAS_DND = True
except ImportError:
    HAS_DND = False
    DND_FILES = None
    TkinterDnD = None

# CustomTkinter
import customtkinter as ctk

# Crea una classe wrapper CTk che supporta DnD
if HAS_DND:
    class CTkDnD(TkinterDnD.Tk):
        """CustomTkinter-compatible root con supporto DnD"""
        def __init__(self, *args, **kwargs):
            # Chiama il costruttore di TkinterDnD.Tk (NON di tk.Tk per evitare ricorsione)
            super().__init__(*args, **kwargs)
            # Applica lo stile CustomTkinter
            ctk.set_appearance_mode("system")
            ctk.set_default_color_theme("blue")
            # Applica gli attributi CTk essenziali per compatibilità
            self._appearance_mode = ctk.get_appearance_mode()
            
        def configure(self, **kwargs):
            """Override per compatibilità con CustomTkinter"""
            # Gestisci parametri CustomTkinter
            if 'fg_color' in kwargs:
                bg_color = kwargs.pop('fg_color')
                if isinstance(bg_color, (list, tuple)) and len(bg_color) == 2:
                    # Scegli colore in base al tema
                    bg_color = bg_color[0] if self._appearance_mode == "Light" else bg_color[1]
                kwargs['bg'] = bg_color
            return super().configure(**kwargs)
else:
    # Fallback: usa CTk normale se DnD non disponibile
    CTkDnD = ctk.CTk

# Aggiungi il parent directory al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.file_operations import FileOperationEngine
from src.ramdrive_handler import RamDriveManager
from src.utils import format_bytes, format_time, long_path, strip_long_path_prefix
from src.update_checker import check_for_update_async
from registry.context_menu import ContextMenuRegistrar

# Imposta l'aspetto di CustomTkinter
ctk.set_appearance_mode("system")  # "dark", "light" o "system"
ctk.set_default_color_theme("blue")  # "blue", "green", "dark-blue", etc.

# Funzioni helper per Windows admin drag and drop
try:
    import ctypes
    from ctypes import wintypes
    
    def is_admin():
        """Verifica se l'app è eseguita come amministratore"""
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False
    
    def enable_drag_drop_for_elevated():
        """Abilita drag and drop anche se l'app è eseguita come Administrator"""
        try:
            # Messaggi Windows necessari per drag and drop
            WM_DROPFILES = 0x0233
            WM_COPYDATA = 0x004A
            WM_COPYGLOBALDATA = 0x0049
            
            # Costante per permettere messaggi da privilegi inferiori
            MSGFLT_ADD = 1
            
            # Chiama ChangeWindowMessageFilter per ogni messaggio necessario
            ctypes.windll.user32.ChangeWindowMessageFilter(WM_DROPFILES, MSGFLT_ADD)
            ctypes.windll.user32.ChangeWindowMessageFilter(WM_COPYDATA, MSGFLT_ADD)
            ctypes.windll.user32.ChangeWindowMessageFilter(WM_COPYGLOBALDATA, MSGFLT_ADD)
            
            return True
        except Exception:
            return False
except:
    def is_admin():
        return False
    
    def enable_drag_drop_for_elevated():
        return False

# ── IPC per aggregazione file dal context menu ──────────────
# Approccio ibrido: file condiviso + Named Pipe per massima robustezza.
# 1. Le istanze secondarie scrivono i path in un file condiviso (temp)
# 2. L'istanza principale poll il file condiviso periodicamente via root.after()
# 3. Il Named Pipe è un canale aggiuntivo per latenza minima

import tempfile

_IPC_DIR = Path(tempfile.gettempdir()) / 'AdvancedFileMover_IPC'
_IPC_PENDING_FILE = _IPC_DIR / 'pending_files.txt'
_IPC_LOCK_FILE = _IPC_DIR / 'pending_files.lock'
PIPE_NAME = r'\\.\pipe\AdvancedFileMover_IPC'
_IPC_PIPE_THREAD = None

def _ipc_send_file(file_path: str, operation: str) -> bool:
    """Invia un file all'istanza principale scrivendo nel file condiviso.
    Tenta anche il Named Pipe per latenza minima."""
    if sys.platform != 'win32':
        return False
    
    sent = False
    
    # Metodo 1: File condiviso (sempre affidabile)
    try:
        _IPC_DIR.mkdir(parents=True, exist_ok=True)
        msg = f"{operation}|{file_path}\n"
        # Usa 'a' (append) - thread-safe su Windows per writes < 4KB
        with open(_IPC_PENDING_FILE, 'a', encoding='utf-8') as f:
            f.write(msg)
        sent = True
    except Exception:
        pass
    
    # Metodo 2: Named Pipe (per latenza minima se il listener è pronto)
    try:
        import ctypes
        from ctypes import wintypes
        kernel32 = ctypes.windll.kernel32
        GENERIC_WRITE = 0x40000000
        OPEN_EXISTING = 3
        INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value
        
        # Retry con delay breve per dare tempo al pipe listener di partire
        for attempt in range(5):
            handle = kernel32.CreateFileW(
                PIPE_NAME, GENERIC_WRITE, 0, None,
                OPEN_EXISTING, 0, None
            )
            if handle != INVALID_HANDLE_VALUE:
                msg = f"{operation}|{file_path}\n".encode('utf-8')
                written = wintypes.DWORD(0)
                kernel32.WriteFile(handle, msg, len(msg), ctypes.byref(written), None)
                kernel32.CloseHandle(handle)
                sent = True
                break
            import time; time.sleep(0.3)
    except Exception:
        pass
    
    return sent

def _ipc_start_listener(app_instance):
    """Avvia il listener IPC:
    - Named Pipe in thread background (per latenza minima)
    - Polling file condiviso via root.after() (affidabile)"""
    if sys.platform != 'win32':
        return
    
    # === Named Pipe listener (background thread) ===
    def _pipe_listener():
        import ctypes
        from ctypes import wintypes
        kernel32 = ctypes.windll.kernel32
        
        PIPE_ACCESS_INBOUND = 0x00000001
        PIPE_TYPE_BYTE = 0x00000000
        PIPE_READMODE_BYTE = 0x00000000
        PIPE_WAIT = 0x00000000
        PIPE_UNLIMITED_INSTANCES = 255
        INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value
        BUFFER_SIZE = 4096
        
        while True:
            try:
                handle = kernel32.CreateNamedPipeW(
                    PIPE_NAME,
                    PIPE_ACCESS_INBOUND,
                    PIPE_TYPE_BYTE | PIPE_READMODE_BYTE | PIPE_WAIT,
                    PIPE_UNLIMITED_INSTANCES,
                    BUFFER_SIZE, BUFFER_SIZE,
                    0, None
                )
                if handle == INVALID_HANDLE_VALUE:
                    import time; time.sleep(0.5)
                    continue
                
                connected = kernel32.ConnectNamedPipe(handle, None)
                if connected or kernel32.GetLastError() == 535:
                    buf = ctypes.create_string_buffer(BUFFER_SIZE)
                    read = wintypes.DWORD(0)
                    total_data = b''
                    while True:
                        success = kernel32.ReadFile(handle, buf, BUFFER_SIZE, ctypes.byref(read), None)
                        if read.value > 0:
                            total_data += buf.raw[:read.value]
                        if not success or read.value < BUFFER_SIZE:
                            break
                    
                    kernel32.DisconnectNamedPipe(handle)
                    kernel32.CloseHandle(handle)
                    
                    if total_data:
                        _process_ipc_messages(total_data.decode('utf-8', errors='replace').strip(), app_instance)
                else:
                    kernel32.CloseHandle(handle)
            except Exception:
                import time; time.sleep(0.5)
    
    global _IPC_PIPE_THREAD
    _IPC_PIPE_THREAD = threading.Thread(target=_pipe_listener, daemon=True)
    _IPC_PIPE_THREAD.start()
    
    # === File condiviso polling (via Tk event loop) ===
    def _poll_pending_files():
        try:
            if _IPC_PENDING_FILE.exists() and _IPC_PENDING_FILE.stat().st_size > 0:
                # Rename atomico: i nuovi writer troveranno il file mancante e ne creeranno uno nuovo.
                # Questo evita la race condition lettura/svuotamento.
                tmp_path = _IPC_PENDING_FILE.with_suffix('.tmp_read')
                try:
                    _IPC_PENDING_FILE.rename(tmp_path)
                    with open(tmp_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    try:
                        tmp_path.unlink()
                    except Exception:
                        pass
                    if content.strip():
                        _process_ipc_messages(content.strip(), app_instance)
                except Exception:
                    # Se rename fallisce, prova lettura classica (fallback)
                    try:
                        with open(_IPC_PENDING_FILE, 'r', encoding='utf-8') as f:
                            content = f.read()
                        with open(_IPC_PENDING_FILE, 'w', encoding='utf-8') as f:
                            f.write('')
                        if content.strip():
                            _process_ipc_messages(content.strip(), app_instance)
                    except Exception:
                        pass
        except Exception:
            pass
        
        # Ripeti ogni 500ms
        try:
            if app_instance and hasattr(app_instance, 'root'):
                app_instance.root.after(500, _poll_pending_files)
        except Exception:
            pass
    
    # Avvia il primo poll dopo 300ms
    try:
        if app_instance and hasattr(app_instance, 'root'):
            app_instance.root.after(300, _poll_pending_files)
    except Exception:
        pass

def _process_ipc_messages(text: str, app_instance):
    """Processa messaggi IPC ricevuti (da pipe o file condiviso)."""
    if not text or not app_instance:
        return
    
    paths_to_add = []
    for line in text.split('\n'):
        line = line.strip()
        if '|' in line:
            op, path = line.split('|', 1)
            path = path.strip().strip('"')
            if path:
                paths_to_add.append(path)
    
    if paths_to_add and hasattr(app_instance, 'root'):
        app_instance.root.after(0, lambda ps=list(paths_to_add): app_instance._add_source_paths(ps))

# ConfigManager per salvare/caricare configurazione
class ConfigManager:
    def __init__(self, config_path='config.json'):
        # Nota: il parametro config_path è mantenuto per retrocompatibilità.
        # Da ora la configurazione utente vive in %LOCALAPPDATA%\AdvancedFileMover\config.json
        self.app_data_dir = self._get_app_data_dir()
        self.config_path = self.app_data_dir / 'config.json'
        self.config = self.load_config()

    @staticmethod
    def _get_app_data_dir() -> Path:
        try:
            base = Path(os.environ.get('LOCALAPPDATA', str(Path.home() / 'AppData' / 'Local')))
        except Exception:
            base = Path.home() / 'AppData' / 'Local'
        return base / 'AdvancedFileMover'

    @staticmethod
    def _get_bundled_config_path() -> Path:
        """Percorso del config.json "bundled" (vicino all'exe o al progetto).

        Serve solo come template per il primo avvio, non come config scrivibile.
        """
        try:
            if getattr(sys, 'frozen', False):
                app_root = Path(sys.executable).parent
            else:
                app_root = Path(__file__).parent.parent
            return app_root / 'config.json'
        except Exception:
            return Path('config.json')
    
    def load_config(self):
        """Carica la configurazione da JSON"""
        default = self.get_default_config()

        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)

                # Merge con default config per assicurare che tutti i campi siano presenti
                merged_config = {**default, **user_config}

                # Sync version from bundled config (auto-update version field)
                try:
                    bundled_config_path = self._get_bundled_config_path()
                    if bundled_config_path.exists():
                        with open(bundled_config_path, 'r', encoding='utf-8') as f:
                            bundled_config = json.load(f)
                        
                        bundled_version = bundled_config.get('version', '1.0.0')
                        user_version = merged_config.get('version', '0.0.0')
                        
                        # If bundled version is different, update it
                        if bundled_version != user_version:
                            merged_config['version'] = bundled_version
                            # Save immediately to persist version update
                            self.config = merged_config
                            self.save_config()
                except Exception:
                    # Silently fail version sync if bundled config is not available
                    pass
                
                return merged_config
            except:
                return default

        # Primo avvio: prova a migrare da config "bundled" (vicino all'exe/progetto)
        try:
            src = self._get_bundled_config_path()
            if src.exists():
                try:
                    self.config_path.parent.mkdir(parents=True, exist_ok=True)
                except Exception:
                    pass

                try:
                    with open(src, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    if isinstance(data, dict):
                        self.config = data
                        self.save_config()
                        return data
                except Exception:
                    pass
        except Exception:
            pass

        # Se non c'è un template, crea config default in AppData\Local\AdvancedFileMover
        try:
            data = self.get_default_config()
            self.config = data
            self.save_config()
            return data
        except Exception:
            return self.get_default_config()
    
    def save_config(self):
        """Salva la configurazione su JSON"""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
                f.flush()  # Forza scrittura immediata su disco
        except Exception as e:
            print(f"Errore nel salvataggio della configurazione: {e}")
    
    def get_default_config(self):
        """Ritorna la configurazione di default"""
        return {
            'language': 'it',
            'auto_elevate_on_start': False,
            'theme': 'dark',
            'always_on_top': False,
            'window_position': {'x': 100, 'y': 100},
            'window_size': {'width': 602, 'height': 584},
            'buffer_size': 100,
            'threads': 4,
            'ramdrive': False,
            'overwrite': False
        }
    
    def get(self, key, default=None):
        return self.config.get(key, default)
    
    def set(self, key, value):
        self.config[key] = value
        self.save_config()


class AdvancedFileMoverCustomTkinter:
    def __init__(
        self,
        root,
        source_path=None,
        operation_type=None,
        initial_sources=None,
        launched_from_context_menu=False,
    ):
        self.root = root
        
        # Flag per bloccare il resize automatico durante l'inizializzazione
        self._lock_window_size = False
        
        # Carica configurazione
        self.config_manager = ConfigManager()

        # Lingua UI (i18n) — usa lingua salvata, oppure rileva dal sistema
        _saved_lang = str(self.config_manager.get('language', '') or '').lower()
        if _saved_lang in ('it', 'en', 'fr', 'de', 'es'):
            self.language_code = _saved_lang
        else:
            self.language_code = _detect_system_language()
        self._translations = {}
        self._i18n_widgets = []
        self._tab_titles = {}
        try:
            self._translations = self._load_translations(self.language_code)
        except Exception:
            self._translations = {}

        # Titolo finestra
        try:
            self.root.title(self._t('app_title', 'Advanced File Mover Pro'))
        except Exception:
            self.root.title('Advanced File Mover Pro')

        # Elevazione
        self.auto_elevate_on_start = tk.BooleanVar(value=bool(self.config_manager.get('auto_elevate_on_start', False)))
        
        # Variabili dell'applicazione
        self.source_paths = []
        self.dest_path = tk.StringVar()
        # Aggiungi trace per auto-tuning e refresh Info quando dest_path cambia
        self._info_update_after_id = None
        self.dest_path.trace_add('write', lambda *args: self._on_destination_changed())

        # Refresh accurato storage (solo drive coinvolti) - debounced
        self._accurate_refresh_after_id = None
        self._pending_accurate_refresh_letters = set()
        self.operation_thread = None
        self.cancel_requested = False
        self.operation_in_progress = False  # Flag per controllare se operazione è in corso

        self._menu_status_restore_after_id = None
        self._auto_close_after_id = None

        # Limite globale: max N chiamate "accurate" (PowerShell) in parallelo
        # Evita raffiche di processi pwsh/powershell quando ci sono molti drive.
        self._accurate_detection_semaphore = threading.Semaphore(2)

        self.launched_from_context_menu = bool(launched_from_context_menu)
        self.context_operation_type = operation_type if operation_type in ('copy', 'move') else None
        
        # Checkbox variables
        self.ramdrive_enabled = tk.BooleanVar(value=self.config_manager.get('ramdrive', False))
        # Preferenza utente reale: conservata quando il checkbox viene disabilitato a forza
        # (es. sorgente/destinazione coincide con il RamDrive). None = nessun override attivo.
        self._ramdrive_user_pref: bool | None = None
        self.overwrite_enabled = tk.BooleanVar(value=self.config_manager.get('overwrite', False))
        self.delete_source_enabled = tk.BooleanVar(value=self.config_manager.get('delete_source', False))
        self.always_on_top_var = tk.BooleanVar(value=self.config_manager.get('always_on_top', False))
        
        # Buffer e Thread - HARDCODED (non legge da config, non salva)
        # Verranno aggiornati automaticamente in base ai drive selezionati
        self.buffer_size = tk.StringVar(value='100')  # Default: 100MB (hardcoded)
        self.threads = tk.StringVar(value='4')  # Default: 4 thread (hardcoded)
        
        # Tema - Carica e applica SUBITO prima di creare i widget
        self.current_theme = self.config_manager.get('theme', 'dark')
        ctk.set_appearance_mode(self.current_theme)
        
        # Managers
        self.ramdrive_manager = RamDriveManager()
        
        self.file_engine = FileOperationEngine(
            buffer_size=int(self.buffer_size.get()) * 1024 * 1024,  # Converti MB a bytes
            num_threads=int(self.threads.get()),
            overwrite=self.overwrite_enabled.get()
        )

        # Drag and Drop (il monkey-patch è già applicato negli import)
        self.dnd_enabled = HAS_DND
        
        # Callback progress: aggiorna UI direttamente dal motore (thread-safe via root.after)
        try:
            self.file_engine.set_progress_callback(self._on_engine_progress)
        except Exception:
            pass

        # Callback error: salva ultimo errore per mostrarlo in UI
        try:
            self.file_engine.set_error_callback(self._on_engine_error)
        except Exception:
            pass

        # Callback conflict: richiede decisione utente quando overwrite=False e file esiste
        try:
            self.file_engine.on_conflict = self._ask_overwrite_conflict
        except Exception:
            pass
        
        # Context menu (passa le etichette tradotte nella lingua corrente)
        self.context_manager = ContextMenuRegistrar(
            copy_label=self._t('ctx_copy_label', 'Copia [Avanzata]'),
            move_label=self._t('ctx_move_label', 'Sposta [Avanzata]')
        )

        # UI - Crea l'interfaccia PRIMA della detection (non bloccare UI)
        self.create_widgets()
        
        # Start async update check after UI is created
        self._start_update_check()
        
        # Early detection thread: scansiona tutti i drive in background per accuratezza massima
        def early_storage_detection():
            try:
                self.ramdrive_manager.detect_ramdrive()
                self.ramdrive_manager.scan_all_drives()  # Popola cache veloce con QueryDosDevice
                
                # Carica cache persistente per evitare detection ripetuta
                cached_types = self.ramdrive_manager._classification_cache.copy()
                
                # Determina quali drive richiedono detection (quelli non in cache)
                drives_to_detect = []
                for letter in self.ramdrive_manager._all_drives_cache.keys():
                    if letter not in cached_types:
                        drives_to_detect.append(letter)
                
                # Se tutti i drive sono in cache, skip PowerShell
                if not drives_to_detect:
                    try:
                        self.status_label.configure(text=self._t('status_ready_cache', "Pronto (cache)"))
                    except:
                        pass
                    return
                
                # Rilevamento parallelo per drive non in cache
                def detect_one_drive(letter):
                    try:
                        # Se già in cache (caricato prima), salta
                        if letter in self.ramdrive_manager._classification_cache:
                            return None

                        # Limita concorrenza PowerShell (max 2 processi) anche in early detection
                        try:
                            self._accurate_detection_semaphore.acquire()
                            refined = self.ramdrive_manager._detect_nvme_ssd_hdd_lazy(letter)
                        finally:
                            try:
                                self._accurate_detection_semaphore.release()
                            except Exception:
                                pass
                        if refined:
                            self.ramdrive_manager._classification_cache[letter] = refined
                            return (letter, refined)
                        else:
                            # PowerShell fallito o disco non supportato -> usa classificazione veloce
                            base_type = self.ramdrive_manager._all_drives_cache.get(letter, "hdd")
                            self.ramdrive_manager._classification_cache[letter] = base_type
                            return None  # Non mostrare notifica se è fallback
                    except:
                        pass
                    return None
                
                # Esegui detection parallelo ma limitato (max 2 in parallelo)
                with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                    futures = {executor.submit(detect_one_drive, letter): letter for letter in drives_to_detect}
                    
                    for future in concurrent.futures.as_completed(futures):
                        result = future.result()
                        if result:
                            letter, storage_type = result
                            try:
                                self.status_label.configure(text=self._t('status_detected_drive', 'Rilevato {letter}: {type}').format(letter=letter, type=storage_type.upper()))
                            except:
                                pass
                
                # Salva cache al completamento
                self.ramdrive_manager._save_persistent_cache()
                
                # Status finale
                try:
                    self.status_label.configure(text=self._t('status_ready', 'Pronto'))
                except:
                    pass
            except Exception as e:
                print(f"Early detection error: {e}")
        
        detection_thread = threading.Thread(target=early_storage_detection, daemon=True)
        detection_thread.start()

        # Inizializza sorgenti (manuale vs menu contestuale)
        sources_to_add = []
        if initial_sources:
            sources_to_add.extend(list(initial_sources))
        if source_path:
            sources_to_add.append(source_path)
        if sources_to_add:
            self._add_source_paths(sources_to_add)
        
        # Carica stato window
        self.restore_window_state()
        
        # Centra finestra dopo che tutto è caricato
        self.root.after(100, self._center_window)
        
        # Imposta dimensioni finali e blocca il resize
        def finalize_window():
            if hasattr(self, '_desired_width') and hasattr(self, '_desired_height'):
                # Imposta le dimensioni definitive
                self.root.geometry(f"{self._desired_width}x{self._desired_height}+{self.root.winfo_x()}+{self.root.winfo_y()}")
            # Blocca il resize (rimuove il pulsante di massimizzazione dalla barra titolo)
            self.root.resizable(False, False)
            self._lock_window_size = False
        
        self.root.after(200, finalize_window)

        # Registra listener WM_DEVICECHANGE per rilevare inserimento/rimozione periferiche
        self.root.after(300, self._setup_device_change_listener)
    
    
        # Auto-tuning buffer e thread in base alla destination storage
        self._auto_tune_parameters()

        # Se avvio da menu contestuale: chiede subito la destinazione
        if self.launched_from_context_menu and self.source_paths:
            self.root.after(250, self._context_menu_pick_destination)
        
        # Salva stato al chiusura
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _setup_device_change_listener(self):
        """Rileva inserimento/rimozione periferiche (USB, ecc.) tramite polling
        delle lettere drive disponibili e aggiorna automaticamente il tab Informazioni."""
        try:
            # Snapshot iniziale dei drive presenti
            self._known_drives = self._get_drive_letters()
        except Exception:
            self._known_drives = set()

        def _check_drives():
            try:
                current = self._get_drive_letters()
                if current != self._known_drives:
                    self._known_drives = current
                    # Invalida la cache storage così il re-scan rileva i nuovi drive
                    try:
                        self.ramdrive_manager._drives_scanned = False
                        self.ramdrive_manager._all_drives_cache.clear()
                        # Rimuovi dalla classification_cache le lettere non più presenti
                        for letter in list(self.ramdrive_manager._classification_cache.keys()):
                            if letter not in current:
                                del self.ramdrive_manager._classification_cache[letter]
                    except Exception:
                        pass
                    try:
                        self.update_info()
                    except Exception:
                        pass
            except Exception:
                pass
            # Controlla ogni 3 secondi (leggero, nessun impatto su CPU)
            try:
                self.root.after(3000, _check_drives)
            except Exception:
                pass

        self.root.after(3000, _check_drives)

    @staticmethod
    def _get_drive_letters() -> set:
        """Restituisce il set delle lettere drive attualmente montate."""
        drives = set()
        try:
            bitmask = ctypes.windll.kernel32.GetLogicalDrives()
            for i in range(26):
                if bitmask & (1 << i):
                    drives.add(chr(ord('A') + i))
        except Exception:
            pass
        return drives

    def _i18n_register(self, widget, key: str, default: str):
        """Registra un widget a cui applicare le traduzioni dinamiche."""
        try:
            if not hasattr(self, '_i18n_widgets'):
                self._i18n_widgets = []
            self._i18n_widgets.append((widget, key, default))
        except Exception:
            pass

    def apply_language(self, language_code: str):
        """Applica la lingua subito a tutta la GUI (testi statici)."""
        try:
            code = str(language_code or 'it').strip().lower()
            if code not in ('it', 'en', 'fr', 'de', 'es'):
                code = 'it'
            self.language_code = code
            try:
                self.config_manager.set('language', code)
            except Exception:
                pass

            try:
                self._translations = self._load_translations(code)
            except Exception:
                self._translations = {}

            # Titolo finestra
            try:
                self.root.title(self._t('app_title', 'Advanced File Mover Pro'))
            except Exception:
                pass

            # Tab titles (se possibile)
            try:
                desired = {
                    'main': self._t('tab_main', '📋 Principale'),
                    'info': self._t('tab_info', 'ℹ️ Informazioni'),
                    'menu': self._t('tab_menu', '🖱️ Menu Contestuale'),
                    'view': self._t('tab_view', '👁️ Visualizzazione'),
                }

                for k, new_title in desired.items():
                    old_title = (self._tab_titles or {}).get(k)
                    if not old_title or old_title == new_title:
                        self._tab_titles[k] = new_title
                        continue

                    renamed = False
                    try:
                        if hasattr(self, 'notebook') and hasattr(self.notebook, 'rename'):
                            self.notebook.rename(old_title, new_title)
                            # Bug CTkTabview: rename() non aggiorna _current_name
                            if getattr(self.notebook, '_current_name', None) == old_title:
                                self.notebook._current_name = new_title
                            renamed = True
                    except Exception:
                        renamed = False

                    if not renamed:
                        # Fallback: aggiorna testo bottone + chiave interna _tab_dict
                        try:
                            sb = getattr(self.notebook, '_segmented_button', None)
                            buttons = getattr(sb, '_buttons_dict', None)
                            if isinstance(buttons, dict) and old_title in buttons:
                                btn_widget = buttons.pop(old_title)
                                # Aggiorna testo e lambda command del bottone
                                btn_widget.configure(
                                    text=new_title,
                                    command=lambda v=new_title: sb.set(v, from_button_callback=True),
                                )
                                buttons[new_title] = btn_widget
                                # Aggiorna _tab_dict (chiave interna di CTkTabview)
                                tab_dict = getattr(self.notebook, '_tab_dict', None)
                                if isinstance(tab_dict, dict) and old_title in tab_dict:
                                    tab_dict[new_title] = tab_dict.pop(old_title)
                                # Aggiorna _name_list se presente
                                name_list = getattr(self.notebook, '_name_list', None)
                                if isinstance(name_list, list):
                                    for i, name in enumerate(name_list):
                                        if name == old_title:
                                            name_list[i] = new_title
                                            break
                                # Aggiorna _current_name se è il tab attivo
                                if getattr(self.notebook, '_current_name', None) == old_title:
                                    self.notebook._current_name = new_title
                                # Aggiorna valori del segmented button
                                if sb is not None and hasattr(sb, '_value_list'):
                                    for i, v in enumerate(sb._value_list):
                                        if v == old_title:
                                            sb._value_list[i] = new_title
                                            break
                                    if getattr(sb, '_current_value', None) == old_title:
                                        sb._current_value = new_title
                                renamed = True
                        except Exception:
                            pass

                    if renamed:
                        self._tab_titles[k] = new_title
            except Exception:
                pass

            # Widget registrati
            for (w, key, default) in list(getattr(self, '_i18n_widgets', []) or []):
                try:
                    if w is None:
                        continue
                    w.configure(text=self._t(key, default))
                except Exception:
                    pass

            # Testi dipendenti dallo stato
            try:
                if hasattr(self, 'theme_btn') and self.theme_btn is not None:
                    self.theme_btn.configure(
                        text=self._t('theme_dark_current', '🌙 Tema Scuro (Corrente)')
                        if self.current_theme == 'dark'
                        else self._t('theme_light_current', '☀️ Tema Chiaro (Corrente)')
                    )
            except Exception:
                pass

            # Progress placeholder (se presente)
            try:
                if hasattr(self, 'progress_label') and self.progress_label is not None:
                    current_text = ''
                    try:
                        current_text = str(self.progress_label.cget('text') or '')
                    except Exception:
                        current_text = ''

                    if current_text and ('0%' in current_text) and ('MB/s' in current_text) and ('ETA' in current_text or 'T:' in current_text):
                        placeholder = self._t('progress_placeholder', "Pronto|0%|--- MB/s|ETA:--:--")
                        self._set_progress_text(placeholder.replace('|', ' | '))
            except Exception:
                pass

            # Flag lingua corrente (se presente)
            try:
                self._load_flag_images()
                if hasattr(self, 'lang_flag_label') and self.lang_flag_label is not None:
                    img = (getattr(self, '_flag_images', None) or {}).get(self.language_code)
                    if img is not None:
                        self.lang_flag_label.configure(image=img)
            except Exception:
                pass

            # Aggiorna info tab se esiste, così anche i titoli testuali si aggiornano
            try:
                if hasattr(self, 'info_text'):
                    self.update_info()
            except Exception:
                pass

            # Aggiorna le etichette del menu contestuale per la nuova lingua
            try:
                self.context_manager = ContextMenuRegistrar(
                    copy_label=self._t('ctx_copy_label', 'Copia [Avanzata]'),
                    move_label=self._t('ctx_move_label', 'Sposta [Avanzata]')
                )
                # Se il menu è già registrato, ri-registra automaticamente con le nuove etichette
                if self.context_manager.is_registered():
                    self.context_manager.register()
            except Exception:
                pass
        except Exception:
            pass

    def _get_i18n_base_dir(self) -> Path:
        """Ritorna la cartella base in cui cercare i file i18n."""
        try:
            if getattr(sys, 'frozen', False):
                return Path(sys.executable).parent
            return Path(__file__).parent.parent
        except Exception:
            return Path.cwd()

    def _get_flags_dir(self) -> Path:
        """Ritorna la cartella contenente le bandiere PNG."""
        try:
            base_dir = self._get_i18n_base_dir()
        except Exception:
            base_dir = Path.cwd()

        try:
            meipass = Path(getattr(sys, '_MEIPASS')) if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS') else None
        except Exception:
            meipass = None

        candidates = [
            base_dir / 'assets' / 'flags',
            base_dir / 'src' / 'assets' / 'flags',
            Path(__file__).parent.parent / 'src' / 'assets' / 'flags',
        ]

        if meipass is not None:
            candidates.insert(0, meipass / 'assets' / 'flags')

        for p in candidates:
            try:
                if p.exists():
                    return p
            except Exception:
                continue

        return candidates[-1]

    def _load_flag_images(self):
        """Carica le immagini bandiere e mantiene i riferimenti.

        Preferisce CTkImage (Pillow) per supporto HiDPI; fallback a tk.PhotoImage.
        """
        try:
            if hasattr(self, '_flag_images') and isinstance(self._flag_images, dict) and self._flag_images:
                return
        except Exception:
            pass

        self._flag_images = {}

        # Se disponibile, usa Pillow + CTkImage per scaling corretto su HighDPI
        pil_available = False
        try:
            from PIL import Image
            pil_available = True
        except ImportError:
            # PIL not available, will use fallback
            pil_available = False

        if pil_available:
            try:
                flags_dir = self._get_flags_dir()
                for code in ('it', 'en', 'fr', 'de', 'es'):
                    p = flags_dir / f'{code}.png'
                    try:
                        if not p.exists():
                            continue
                    except Exception:
                        continue

                    try:
                        from PIL import Image
                        im = Image.open(p)
                        try:
                            im = im.convert('RGBA')
                        except Exception:
                            pass

                        # Dimensione target (piccola, leggibile in UI)
                        size = (28, 18)
                        try:
                            im2 = im.resize(size, Image.Resampling.LANCZOS)
                        except Exception:
                            im2 = im.resize(size)

                        self._flag_images[code] = ctk.CTkImage(light_image=im2, dark_image=im2, size=size)
                    except Exception:
                        continue

                return
            except Exception:
                pass

        # Fallback: tk.PhotoImage (no PIL required)
        try:
            flags_dir = self._get_flags_dir()
            for code in ('it', 'en', 'fr', 'de', 'es'):
                p = flags_dir / f'{code}.png'
                try:
                    if not p.exists():
                        continue
                except Exception:
                    continue

                try:
                    img = tk.PhotoImage(file=str(p))
                    try:
                        while img.width() > 28:
                            img = img.subsample(2, 2)
                    except Exception:
                        pass
                    self._flag_images[code] = img
                except Exception:
                    continue
        except Exception:
            pass

    def _op_name(self, operation_type: str) -> str:
        op = str(operation_type or '').lower()
        if op == 'copy':
            return self._t('op_copy', 'Copia')
        if op == 'move':
            return self._t('op_move', 'Sposta')
        return str(operation_type or '')

    def _op_name_upper(self, operation_type: str) -> str:
        op = str(operation_type or '').lower()
        if op == 'copy':
            return self._t('op_copy_upper', 'COPIA')
        if op == 'move':
            return self._t('op_move_upper', 'SPOSTA')
        try:
            return str(self._op_name(operation_type)).upper()
        except Exception:
            return str(operation_type or '').upper()

    def _load_translations(self, language_code: str) -> dict:
        """Carica il dizionario traduzioni da i18n/<lang>.json."""
        try:
            code = str(language_code or 'it').strip().lower()
            if code not in ('it', 'en', 'fr', 'de', 'es'):
                code = 'it'

            base_dir = self._get_i18n_base_dir()
            candidates = []

            # 1) In bundle onefile (sys._MEIPASS)
            try:
                if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
                    candidates.append(Path(getattr(sys, '_MEIPASS')) / 'i18n' / f'{code}.json')
            except Exception:
                pass

            # 2) Vicino all'EXE (installazione / dist)
            candidates.append(base_dir / 'i18n' / f'{code}.json')

            # 3) Dev (repo)
            candidates.append(Path(__file__).parent.parent / 'i18n' / f'{code}.json')

            for p in candidates:
                try:
                    if p.exists():
                        with open(p, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        return data if isinstance(data, dict) else {}
                except Exception:
                    continue
        except Exception:
            pass
        return {}

    def _t(self, key: str, default: str = "") -> str:
        """Ritorna la traduzione per una key, con fallback."""
        try:
            if isinstance(self._translations, dict) and key in self._translations:
                v = self._translations.get(key)
                if isinstance(v, str) and v:
                    return v
        except Exception:
            pass
        return default if isinstance(default, str) else str(default)

    def _restart_as_admin(self):
        """Rilancia l'app con privilegi amministrativi (UAC)."""
        try:
            if sys.platform != 'win32':
                return
            if _is_running_as_admin():
                try:
                    messagebox.showinfo(self._t('elevation_section', 'Privilegi'), self._t('already_admin', 'Sei già amministratore.'))
                except Exception:
                    pass
                return

            argv = list(sys.argv or [])
            if '--no-auto-elevate' not in argv:
                argv.append('--no-auto-elevate')

            ok = bool(_relaunch_elevated(argv))
            if ok:
                try:
                    self.root.destroy()
                except Exception:
                    pass
        except Exception:
            pass

    def _update_ramdrive_option_state(self):
        """Disabilita 'Usa RamDrive' se la sorgente o la destinazione coincidono con il RamDrive."""
        try:
            try:
                has_ramdrive = bool(self.ramdrive_manager.detect_ramdrive())
            except Exception:
                has_ramdrive = False

            if not has_ramdrive:
                # Nessun RamDrive presente: ripristina preferenza utente e abilita
                try:
                    if self._ramdrive_user_pref is not None:
                        self.ramdrive_enabled.set(self._ramdrive_user_pref)
                        self._ramdrive_user_pref = None
                except Exception:
                    pass
                try:
                    if hasattr(self, 'ramdrive_checkbox'):
                        self.ramdrive_checkbox.configure(state='normal')
                except Exception:
                    pass
                return

            # Verifica sorgenti
            path_on_ram = False
            for src in list(self.source_paths or []):
                try:
                    if self.ramdrive_manager.get_storage_type(src) == 'ram':
                        path_on_ram = True
                        break
                except Exception:
                    continue

            # Verifica destinazione (se sorgenti ok)
            if not path_on_ram:
                try:
                    dest = self.dest_path.get()
                    if dest and self.ramdrive_manager.get_storage_type(dest) == 'ram':
                        path_on_ram = True
                except Exception:
                    pass

            if path_on_ram:
                # Salva preferenza reale solo la prima volta (evita di sovrascrivere con False)
                try:
                    if self._ramdrive_user_pref is None:
                        self._ramdrive_user_pref = self.ramdrive_enabled.get()
                    self.ramdrive_enabled.set(False)
                except Exception:
                    pass
                try:
                    if hasattr(self, 'ramdrive_checkbox'):
                        self.ramdrive_checkbox.configure(state='disabled')
                except Exception:
                    pass
            else:
                # Sorgente e destinazione non sul RamDrive: ripristina preferenza utente
                try:
                    if self._ramdrive_user_pref is not None:
                        self.ramdrive_enabled.set(self._ramdrive_user_pref)
                        self._ramdrive_user_pref = None
                except Exception:
                    pass
                try:
                    if hasattr(self, 'ramdrive_checkbox'):
                        self.ramdrive_checkbox.configure(state='normal')
                except Exception:
                    pass
        except Exception:
            pass

    def _on_destination_changed(self):
        try:
            self._auto_tune_parameters()
        except Exception:
            pass

        # Forza refresh accurato SOLO del drive di destinazione (debounced + background)
        try:
            self._queue_accurate_refresh_for_path(self.dest_path.get())
            self._schedule_accurate_storage_refresh()
        except Exception:
            pass

        # Se la destinazione è sul RamDrive, disabilita l'opzione "Usa RamDrive"
        try:
            self._update_ramdrive_option_state()
        except Exception:
            pass

        # Aggiorna automaticamente il tab Informazioni (debounced)
        self._schedule_info_update()

    def _on_sources_changed(self):
        # Auto-profilazione se abbiamo sia sorgente che destinazione
        try:
            self._auto_profile_parameters()
        except Exception:
            pass

        # Aggiorna automaticamente il tab Informazioni (debounced)
        self._schedule_info_update()

        # Forza refresh accurato SOLO dei drive sorgenti (e destinazione se presente)
        try:
            for src in list(self.source_paths or []):
                self._queue_accurate_refresh_for_path(src)
            if self.dest_path.get():
                self._queue_accurate_refresh_for_path(self.dest_path.get())
            self._schedule_accurate_storage_refresh()
        except Exception:
            pass

        # Se la sorgente è sul RamDrive, disabilita l'opzione "Usa RamDrive"
        try:
            self._update_ramdrive_option_state()
        except Exception:
            pass

    def _queue_accurate_refresh_for_path(self, path: str):
        try:
            if not path:
                return
            drive = os.path.splitdrive(str(path))[0]
            if not drive:
                return
            letter = drive[0].upper()
            if letter < 'A' or letter > 'Z':
                return
            self._pending_accurate_refresh_letters.add(letter)
        except Exception:
            pass

    def _schedule_accurate_storage_refresh(self, delay_ms: int = 650):
        try:
            if self._accurate_refresh_after_id is not None:
                self.root.after_cancel(self._accurate_refresh_after_id)
        except Exception:
            pass

        try:
            self._accurate_refresh_after_id = self.root.after(delay_ms, self._run_accurate_storage_refresh_background)
        except Exception:
            self._accurate_refresh_after_id = None

    def _run_accurate_storage_refresh_background(self):
        try:
            self._accurate_refresh_after_id = None
        except Exception:
            pass

        try:
            letters = sorted(self._pending_accurate_refresh_letters)
            self._pending_accurate_refresh_letters.clear()
        except Exception:
            letters = []

        if not letters:
            return

        def worker(selected_letters):
            try:
                for letter in selected_letters:
                    try:
                        # Assicura detection accurata SOLO per questi drive (limita concorrenza PowerShell)
                        try:
                            self._accurate_detection_semaphore.acquire()
                            self.ramdrive_manager.refresh_storage_type_for_letter(letter, force=False)
                        finally:
                            try:
                                self._accurate_detection_semaphore.release()
                            except Exception:
                                pass
                    except Exception:
                        pass
            finally:
                def _apply():
                    # Ri-applica tuning/profilo ora che la classificazione è (probabilmente) più accurata
                    try:
                        self._auto_tune_parameters()
                    except Exception:
                        pass
                    try:
                        self._auto_profile_parameters()
                    except Exception:
                        pass
                    self._schedule_info_update(delay_ms=0)

                try:
                    self.root.after(0, _apply)
                except Exception:
                    pass

        try:
            threading.Thread(target=worker, args=(letters,), daemon=True).start()
        except Exception:
            pass

    def _schedule_info_update(self, delay_ms: int = 300):
        # Se il tab Informazioni non è stato ancora creato, non fare nulla
        if not hasattr(self, 'info_text'):
            return

        try:
            if self._info_update_after_id is not None:
                self.root.after_cancel(self._info_update_after_id)
        except Exception:
            pass

        try:
            self._info_update_after_id = self.root.after(delay_ms, self.update_info)
        except Exception:
            self._info_update_after_id = None

    def _add_source_paths(self, paths):
        added_any = False
        added_bytes = 0
        added_count = 0
        for p in paths:
            if not p:
                continue
            try:
                path_str = str(p)
            except Exception:
                continue
            if path_str not in self.source_paths:
                added_any = True
                self.source_paths.append(path_str)
                # Se un'operazione è in corso in modalità batch (solo file), accumula
                # i byte del nuovo file in modo da aggiornare _batch_total_size e
                # _batch_file_count; questo evita che la barra rimanga bloccata al 100%
                # mentre i file appena aggiunti vengono ancora elaborati.
                try:
                    if self.operation_in_progress and int(getattr(self, '_batch_total_size', 0) or 0) > 0:
                        if os.path.isfile(long_path(path_str)):
                            added_bytes += int(os.path.getsize(long_path(path_str)))
                            added_count += 1
                except Exception:
                    pass
                try:
                    self.source_listbox.insert('end', path_str)
                except Exception:
                    pass

        if added_any:
            # Aggiorna i contatori batch se l'operazione è in corso
            try:
                if self.operation_in_progress and int(getattr(self, '_batch_total_size', 0) or 0) > 0:
                    if added_bytes > 0:
                        self._batch_total_size += added_bytes
                    if added_count > 0:
                        self._batch_file_count += added_count
            except Exception:
                pass
            self._on_sources_changed()

    def _context_menu_pick_destination(self):
        if self.dest_path.get():
            return

        folder = filedialog.askdirectory(title=self._t('dlg_select_destination_folder_title', 'Seleziona cartella destinazione'))
        if not folder:
            return

        self.dest_path.set(folder)

        # Auto-profilazione (buffer/thread) quando abbiamo sorgente+dest
        try:
            self._auto_profile_parameters()
        except Exception:
            pass

        # Feedback leggero: mette focus sul bottone coerente con l'azione scelta nel menu
        try:
            if self.context_operation_type == 'move':
                self.move_btn.focus_set()
                self.status_label.configure(text=self._t('status_ready_move', "Pronto (Sposta)"))
            elif self.context_operation_type == 'copy':
                self.copy_btn.focus_set()
                self.status_label.configure(text=self._t('status_ready_copy', "Pronto (Copia)"))
        except Exception:
            pass

        # Avvio automatico se l'app è stata lanciata dal menu contestuale
        try:
            if self.context_operation_type and not self.operation_in_progress:
                self._start_operation(self.context_operation_type)
        except Exception:
            pass

    def _on_engine_error(self, message: str):
        try:
            self._last_engine_error = str(message)
        except Exception:
            self._last_engine_error = None

        def _apply():
            try:
                self.status_label.configure(text=str(message))
            except Exception:
                pass

        try:
            self.root.after(0, _apply)
        except Exception:
            pass
    
    def create_widgets(self):
        """Crea i widget della GUI con CustomTkinter"""
        # Layout root: notebook sopra (espandibile) + footer sotto (altezza fissa)
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_rowconfigure(1, weight=0)
        self.root.grid_columnconfigure(0, weight=1)
        
        # Disabilita propagazione resize dai widget figli (mantiene dimensioni salvate)
        self.root.grid_propagate(False)

        # Notebook per tabs
        self.notebook = ctk.CTkTabview(self.root)
        self.notebook.grid(row=0, column=0, sticky='nsew', padx=5, pady=(5, 0))
        
        # Aggiungi tabs VUOTE (creazione veloce)
        self._tab_titles['main'] = self._t('tab_main', "📋 Principale")
        self._tab_titles['info'] = self._t('tab_info', "ℹ️ Informazioni")
        self._tab_titles['menu'] = self._t('tab_menu', "🖱️ Menu Contestuale")
        self._tab_titles['view'] = self._t('tab_view', "👁️ Visualizzazione")

        self.main_tab = self.notebook.add(self._tab_titles['main'])
        self.info_tab = self.notebook.add(self._tab_titles['info'])
        self.menu_tab = self.notebook.add(self._tab_titles['menu'])
        self.view_tab = self.notebook.add(self._tab_titles['view'])
        
        # Crea main_tab subito (quella principale)
        self.create_main_tab()
        
        # Carica le altre tab nel main thread dopo un breve ritardo (avvio veloce).
        # IMPORTANTE: la creazione di widget Tkinter NON è thread-safe –
        # non usare threading.Thread per creare widget.
        def load_remaining_tabs():
            try:
                self.create_info_tab()
            except Exception as e:
                print(f"Errore creazione info tab: {e}")
            try:
                self.create_menu_tab()
            except Exception as e:
                print(f"Errore creazione menu tab: {e}")
            try:
                self.create_view_tab()
            except Exception as e:
                print(f"Errore creazione view tab: {e}")

        self.root.after(500, load_remaining_tabs)
        
        # Footer con status bar
        footer_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        footer_frame.grid(row=1, column=0, sticky='ew', padx=5, pady=(0, 2))
        footer_frame.grid_propagate(False)  # Blocca altezza del footer
        footer_frame.configure(height=50)   # Altezza fissa
        
        status_frame = ctk.CTkFrame(footer_frame, fg_color="transparent")
        status_frame.pack(side='right', fill='x')
        
        self.status_label = ctk.CTkLabel(
            status_frame,
            text=self._t('status_ready', 'Pronto'),
            text_color=("gray", "gray")
        )
        self.status_label.pack(side='right', padx=5)

        try:
            self._i18n_register(self.status_label, 'status_ready', 'Pronto')
        except Exception:
            pass
    
    def create_main_tab(self):
        """Tab principale: gestione file e cartelle"""
        # Configura grid layout per main_tab: percorsi espandibili, progresso sempre visibile
        self.main_tab.grid_columnconfigure(0, weight=1)
        self.main_tab.grid_rowconfigure(0, weight=1)   # Percorsi: si espande/contrae
        self.main_tab.grid_rowconfigure(1, weight=0)   # Opzioni: altezza fissa
        self.main_tab.grid_rowconfigure(2, weight=0)   # Operazioni: altezza fissa
        self.main_tab.grid_rowconfigure(3, weight=0)   # Progresso: altezza fissa, sempre visibile

        # Sezione Percorsi
        paths_frame = ctk.CTkFrame(self.main_tab)
        paths_frame.grid(row=0, column=0, sticky='nsew', padx=5, pady=1)
        
        self.paths_label = ctk.CTkLabel(paths_frame, text=self._t('main_paths_section', "📂 PERCORSI"), font=("Segoe UI", 12, "bold"))
        self._i18n_register(self.paths_label, 'main_paths_section', "📂 PERCORSI")
        self.paths_label.pack(anchor='w', padx=10, pady=(3, 1))
        
        # Inner frame con grid layout (fill='both' per espandersi verticalmente)
        paths_inner = ctk.CTkFrame(paths_frame)
        paths_inner.pack(fill='both', expand=True, padx=5, pady=1)
        paths_inner.grid_columnconfigure(1, weight=1)  # Fa espandere src_frame
        
        # Sorgente
        self.src_label = ctk.CTkLabel(paths_inner, text=self._t('main_source', "Sorgente:"))
        self._i18n_register(self.src_label, 'main_source', "Sorgente:")
        self.src_label.grid(row=0, column=0, sticky='nw', pady=(5,0))
        
        # Frame interno per listbox + scrollbar (altezza elastica)
        src_inner_frame = ctk.CTkFrame(paths_inner)
        src_inner_frame.grid(row=0, column=1, sticky='nsew', padx=5)  # nsew = espandi in tutte le direzioni
        src_inner_frame.grid_rowconfigure(0, weight=1, minsize=80)  # Espande verticalmente con minimo 80px
        src_inner_frame.grid_columnconfigure(0, weight=1)
        
        # Determina colori Listbox in base al tema
        listbox_bg = "#2b2b2b" if self.current_theme == 'dark' else "#ffffff"
        listbox_fg = "#ffffff" if self.current_theme == 'dark' else "#000000"
        
        self.source_listbox = tk.Listbox(
            src_inner_frame,
            height=5,
            bg=listbox_bg,
            fg=listbox_fg,
            selectbackground="#0078d4",
            relief='flat',
            borderwidth=1
        )
        self.source_listbox.grid(row=0, column=0, sticky='nsew', padx=(0,2))  # nsew = espandi in tutte le direzioni
        
        scrollbar = ctk.CTkScrollbar(src_inner_frame, command=self.source_listbox.yview)
        scrollbar.grid(row=0, column=1, sticky='ns')
        self.source_listbox.config(yscrollcommand=scrollbar.set)
        
        # Configura grid di paths_inner per far espandere src_inner_frame
        paths_inner.grid_rowconfigure(0, weight=1)  # La riga 0 si espande verticalmente
        
        # Hint DnD (sotto la listbox, stessa colonna)
        hint_color = "gray" if self.current_theme == 'dark' else "#7a5a00"
        self.dnd_hint = ctk.CTkLabel(
            paths_inner,
            text="",
            text_color=hint_color,
            font=("Segoe UI", 8)
        )
        self.dnd_hint.grid(row=1, column=1, sticky='w', padx=5, pady=(2,0))
        
        # Drag and Drop
        if HAS_DND and self.dnd_enabled:
            try:
                self.source_listbox.drop_target_register(DND_FILES)
                self.source_listbox.dnd_bind('<<Drop>>', self.drop_files)
                
                hint_text = self._t('dnd_hint', "💡 Trascina qui i file")
                if is_admin():
                    hint_text += " (DnD admin)"
                
                self.dnd_hint.configure(text=hint_text)
                self._i18n_register(self.dnd_hint, 'dnd_hint', "💡 Trascina qui i file")
            except Exception:
                pass
        elif HAS_DND and is_admin():
            try:
                self.dnd_hint.configure(text=self._t('dnd_not_available_admin', "⚠️ DnD non disponibile (Administrator)"), text_color="orange")
                self._i18n_register(self.dnd_hint, 'dnd_not_available_admin', "⚠️ DnD non disponibile (Administrator)")
            except Exception:
                pass
        elif not HAS_DND:
            try:
                self.dnd_hint.configure(text=self._t('dnd_install_hint', "💡 pip install tkinterdnd2 per drag & drop"))
                self._i18n_register(self.dnd_hint, 'dnd_install_hint', "💡 pip install tkinterdnd2 per drag & drop")
            except Exception:
                pass
        
        # Bottoni sorgente
        src_btn_frame = ctk.CTkFrame(paths_inner)
        src_btn_frame.grid(row=0, column=2, padx=5, sticky='n')
        src_btn_frame.grid(row=0, column=2, padx=5, sticky='n')
        
        self.add_file_btn = ctk.CTkButton(src_btn_frame, text=self._t('btn_add_file', "➕ File"), command=self._add_files, width=100)
        self._i18n_register(self.add_file_btn, 'btn_add_file', "➕ File")
        self.add_file_btn.pack(pady=2, fill='x')

        self.add_folder_btn = ctk.CTkButton(src_btn_frame, text=self._t('btn_add_folder', "➕ Cartella"), command=self._add_folder, width=100)
        self._i18n_register(self.add_folder_btn, 'btn_add_folder', "➕ Cartella")
        self.add_folder_btn.pack(pady=2, fill='x')

        self.remove_btn = ctk.CTkButton(src_btn_frame, text=self._t('btn_remove', "❌ Rimuovi"), command=self._remove_source_item, width=100)
        self._i18n_register(self.remove_btn, 'btn_remove', "❌ Rimuovi")
        self.remove_btn.pack(pady=2, fill='x')

        self.remove_all_btn = ctk.CTkButton(src_btn_frame, text=self._t('btn_remove_all', "🗑️ Rimuovi Tutti"), command=self._clear_all_sources_and_destination, width=100)
        self._i18n_register(self.remove_all_btn, 'btn_remove_all', "🗑️ Rimuovi Tutti")
        self.remove_all_btn.pack(pady=2, fill='x')
        src_btn_frame.grid_rowconfigure(0, weight=1)  # Centra verticalmente i bottoni
        
        # Destinazione (row 2, per stare sotto all'hint)
        self.dst_label = ctk.CTkLabel(paths_inner, text=self._t('main_destination', "Destinazione:"))
        self._i18n_register(self.dst_label, 'main_destination', "Destinazione:")
        self.dst_label.grid(row=2, column=0, sticky='w', pady=(5,0))
        
        dest_entry = ctk.CTkEntry(paths_inner, textvariable=self.dest_path)
        dest_entry.grid(row=2, column=1, sticky='ew', padx=5)
        
        self.browse_btn = ctk.CTkButton(paths_inner, text=self._t('btn_browse', "Sfoglia"), command=lambda: self.browse_folder(for_source=False), width=100)
        self._i18n_register(self.browse_btn, 'btn_browse', "Sfoglia")
        self.browse_btn.grid(row=2, column=2, padx=5)
        
        # Sezione Opzioni
        options_frame = ctk.CTkFrame(self.main_tab)
        options_frame.grid(row=1, column=0, sticky='ew', padx=5, pady=1)
        
        self.options_label = ctk.CTkLabel(options_frame, text=self._t('main_options_section', "⚙️ OPZIONI"), font=("Segoe UI", 12, "bold"))
        self._i18n_register(self.options_label, 'main_options_section', "⚙️ OPZIONI")
        self.options_label.pack(anchor='w', padx=5, pady=(2, 1))
        
        opts_inner = ctk.CTkFrame(options_frame)
        opts_inner.pack(fill='x', padx=5, pady=1)
        
        self.ramdrive_checkbox = ctk.CTkCheckBox(opts_inner, text=self._t('opt_use_ramdrive', "Usa RamDrive"), variable=self.ramdrive_enabled)
        self._i18n_register(self.ramdrive_checkbox, 'opt_use_ramdrive', "Usa RamDrive")
        self.ramdrive_checkbox.pack(anchor='w', pady=2)
        self.overwrite_checkbox = ctk.CTkCheckBox(opts_inner, text=self._t('opt_overwrite', "Sovrascrivi file esistenti"), variable=self.overwrite_enabled)
        self._i18n_register(self.overwrite_checkbox, 'opt_overwrite', "Sovrascrivi file esistenti")
        self.overwrite_checkbox.pack(anchor='w', pady=2)

        self.delete_source_checkbox = ctk.CTkCheckBox(opts_inner, text=self._t('opt_delete_source', "Elimina origine (Sposta)"), variable=self.delete_source_enabled)
        self._i18n_register(self.delete_source_checkbox, 'opt_delete_source', "Elimina origine (Sposta)")
        self.delete_source_checkbox.pack(anchor='w', pady=2)
        
        # Buffer e Thread - HARDCODED (auto-profilazione basata su storage)
        params_frame = ctk.CTkFrame(opts_inner)
        params_frame.pack(fill='x', pady=5)
        
        self.buffer_label = ctk.CTkLabel(params_frame, text=self._t('label_buffer_mb', "Buffer (MB):"))
        self._i18n_register(self.buffer_label, 'label_buffer_mb', "Buffer (MB):")
        self.buffer_label.pack(side='left', padx=5)
        buffer_entry = ctk.CTkEntry(params_frame, textvariable=self.buffer_size, width=80, state='disabled')
        buffer_entry.pack(side='left', padx=5)
        
        self.threads_label = ctk.CTkLabel(params_frame, text=self._t('label_threads', "Thread:"))
        self._i18n_register(self.threads_label, 'label_threads', "Thread:")
        self.threads_label.pack(side='left', padx=20)
        thread_entry = ctk.CTkEntry(params_frame, textvariable=self.threads, width=80, state='disabled')
        thread_entry.pack(side='left', padx=5)
        
        self.auto_profile_hint = ctk.CTkLabel(params_frame, text=self._t('hint_auto_profile', "(Auto-profilazione basata su storage)"), text_color="gray")
        self._i18n_register(self.auto_profile_hint, 'hint_auto_profile', "(Auto-profilazione basata su storage)")
        self.auto_profile_hint.pack(side='left', padx=20)
        
        # Sezione Operazioni
        ops_frame = ctk.CTkFrame(self.main_tab)
        ops_frame.grid(row=2, column=0, sticky='ew', padx=10, pady=1)
        
        self.ops_label = ctk.CTkLabel(ops_frame, text=self._t('main_ops_section', "🚀 OPERAZIONI"), font=("Segoe UI", 12, "bold"))
        self._i18n_register(self.ops_label, 'main_ops_section', "🚀 OPERAZIONI")
        self.ops_label.pack(anchor='w', padx=10, pady=(3, 1))
        
        ops_inner = ctk.CTkFrame(ops_frame)
        ops_inner.pack(fill='x', padx=10, pady=2)
        
        # Frame interno per centrare i bottoni
        buttons_frame = ctk.CTkFrame(ops_inner, fg_color="transparent")
        buttons_frame.pack(expand=True)
        
        self.copy_btn = ctk.CTkButton(buttons_frame, text=self._t('btn_copy', "📋 Copia"), command=lambda: self._start_operation('copy'))
        self._i18n_register(self.copy_btn, 'btn_copy', "📋 Copia")
        self.copy_btn.pack(side='left', padx=5)
        
        self.move_btn = ctk.CTkButton(buttons_frame, text=self._t('btn_move', "✂️ Sposta"), command=lambda: self._start_operation('move'))
        self._i18n_register(self.move_btn, 'btn_move', "✂️ Sposta")
        self.move_btn.pack(side='left', padx=5)
        
        self.cancel_btn = ctk.CTkButton(buttons_frame, text=self._t('btn_cancel', "❌ Annulla"), command=self.cancel_operation, state='disabled')
        self._i18n_register(self.cancel_btn, 'btn_cancel', "❌ Annulla")
        self.cancel_btn.pack(side='left', padx=5)
        
        # Sezione Progresso (sempre visibile in fondo grazie al grid layout)
        progress_frame = ctk.CTkFrame(self.main_tab)
        progress_frame.grid(row=3, column=0, sticky='sew', padx=5, pady=(2, 3))
        
        self.progress_section_label = ctk.CTkLabel(progress_frame, text=self._t('main_progress_section', "📊 PROGRESSO"), font=("Segoe UI", 12, "bold"))
        self._i18n_register(self.progress_section_label, 'main_progress_section', "📊 PROGRESSO")
        self.progress_section_label.pack(anchor='w', padx=5, pady=(2, 1))
        
        prog_inner = ctk.CTkFrame(progress_frame)
        prog_inner.pack(fill='x', padx=5, pady=(2, 8))

        # Progress text (sopra la barra)
        self.progress_label = ctk.CTkLabel(
            prog_inner,
            text=self._t('progress_placeholder', "Pronto|0%|--- MB/s|ETA:--:--").replace('|', ' | '),
            text_color=("#000000", "#FFFFFF"),
            font=("Segoe UI", 13, "bold"),
            anchor='center',
            justify='center'
        )
        self.progress_label.pack(fill='x', pady=(3, 3))

        # Progress bar (semplice, senza testo sovrapposto)
        self.progress_bar = ctk.CTkProgressBar(
            prog_inner, 
            height=26, 
            mode='determinate',
            progress_color=("#1f6aa5", "#1f6aa5"),
            border_width=1
        )
        self.progress_bar.set(0.0)
        self.progress_bar.pack(fill='x', pady=(2, 3))

        # Compatibilità: file_counter_label è None (disabilitato per spazio)
        self.file_counter_label = None

        # Riga dettagli non necessaria (manteniamo per compatibilita')
        self.progress_details_row = ctk.CTkFrame(prog_inner, fg_color="transparent")
        self.progress_details_row.pack_forget()

        # Mostra sempre la progress UI (non nasconderla all'avvio)
        self._progress_ui_visible = True

    def _show_progress_ui(self):
        if getattr(self, '_progress_ui_visible', False):
            return
        try:
            if hasattr(self, 'progress_label') and self.progress_label is not None:
                self.progress_label.pack(fill='x', pady=(2, 2))
            self.progress_bar.pack(fill='x', pady=0)
            self.progress_details_row.pack_forget()
            self._progress_ui_visible = True
        except Exception:
            pass

    def _hide_progress_ui(self):
        if not getattr(self, '_progress_ui_visible', False):
            return
        try:
            if hasattr(self, 'progress_label') and self.progress_label is not None:
                self.progress_label.pack_forget()
            self.progress_bar.pack_forget()
            self.progress_details_row.pack_forget()
            self._progress_ui_visible = False
        except Exception:
            pass

    def _set_progress_text(self, text: str, percentage: int | None = None):
        """Aggiorna il testo della barra di progresso"""
        try:
            if hasattr(self, 'progress_label') and self.progress_label is not None:
                self.progress_label.configure(text=text)
        except Exception:
            pass

    def _set_file_counter_text(self, text: str) -> None:
        try:
            if getattr(self, 'file_counter_label', None) is None:
                return
            self.file_counter_label.configure(text=text)
        except Exception:
            pass
    
    def create_info_tab(self):
        """Tab informazioni - Sistema, Storage, RamDrive"""
        frame = ctk.CTkFrame(self.info_tab)
        frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Scrollable text box per informazioni con sfondo simile agli altri frame
        # Usa un colore che si adatta al tema (grigio scuro in dark, grigio chiaro in light)
        self.info_text = ctk.CTkTextbox(frame, wrap='word', state='disabled', fg_color=("gray85", "gray20"))
        self.info_text.pack(fill='both', expand=True, pady=5)
        
        # Bottone check updates
        self.check_updates_btn = ctk.CTkButton(frame, text=self._t('btn_check_updates', "🚀 Controlla Aggiornamenti"), command=self._manual_check_updates, fg_color="#2E7D32")
        self._i18n_register(self.check_updates_btn, 'btn_check_updates', "🚀 Controlla Aggiornamenti")
        self.check_updates_btn.pack(pady=5)
        
        # Carica informazioni iniziali in modo async per non bloccare avvio
        self.root.after(100, self.update_info)
    
    def update_info(self):
        """Aggiorna le informazioni di sistema nel tab"""
        try:
            import platform
            import psutil
            
            self.info_text.configure(state='normal')
            self.info_text.delete('1.0', 'end')
            
            # === SYSTEM INFO ===
            self.info_text.insert('end', self._t('info_system_section', "🔧 INFORMAZIONI SISTEMA") + "\n")
            
            # OS e Python
            os_name = f"{platform.system()} {platform.release()}"
            python_ver = platform.python_version()
            self.info_text.insert('end', f"OS: {os_name} | Python: {python_ver}\n")
            
            # CPU
            cpu_info = platform.processor()
            self.info_text.insert('end', f"CPU: {cpu_info}\n")
            
            # RAM
            mem = psutil.virtual_memory()
            ram_total = mem.total / (1024**3)
            ram_available = mem.available / (1024**3)
            ram_percent = mem.percent
            self.info_text.insert('end', self._t('info_ram_line', 'RAM: {total:.1f}GB | Libera: {free:.1f}GB ({pct:.0f}%)').format(total=ram_total, free=ram_available, pct=ram_percent) + "\n")
            
            # === RAMDRIVE ===
            self.info_text.insert('end', "\n" + self._t('info_ramdrive_section', "💾 RAMDRIVE") + "\n")
            
            ramdrive_status = self.ramdrive_manager.detect_ramdrive()
            if ramdrive_status:
                ram_letter = self.ramdrive_manager.ramdrive_letter
                self.info_text.insert('end', self._t('info_status_detected', "✅ RILEVATO") + f" ({ram_letter}:)")
                
                # Ottieni info spazio RamDrive
                try:
                    ram_info = self.ramdrive_manager.get_ramdrive_info()
                    if ram_info['available']:
                        self.info_text.insert('end', f" | {ram_info['total_formatted']} | {self._t('info_free_label', 'Libero')}: {ram_info['free_formatted']}")
                except:
                    pass
                self.info_text.insert('end', "\n")
            else:
                self.info_text.insert('end', self._t('info_status_not_detected', "❌ NON RILEVATO") + "\n")
            
            # === STORAGE ===
            self.info_text.insert('end', "\n" + self._t('info_storage_section', "🗂️ STORAGE") + "\n")
            try:
                import os
                drives = []
                for letter in sorted('CDEFGHIJKLMNOPQRSTUVWXYZ'):
                    if os.path.exists(f"{letter}:\\"):
                        storage_type = self.ramdrive_manager.get_storage_type(f"{letter}:\\")
                        drives.append(f"{letter}: {storage_type.upper()}")
                self.info_text.insert('end', " | ".join(drives) + "\n")
            except Exception as e:
                self.info_text.insert('end', f"{self._t('info_detect_error', 'Errore')}: {str(e)}\n")
            
            # === ENGINE CONFIG ===
            self.info_text.insert('end', "\n" + self._t('info_engine_config', "⚙️ MOTORE") + "\n")
            config_items = [
                f"{self._t('info_buffer_config', 'Buffer')}: {self.buffer_size.get()}MB",
                f"{self._t('info_thread_config', 'Thread')}: {self.threads.get()}",
                f"{self._t('info_ramdrive_config', 'RamDrive')}: {'✅' if self.ramdrive_enabled.get() else '❌'}",
                f"{self._t('info_overwrite_config', 'Sovrascrivi')}: {'✅' if self.overwrite_enabled.get() else '❌'}",
                f"{self._t('info_move_config', 'Sposta')}: {'✅' if self.delete_source_enabled.get() else '❌'}"
            ]
            self.info_text.insert('end', " | ".join(config_items) + "\n")
            
            # === HARDWARE OPTIMIZATION ===
            self.info_text.insert('end', "\n" + self._t('menu_hw_title', "🔧 Ottimizzazione Hardware") + "\n")
            hw_lines = [
                self._t('hw_auto_detect', "Il sistema riconosce automaticamente il tipo di storage:"),
                "",
                "🚀 NVMe: Buffer 256MB, 12 Thread",
                "⚡ SSD: Buffer 128MB, 8 Thread",
                "💾 HDD: Buffer 80MB, 2 Thread",
                "🔌 USB: Buffer 64MB, 4 Thread",
                "🌐 NAS: Buffer 32MB, 2 Thread",
                "💾 RamDrive: Buffer 8MB (RAM pura), 16 Thread",
                "",
                self._t('hw_auto_params', "I parametri vengono regolati automaticamente in base al percorso di destinazione."),
            ]
            self.info_text.insert('end', "\n".join(hw_lines) + "\n")

            # === VERSION ===
            self.info_text.insert('end', "\n📝 Advanced File Mover Pro v")
            app_version = self.config_manager.get('version', '1.0.0')
            self.info_text.insert('end', app_version)
            
            self.info_text.configure(state='disabled')
        except Exception as e:
            self.info_text.configure(state='normal')
            self.info_text.delete('1.0', 'end')
            self.info_text.insert('end', f"{self._t('info_update_error', 'Errore nell\'aggiornamento')}: {str(e)}")
            self.info_text.configure(state='disabled')
    
    def create_menu_tab(self):
        """Tab menu contestuale"""
        frame = ctk.CTkFrame(self.menu_tab)
        frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        title = ctk.CTkLabel(frame, text=self._t('menu_title', "🖱️ Menu Contestuale di Windows"), font=("Segoe UI", 12, "bold"))
        self._i18n_register(title, 'menu_title', "🖱️ Menu Contestuale di Windows")
        title.pack(pady=5)
        
        # Descrizione
        info_frame = ctk.CTkFrame(frame)
        info_frame.pack(fill='x', padx=5, pady=5)
        
        info_label = ctk.CTkLabel(
            info_frame,
            text=self._t(
                'menu_description',
                "Registra il menu contestuale di Windows per accedere rapidamente a Copia e Sposta.\n\n"
                "✅ Tasto destro su file/cartella → Copia Avanzata\n"
                "✅ Tasto destro su file/cartella → Sposta Avanzato\n\n"
                "La sorgente sarà il file/cartella selezionato e la GUI aprirà il browsing per scegliere la destinazione.",
            ),
            justify='left',
            wraplength=550,
        )
        self._i18n_register(info_label, 'menu_description',
                            "Registra il menu contestuale di Windows per accedere rapidamente a Copia e Sposta.\n\n"
                            "✅ Tasto destro su file/cartella → Copia Avanzata\n"
                            "✅ Tasto destro su file/cartella → Sposta Avanzato\n\n"
                            "La sorgente sarà il file/cartella selezionato e la GUI aprirà il browsing per scegliere la destinazione.")
        info_label.pack(anchor='w', padx=5, pady=5)
        
        # Buttons
        buttons_frame = ctk.CTkFrame(frame)
        buttons_frame.pack(pady=15)
        
        self.register_menu_btn = ctk.CTkButton(buttons_frame, text=self._t('btn_register_menu', "✅ Registra Menu"), command=self._register_menu)
        self._i18n_register(self.register_menu_btn, 'btn_register_menu', "✅ Registra Menu")
        self.register_menu_btn.pack(side='left', padx=5)

        self.unregister_menu_btn = ctk.CTkButton(buttons_frame, text=self._t('btn_unregister_menu', "❌ Rimuovi Menu"), command=self._unregister_menu)
        self._i18n_register(self.unregister_menu_btn, 'btn_unregister_menu', "❌ Rimuovi Menu")
        self.unregister_menu_btn.pack(side='left', padx=5)

        self.check_menu_btn = ctk.CTkButton(buttons_frame, text=self._t('btn_check_status', "ℹ️ Verifica Stato"), command=self.check_menu_status)
        self._i18n_register(self.check_menu_btn, 'btn_check_status', "ℹ️ Verifica Stato")
        self.check_menu_btn.pack(side='left', padx=5)
        
        # Status display
        status_frame = ctk.CTkFrame(frame)
        status_frame.pack(fill='x', padx=5, pady=5)
        
        self.menu_status_label = ctk.CTkLabel(status_frame, text=self._t('menu_status_unknown', "Stato: Sconosciuto"), justify='left', wraplength=550)
        self._i18n_register(self.menu_status_label, 'menu_status_unknown', "Stato: Sconosciuto")
        self.menu_status_label.pack(anchor='w', padx=5, pady=5)
        
        # Spacer in fondo per uniformità con altre tab
        ctk.CTkFrame(frame, height=20, fg_color="transparent").pack(fill='x')
        
        # Carica stato iniziale
        self.check_menu_status()
    
    def create_view_tab(self):
        """Tab visualizzazione"""
        frame = ctk.CTkFrame(self.view_tab)
        frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        title = ctk.CTkLabel(frame, text=self._t('view_title', "Visualizzazione"), font=("Segoe UI", 14, "bold"))
        self._i18n_register(title, 'view_title', "Visualizzazione")
        title.pack(pady=5)
        
        # Always on top
        self.always_on_top_checkbox = ctk.CTkCheckBox(frame, text=self._t('always_on_top', "Sempre in primo piano"), variable=self.always_on_top_var, command=self.toggle_always_on_top)
        self._i18n_register(self.always_on_top_checkbox, 'always_on_top', "Sempre in primo piano")
        self.always_on_top_checkbox.pack(anchor='w', padx=5, pady=5)
        
        # Separatore
        sep = ctk.CTkFrame(frame, height=2, fg_color="gray30")
        sep.pack(fill='x', padx=5, pady=8)
        
        # Tema toggle
        tema_label = ctk.CTkLabel(frame, text=self._t('theme_label', "🎨 Tema Interfaccia"), font=("Segoe UI", 12, "bold"))
        self._i18n_register(tema_label, 'theme_label', "🎨 Tema Interfaccia")
        tema_label.pack(anchor='w', padx=5, pady=(5, 2))
        
        self.theme_btn = ctk.CTkButton(
            frame,
            text=self._t('theme_dark_current', "🌙 Tema Scuro (Corrente)") if self.current_theme == 'dark' else self._t('theme_light_current', "☀️ Tema Chiaro (Corrente)"),
            command=self._toggle_theme,
            width=200
        )
        self.theme_btn.pack(padx=5, pady=2)

        # Separatore
        sep2 = ctk.CTkFrame(frame, height=2, fg_color="gray30")
        sep2.pack(fill='x', padx=5, pady=8)

        # Lingua UI
        lang_label = ctk.CTkLabel(frame, text=self._t('language_label', "🌐 Lingua Interfaccia"), font=("Segoe UI", 12, "bold"))
        self._i18n_register(lang_label, 'language_label', "🌐 Lingua Interfaccia")
        lang_label.pack(anchor='w', padx=5, pady=(5, 2))

        values = ["IT", "EN", "FR", "DE", "ES"]

        def _on_language_change(choice: str):
            try:
                code = (choice or '').split()[-1].strip().lower()
                if code not in ('it', 'en', 'fr', 'de', 'es'):
                    return
                self.apply_language(code)
                try:
                    self.lang_hint_label.configure(text=self._t('language_hint_applied', 'Lingua applicata.'))
                except Exception:
                    pass
            except Exception:
                pass

        # Riga selezione lingua: bandiera + dropdown
        lang_row = ctk.CTkFrame(frame, fg_color="transparent")
        lang_row.pack(anchor='w', padx=5, pady=(0, 2))

        try:
            self._load_flag_images()
        except Exception:
            pass

        try:
            img = (getattr(self, '_flag_images', None) or {}).get(self.language_code)
        except Exception:
            img = None

        try:
            self.lang_flag_label = ctk.CTkLabel(lang_row, text="", image=img, width=28, height=18)
            self.lang_flag_label.pack(side='left', padx=(0, 8))
        except Exception:
            self.lang_flag_label = None

        self.lang_menu = ctk.CTkOptionMenu(lang_row, values=values, command=_on_language_change)
        try:
            current = (self.language_code or 'it').upper()
            display = next((v for v in values if v == current), values[0])
            self.lang_menu.set(display)
        except Exception:
            pass
        self.lang_menu.pack(side='left')

        self.lang_hint_label = ctk.CTkLabel(frame, text=self._t('language_hint_applied', 'Lingua applicata.'), text_color=("gray", "gray"))
        self._i18n_register(self.lang_hint_label, 'language_hint_applied', 'Lingua applicata.')
        self.lang_hint_label.pack(anchor='w', padx=5, pady=(0, 5))

        # Privilegi / Elevazione
        elev_label = ctk.CTkLabel(frame, text=self._t('elevation_section', '🔒 Privilegi'), font=("Segoe UI", 12, "bold"))
        self._i18n_register(elev_label, 'elevation_section', '🔒 Privilegi')
        elev_label.pack(anchor='w', padx=5, pady=(5, 2))

        def _toggle_auto_elevate():
            try:
                self.config_manager.set('auto_elevate_on_start', bool(self.auto_elevate_on_start.get()))
            except Exception:
                pass

        self.auto_elevate_checkbox = ctk.CTkCheckBox(
            frame,
            text=self._t('auto_elevate_manual', "Auto-elevazione (UAC) all'avvio (solo avvio manuale)"),
            variable=self.auto_elevate_on_start,
            command=_toggle_auto_elevate,
        )
        self._i18n_register(self.auto_elevate_checkbox, 'auto_elevate_manual', "Auto-elevazione (UAC) all'avvio (solo avvio manuale)")
        self.auto_elevate_checkbox.pack(anchor='w', padx=5, pady=(0, 2))

        self.restart_admin_btn = ctk.CTkButton(
            frame,
            text=self._t('restart_as_admin', 'Riavvia come amministratore'),
            command=self._restart_as_admin,
            width=260,
        )
        self._i18n_register(self.restart_admin_btn, 'restart_as_admin', 'Riavvia come amministratore')
        self.restart_admin_btn.pack(anchor='w', padx=5, pady=(0, 5))
    
    def _auto_tune_parameters(self):
        """Auto-tuning di buffer e thread in base al tipo di storage della destinazione"""
        try:
            if not self.dest_path.get():
                return  # Skip se destinazione non impostata
            
            # Rileva storage type della destinazione usando RamDriveManager
            storage_type_str = self.ramdrive_manager.get_storage_type(self.dest_path.get())
            
            # Mappa storage type string -> parametri ottimali
            optimal_params = {
                'ram': {'buffer_mb': 8, 'threads': 16},
                'nvme': {'buffer_mb': 256, 'threads': 12},
                'ssd': {'buffer_mb': 128, 'threads': 8},
                'usb': {'buffer_mb': 64, 'threads': 4},
                'nas': {'buffer_mb': 32, 'threads': 2},
                'hdd': {'buffer_mb': 80, 'threads': 2}
            }
            
            params = optimal_params.get(storage_type_str, {'buffer_mb': 100, 'threads': 4})
            
            # Aggiorna i parametri visualizzati
            self.buffer_size.set(str(params['buffer_mb']))
            self.threads.set(str(params['threads']))
        
        except Exception as e:
            print(f"Auto-tuning error: {e}")
    
    def _toggle_theme(self):
        """Alterna il tema scuro/chiaro"""
        self.current_theme = 'light' if self.current_theme == 'dark' else 'dark'
        self.config_manager.set('theme', self.current_theme)
        ctk.set_appearance_mode(self.current_theme)
        
        # Aggiorna testo del bottone tema
        if hasattr(self, 'theme_btn'):
            self.theme_btn.configure(
                text=self._t('theme_dark_current', '🌙 Tema Scuro (Corrente)')
                if self.current_theme == 'dark'
                else self._t('theme_light_current', '☀️ Tema Chiaro (Corrente)')
            )
        
        # Aggiorna colori del Listbox (widget tk nativo)
        if self.current_theme == 'dark':
            self.source_listbox.config(bg="#2b2b2b", fg="#ffffff", selectbackground="#0078d4")
        else:
            self.source_listbox.config(bg="#ffffff", fg="#000000", selectbackground="#0078d4")
    
    def _add_files(self):
        """Aggiunge file alla lista sorgente"""
        files = filedialog.askopenfilenames(title=self._t('dlg_select_files_title', 'Seleziona file'))
        added_any = False
        for file in files:
            if file not in self.source_paths:
                added_any = True
                self.source_paths.append(file)
                self.source_listbox.insert('end', file)

        if added_any:
            self._on_sources_changed()
    
    def _add_folder(self):
        """Aggiunge cartella alla lista sorgente"""
        folder = filedialog.askdirectory(title=self._t('dlg_select_folder_title', 'Seleziona cartella'))
        if folder and folder not in self.source_paths:
            self.source_paths.append(folder)
            self.source_listbox.insert('end', folder)

            self._on_sources_changed()
    
    def _remove_source_item(self):
        """Rimuove elemento dalla lista sorgente"""
        selection = self.source_listbox.curselection()
        if selection:
            idx = selection[0]
            self.source_listbox.delete(idx)
            self.source_paths.pop(idx)

            self._on_sources_changed()
    
    def _clear_all_sources(self):
        """Rimuove TUTTI gli elementi dalla lista sorgente"""
        if self.source_paths:
            self.source_listbox.delete(0, 'end')
            self.source_paths.clear()

            self._on_sources_changed()

    def _clear_all_sources_and_destination(self):
        """Pulisce sorgenti + destinazione e aggiorna info (per bottone 'Rimuovi Tutti')."""
        try:
            if self.source_paths:
                self.source_listbox.delete(0, 'end')
                self.source_paths.clear()
        except Exception:
            pass

        try:
            self.dest_path.set("")
        except Exception:
            pass

        # Aggiorna info anche se l'Info tab non è ancora pronto: usa i trigger esistenti
        try:
            self._on_sources_changed()
        except Exception:
            pass
        try:
            self._on_destination_changed()
        except Exception:
            pass
    
    def drop_files(self, event):
        """Gestisce i file/cartelle trascinati sulla listbox sorgente"""
        try:
            # Il dato può arrivare in formati diversi da tkinterdnd2
            files = self.root.tk.splitlist(event.data)
            
            added_count = 0
            for file_path in files:
                # Rimuove eventuali graffe, apici, spazi extra
                file_path = file_path.strip('{}"\' ')
                
                if not file_path or not os.path.exists(long_path(file_path)):
                    continue
                
                # Aggiungi solo se non già presente
                if file_path not in self.source_paths:
                    self.source_paths.append(file_path)
                    try:
                        self.source_listbox.insert('end', file_path)
                    except Exception:
                        pass
                    added_count += 1
            
            if added_count > 0:
                self._on_sources_changed()
                try:
                    status_msg = self._t('status_dnd_added', f"Aggiunti {added_count} elementi")
                    self.status_label.configure(text=status_msg)
                except Exception:
                    pass
            
            return event.action
        except Exception as e:
            print(f"Errore drop_files: {e}")
            return 'copy'
    
    def browse_folder(self, for_source=False):
        """Sfoglia per cartella"""
        folder = filedialog.askdirectory(title=self._t('dlg_select_folder_title', 'Seleziona cartella'))
        if folder:
            if for_source:
                if folder not in self.source_paths:
                    self.source_paths.append(folder)
                    self.source_listbox.insert('end', folder)
                    self._on_sources_changed()
            else:
                self.dest_path.set(folder)
            
            # Auto-profilazione se abbiamo sia sorgente che destinazione
            self._auto_profile_parameters()
    
    def _auto_profile_parameters(self):
        """Alias di _auto_tune_parameters (già unificati: la logica dipende solo dalla destinazione)."""
        self._auto_tune_parameters()
    
    def _start_operation(self, operation_type):
        """Avvia copia/sposta"""
        if not self.source_paths:
            messagebox.showwarning(self._t('warn_title', 'Avviso'), self._t('warn_select_source', 'Seleziona almeno una sorgente'))
            return

        try:
            for p in list(self.source_paths or []):
                if _is_shell_namespace_path(p):
                    return
        except Exception:
            pass
        
        if not self.dest_path.get():
            messagebox.showwarning(self._t('warn_title', 'Avviso'), self._t('warn_select_destination', 'Seleziona una destinazione'))
            return
        
        self.cancel_requested = False
        self.operation_in_progress = True

        # Ensure accurato immediato (in background) SOLO per i drive correnti
        # - Non blocca l'operazione
        # - In avvio da menu contestuale forza refresh anche se in cache (prima sessione)
        try:
            self._ensure_accurate_storage_for_current_drives_async(operation_type)
        except Exception:
            pass

        try:
            if hasattr(self, 'file_counter_label') and self.file_counter_label is not None:
                self.file_counter_label.configure(text="")
        except Exception:
            pass

        # Reset stato batch (selezione multipli file)
        try:
            self._batch_file_count = 0
            self._batch_file_index = 0
            self._batch_total_size = 0
            self._batch_completed_bytes = 0
        except Exception:
            pass

        # Mostra UI progresso quando parte l'operazione
        self.root.after(0, self._show_progress_ui)
        self.copy_btn.configure(state='disabled')
        self.move_btn.configure(state='disabled')
        self.cancel_btn.configure(state='normal')
        
        self.operation_thread = threading.Thread(
            target=self._operation_worker,
            args=(operation_type,),
            daemon=True
        )
        self.operation_thread.start()

    def _ensure_accurate_storage_for_current_drives_async(self, operation_type: str):
        try:
            letters = set()

            # Sorgenti
            for src in list(self.source_paths or []):
                try:
                    drive = os.path.splitdrive(str(src))[0]
                    if drive:
                        letter = drive[0].upper()
                        if 'A' <= letter <= 'Z':
                            letters.add(letter)
                except Exception:
                    pass

            # Destinazione
            try:
                dest = self.dest_path.get()
                drive = os.path.splitdrive(str(dest))[0]
                if drive:
                    letter = drive[0].upper()
                    if 'A' <= letter <= 'Z':
                        letters.add(letter)
            except Exception:
                pass

            if not letters:
                return

            selected_letters = sorted(letters)
            force = bool(self.launched_from_context_menu)

            def worker(ls, force_refresh):
                try:
                    for letter in ls:
                        try:
                            # Limita concorrenza PowerShell anche tra thread diversi
                            try:
                                self._accurate_detection_semaphore.acquire()
                                self.ramdrive_manager.refresh_storage_type_for_letter(letter, force=force_refresh)
                            finally:
                                try:
                                    self._accurate_detection_semaphore.release()
                                except Exception:
                                    pass
                        except Exception:
                            pass
                finally:
                    def _apply():
                        # Ri-applica tuning/profilo in base alla classificazione aggiornata
                        try:
                            self._auto_tune_parameters()
                        except Exception:
                            pass
                        try:
                            # Auto-profilazione ha senso se abbiamo sorgente+dest
                            self._auto_profile_parameters()
                        except Exception:
                            pass

                        # Se un'operazione è in corso, prova ad aggiornare anche l'engine (best-effort)
                        try:
                            if self.operation_in_progress and hasattr(self, 'file_engine') and self.file_engine is not None:
                                self.file_engine.buffer_size = int(self.buffer_size.get()) * 1024 * 1024
                                self.file_engine.num_threads = int(self.threads.get())
                        except Exception:
                            pass

                        self._schedule_info_update(delay_ms=0)

                    try:
                        self.root.after(0, _apply)
                    except Exception:
                        pass

            threading.Thread(target=worker, args=(selected_letters, force), daemon=True).start()
        except Exception:
            pass

    def _on_engine_progress(self, progress_data):
        """Riceve progress dal FileOperationEngine e aggiorna la UI."""
        try:
            pct = progress_data.get('percentage', 0)
            current = progress_data.get('current_file', '')
            file_index = progress_data.get('file_index', 0)
            file_count = progress_data.get('file_count', 0)
        except Exception:
            pct = 0
            current = ''
            file_index = 0
            file_count = 0

        def _apply():
            # pct dal motore è float (0-100)
            try:
                self._update_progress(pct, current)
            except Exception:
                pass

            # Aggiorna contatore file su label dedicata (più stabile)
            # - Se l'utente ha selezionato SOLO file, usa un contatore "batch" (1/n) anche per n=1
            # - Se c'è una cartella tra le sorgenti, usa il contatore del motore (file dentro la cartella)
            try:
                if getattr(self, 'file_counter_label', None) is None:
                    return
                batch_n = int(getattr(self, '_batch_file_count', 0) or 0)
                batch_i = int(getattr(self, '_batch_file_index', 0) or 0)
                if batch_n > 1:
                    if batch_i <= 0:
                        batch_i = 1
                    self.file_counter_label.configure(text=f"{batch_i}/{batch_n}")
                    return
                elif batch_n == 1:
                    self.file_counter_label.configure(text="")
                    return

                n = int(file_count)
                i = int(file_index)
                if n > 1:
                    if i > 0:
                        self.file_counter_label.configure(text=f"{i}/{n}")
                    else:
                        self.file_counter_label.configure(text=f"0/{n}")
                else:
                    self.file_counter_label.configure(text="")
            except Exception:
                pass

        try:
            self.root.after(0, _apply)
        except Exception:
            pass
    
    def _operation_worker(self, operation_type):
        """Worker thread per operazione copia/sposta"""
        result_state = 'error'
        try:
            # Reset progress bar e timer
            self._progress_start_time = None  # Reset timer per ETA
            self.root.after(0, lambda: self._update_progress(0, self._t('status_operation_in_progress', 'Operazione in corso...')))
            self.root.after(0, lambda: self.status_label.configure(text=self._t('status_operation_running', 'Operazione {op} in corso...').format(op=self._op_name_upper(operation_type))))
            
            # Controlla se usare RamDrive
            try:
                # Refresh detection per gestire cambi a runtime (lettera/dimensione)
                self.ramdrive_manager.refresh_ramdrive()
            except Exception:
                pass

            use_ramdrive = self.ramdrive_enabled.get() and self.ramdrive_manager.detect_ramdrive()
            try:
                self.file_engine.use_ramdrive = bool(use_ramdrive)
                self.file_engine.ramdrive_letter = self.ramdrive_manager.ramdrive_letter if use_ramdrive else None
            except Exception:
                pass

            # Feedback (non invasivo) su stato RamDrive
            try:
                if use_ramdrive and getattr(self.ramdrive_manager, 'ramdrive_letter', None):
                    self.root.after(
                        0,
                        lambda l=self.ramdrive_manager.ramdrive_letter: self.status_label.configure(
                            text=self._t('status_operation_running_ramdrive', 'Operazione {op} in corso... (RamDrive: {letter}:)').format(op=self._op_name_upper(operation_type), letter=l)
                        ),
                    )
            except Exception:
                pass
            
            # Aggiorna engine con parametri correnti
            self.file_engine.buffer_size = int(self.buffer_size.get()) * 1024 * 1024
            self.file_engine.num_threads = int(self.threads.get())
            self.file_engine.overwrite = self.overwrite_enabled.get()  # collega checkbox overwrite
            self.file_engine.reset_progress()
            
            destination = self.dest_path.get()

            # Se l'utente ha selezionato SOLO file, mostra sempre (1/n) a livello batch
            try:
                only_files = True
                for s in self.source_paths:
                    if os.path.isdir(long_path(s)):
                        only_files = False
                        break
                if only_files:
                    self._batch_file_count = int(len(self.source_paths))
                    self._batch_file_index = 0
                    # Calcola il totale byte per percentuale/ETA cumulativi
                    total_bytes = 0
                    for s in self.source_paths:
                        try:
                            total_bytes += int(os.path.getsize(long_path(s)))
                        except Exception:
                            pass
                    self._batch_total_size = int(total_bytes)
                    self._batch_completed_bytes = 0
                else:
                    self._batch_file_count = 0
                    self._batch_file_index = 0
                    self._batch_total_size = 0
                    self._batch_completed_bytes = 0
            except Exception:
                self._batch_file_count = 0
                self._batch_file_index = 0
                self._batch_total_size = 0
                self._batch_completed_bytes = 0
            
            # Calcola numero totale di sorgenti per barra progresso
            total_sources = len(self.source_paths)
            
            # Esegui operazione per ogni sorgente
            for idx, source in enumerate(self.source_paths, start=1):
                if self.cancel_requested:
                    self.root.after(0, lambda: self._update_progress(0, self._t('status_cancelled', "❌ Operazione annullata")))
                    self.root.after(0, lambda: self.status_label.configure(text=self._t('status_cancelled', "❌ Operazione annullata")))
                    result_state = 'cancelled'
                    break

                # Aggiorna contatore batch (solo se selezione contiene solo file)
                try:
                    n = int(getattr(self, '_batch_file_count', 0) or 0)
                    if n > 1:
                        self._batch_file_index = int(idx)
                        i = int(self._batch_file_index)
                        self.root.after(0, lambda i=i, n=n: self._set_file_counter_text(f"{i}/{n}"))
                    elif n == 1:
                        self.root.after(0, lambda: self._set_file_counter_text(""))
                except Exception:
                    pass
                
                # Informa che stiamo elaborando questo file
                self.root.after(0, lambda s=source: self.status_label.configure(text=self._t('status_processing_file', 'Elaborando: {name}...').format(name=Path(s).name)))
                
                # Se la sorgente è una cartella, copia/sposta la cartella intera dentro la destinazione
                # (es: dest\NomeCartella) invece di riversarne i file direttamente nella root
                item_destination = destination
                try:
                    if os.path.isdir(long_path(source)):
                        item_destination = os.path.join(destination, Path(source).name)
                except Exception:
                    item_destination = destination

                if operation_type == 'copy':
                    try:
                        self._last_engine_error = None
                    except Exception:
                        pass
                    success = self.file_engine.copy(source, item_destination)
                elif operation_type == 'move':
                    try:
                        self._last_engine_error = None
                    except Exception:
                        pass
                    success = self.file_engine.move(source, item_destination)
                else:
                    raise ValueError(self._t('error_unknown_operation', 'Operazione sconosciuta: {operation}').format(operation=operation_type))

                # Aggiorna bytes completati per batch (solo file)
                try:
                    if success and int(getattr(self, '_batch_total_size', 0) or 0) > 0 and os.path.isfile(long_path(source)):
                        self._batch_completed_bytes += int(os.path.getsize(long_path(source)))
                except Exception:
                    pass
                
                if not success:
                    try:
                        err = getattr(self, '_last_engine_error', None)
                    except Exception:
                        err = None
                    msg = self._t('status_error_during_operation', '❌ Errore durante {op}').format(op=self._op_name(operation_type))
                    if err:
                        msg = f"{msg}: {err}"
                    self.root.after(0, lambda m=msg: self._update_progress(0, m))
                    self.root.after(0, lambda m=msg: self.status_label.configure(text=m))
                    result_state = 'error'
                    break
            else:
                # Tutti i file processati con successo
                self.root.after(0, lambda: self._update_progress(100, self._t('status_operation_completed', '✅ {op} completato!').format(op=self._op_name_upper(operation_type))))
                self.root.after(0, lambda: self.status_label.configure(text=self._t('status_operation_completed', '✅ {op} completato!').format(op=self._op_name_upper(operation_type))))
                result_state = 'success'
                
        except Exception as e:
            self.root.after(0, lambda: self._update_progress(0, self._t('status_error_generic', '❌ Errore: {error}').format(error=str(e))))
            self.root.after(0, lambda: self.status_label.configure(text=self._t('status_error_generic', '❌ Errore: {error}').format(error=str(e))))
            result_state = 'error'
        finally:
            self.operation_in_progress = False  # Ferma il monitor thread
            try:
                self._batch_file_count = 0
                self._batch_file_index = 0
            except Exception:
                pass
            self.root.after(0, lambda: self.copy_btn.configure(state='normal'))
            self.root.after(0, lambda: self.move_btn.configure(state='normal'))
            self.root.after(0, lambda: self.cancel_btn.configure(state='disabled'))

            # Se l'app è stata lanciata dal menu contestuale:
            # - in caso di SUCCESSO chiudi automaticamente dopo pochi secondi (report leggibile)
            # - in caso di ERRORE/ANNULLATA non chiudere (così puoi studiare il motivo)
            if self.launched_from_context_menu and operation_type in ('copy', 'move'):
                try:
                    if self._auto_close_after_id is not None:
                        self.root.after_cancel(self._auto_close_after_id)
                except Exception:
                    pass

                if result_state == 'success':
                    delay_ms = 1800
                    try:
                        self._auto_close_after_id = self.root.after(delay_ms, self._on_closing)
                    except Exception:
                        self._auto_close_after_id = None
                else:
                    # Non auto-chiudere e non nascondere la UI di progress: lascia tutto visibile.
                    self._auto_close_after_id = None
            else:
                # Uso diretto: mantieni la progress UI visibile
                # self.root.after(3000, self._hide_progress_ui)  # Commentato: mantieni sempre visibile
                pass
    
    def _update_progress(self, percentage, text):
        """Aggiorna la label progress in modo thread-safe con velocità e ETA"""
        import time

        # Normalizza percentuale (mostra sempre intero)
        try:
            percentage = int(round(float(percentage)))
        except Exception:
            percentage = 0
        
        if percentage < 0:
            percentage = 0
        elif percentage > 100:
            percentage = 100

        # Se siamo in modalità batch (solo file selezionati), calcola percentuale cumulativa su byte totali
        try:
            batch_total = int(getattr(self, '_batch_total_size', 0) or 0)
            if batch_total > 0:
                batch_completed = int(getattr(self, '_batch_completed_bytes', 0) or 0)
                engine_processed = 0
                try:
                    engine_processed = int(getattr(self.file_engine, 'processed_size', 0) or 0)
                except Exception:
                    engine_processed = 0
                batch_processed = batch_completed + engine_processed
                if batch_processed < 0:
                    batch_processed = 0
                if batch_processed > batch_total:
                    batch_processed = batch_total
                percentage = int(round((batch_processed / batch_total) * 100)) if batch_total > 0 else 0
                if percentage < 0:
                    percentage = 0
                elif percentage > 100:
                    percentage = 100
        except Exception:
            pass

        try:
            if hasattr(self, 'progress_bar') and self.progress_bar is not None:
                self.progress_bar.set(percentage / 100.0)
        except Exception:
            pass

        # Calcola velocità e ETA
        if not hasattr(self, '_progress_start_time') or self._progress_start_time is None:
            self._progress_start_time = time.time()
        
        current_time = time.time()
        elapsed = current_time - self._progress_start_time
        speed_mb = 0
        eta_str = "--:--"
        file_name = "..."
        
        try:
            # Ottieni informazioni dal file_engine
            if hasattr(self.file_engine, 'current_file') and self.file_engine.current_file:
                file_name = self.file_engine.current_file

            # Per batch: velocità/ETA su totale batch; altrimenti su file/cartella corrente
            batch_total = int(getattr(self, '_batch_total_size', 0) or 0)
            if elapsed > 0:
                if batch_total > 0:
                    batch_completed = int(getattr(self, '_batch_completed_bytes', 0) or 0)
                    processed = batch_completed + int(getattr(self.file_engine, 'processed_size', 0) or 0)
                    total = batch_total
                else:
                    processed = int(getattr(self.file_engine, 'processed_size', 0) or 0)
                    total = int(getattr(self.file_engine, 'total_size', 0) or 0)

                # Calcola velocità in MB/s
                speed_mb = (processed / (1024 * 1024)) / elapsed if elapsed > 0 else 0

                # Calcola ETA
                if speed_mb > 0 and total > processed:
                    remaining_mb = (total - processed) / (1024 * 1024)
                    eta_seconds = remaining_mb / speed_mb
                    minutes, seconds = divmod(int(eta_seconds), 60)
                    eta_str = f"{minutes:02d}:{seconds:02d}"
        except Exception:
            pass

        # A fine operazione: mostra tempo totale impiegato (T) invece di ETA residuo
        def _format_elapsed(seconds_total: float) -> str:
            try:
                seconds_total = int(seconds_total)
            except Exception:
                seconds_total = 0
            if seconds_total < 0:
                seconds_total = 0
            h, rem = divmod(seconds_total, 3600)
            m, s = divmod(rem, 60)
            if h > 0:
                return f"{h:02d}:{m:02d}:{s:02d}"
            return f"{m:02d}:{s:02d}"

        if percentage >= 100:
            eta_str = _format_elapsed(elapsed)
            eta_label = self._t('progress_elapsed_label', 'T')
        else:
            eta_label = self._t('progress_eta_label', 'ETA')

        # Testo label: <nome file> | <percentuale> | <MB/s> | ETA
        safe_text = (text or "").strip()
        # Se non passano un testo esplicito, mostra almeno il file corrente
        if not safe_text:
            safe_text = file_name

        status_text = f"{safe_text} | {percentage}% |  {speed_mb:.1f} MB/s | {eta_label}: {eta_str}"
        try:
            self._set_progress_text(status_text, percentage)
        except Exception:
            pass

    def _ask_overwrite_conflict(self, source: str, destination: str) -> str:
        """Mostra popup di conflitto sovrascrittura sul main thread e blocca il worker fino alla risposta.
        Restituisce 'overwrite', 'skip', 'overwrite_all' o 'skip_all'."""
        import threading as _threading
        event = _threading.Event()
        result = ['skip']  # default sicuro

        def _show_popup():
            try:
                popup = ctk.CTkToplevel(self.root)
                popup.title(self._t('conflict_title', 'File già esistente'))
                popup.resizable(False, False)
                popup.grab_set()
                popup.lift()
                popup.focus_force()

                # Centra il popup sulla finestra principale
                try:
                    px = self.root.winfo_x() + self.root.winfo_width() // 2 - 280
                    py = self.root.winfo_y() + self.root.winfo_height() // 2 - 100
                    popup.geometry(f"560x200+{px}+{py}")
                except Exception:
                    popup.geometry("560x200")

                src_name = source if len(source) <= 60 else f"...{source[-57:]}"
                dst_name = destination if len(destination) <= 60 else f"...{destination[-57:]}"

                ctk.CTkLabel(popup,
                             text=self._t('conflict_msg',
                                          'Il file di destinazione esiste già.\n'
                                          'Sorgente: {src}\nDestinazione: {dst}').format(
                                 src=src_name, dst=dst_name),
                             justify='left', wraplength=520).pack(padx=16, pady=(16, 8))

                btn_frame = ctk.CTkFrame(popup, fg_color='transparent')
                btn_frame.pack(pady=(4, 16))

                def _choose(choice):
                    result[0] = choice
                    popup.grab_release()
                    popup.destroy()
                    event.set()

                ctk.CTkButton(btn_frame, width=120,
                              text=self._t('conflict_overwrite', 'Sovrascrivi'),
                              command=lambda: _choose('overwrite')).grid(row=0, column=0, padx=6)
                ctk.CTkButton(btn_frame, width=120,
                              text=self._t('conflict_skip', 'Salta'),
                              command=lambda: _choose('skip')).grid(row=0, column=1, padx=6)
                ctk.CTkButton(btn_frame, width=140,
                              text=self._t('conflict_overwrite_all', 'Sovrascrivi tutti'),
                              command=lambda: _choose('overwrite_all')).grid(row=0, column=2, padx=6)
                ctk.CTkButton(btn_frame, width=120,
                              text=self._t('conflict_skip_all', 'Salta tutti'),
                              command=lambda: _choose('skip_all')).grid(row=0, column=3, padx=6)

                # Se il popup viene chiuso con la X → skip
                popup.protocol("WM_DELETE_WINDOW", lambda: _choose('skip'))
            except Exception:
                result[0] = 'skip'
                event.set()

        try:
            self.root.after(0, _show_popup)
        except Exception:
            return 'skip'

        event.wait(timeout=300)  # timeout di sicurezza 5 minuti
        return result[0]

    def cancel_operation(self):
        """Annulla operazione in corso"""
        self.cancel_requested = True
        self.file_engine.cancel()
    
    def _register_menu(self):
        """Registra menu contestuale"""
        try:
            self.context_manager.register()
            self.menu_status_label.configure(text=self._t('menu_registered_ok', "✅ Menu registrato con successo! Prova tasto destro su una cartella."))
            self._schedule_menu_status_restore()
        except Exception as e:
            self.menu_status_label.configure(text=self._t('menu_error_register', '❌ Errore registrazione: {error}').format(error=str(e)))
            self._schedule_menu_status_restore()
    
    def _unregister_menu(self):
        """Rimuove menu contestuale"""
        try:
            self.context_manager.unregister()
            self.menu_status_label.configure(text=self._t('menu_removed_ok', "✅ Menu rimosso con successo!"))
            self._schedule_menu_status_restore()
        except Exception as e:
            self.menu_status_label.configure(text=self._t('menu_error_unregister', '❌ Errore rimozione: {error}').format(error=str(e)))
            self._schedule_menu_status_restore()

    def _schedule_menu_status_restore(self, delay_ms: int = 2000):
        """Ripristina (dopo delay) lo stato/testo base del tab Menu Contestuale."""
        try:
            if self._menu_status_restore_after_id is not None:
                self.root.after_cancel(self._menu_status_restore_after_id)
        except Exception:
            pass

        def _restore():
            try:
                self.check_menu_status()
            except Exception:
                try:
                    self.menu_status_label.configure(text=self._t('menu_status_unknown', "Stato: Sconosciuto"))
                except Exception:
                    pass

        try:
            self._menu_status_restore_after_id = self.root.after(delay_ms, _restore)
        except Exception:
            self._menu_status_restore_after_id = None
    
    def check_menu_status(self):
        """Verifica stato menu"""
        try:
            status = self.context_manager.get_status()
            # Traduci il testo dello status dalle stringhe in italiano alle chiavi i18n
            translated_status = self._translate_registry_status(status)
            self.menu_status_label.configure(text=f"{self._t('menu_status_prefix', 'Stato Menu')}:\n{translated_status}")
        except Exception as e:
            self.menu_status_label.configure(text=self._t('menu_error_check_status', '❌ Errore verifica stato: {error}').format(error=str(e)))
    
    def _translate_registry_status(self, status_text):
        """Traduce le stringhe dello stato del registro dalle stringhe in italiano alle chiavi i18n"""
        # Mappa di traduzione: (stringa italiana) -> (chiave i18n)
        translations = {
            "🔍 Stato Menu Contestuale": self._t('registry_status_title', '🔍 Stato Menu Contestuale'),
            "✅ File → 📋 Copia [Avanzata]": self._t('registry_file_copy_ok', '✅ File → 📋 Copia [Avanzata]'),
            "❌ File → Copia [Avanzata] (non trovata)": self._t('registry_file_copy_missing', '❌ File → Copia [Avanzata] (non trovata)'),
            "✅ File → ✂️ Sposta [Avanzata]": self._t('registry_file_move_ok', '✅ File → ✂️ Sposta [Avanzata]'),
            "❌ File → Sposta [Avanzata] (non trovata)": self._t('registry_file_move_missing', '❌ File → Sposta [Avanzata] (non trovata)'),
            "❌ File → Menu non registrato": self._t('registry_file_not_registered', '❌ File → Menu non registrato'),
            "✅ Cartella → 📋 Copia [Avanzata]": self._t('registry_folder_copy_ok', '✅ Cartella → 📋 Copia [Avanzata]'),
            "❌ Cartella → Copia [Avanzata] (non trovata)": self._t('registry_folder_copy_missing', '❌ Cartella → Copia [Avanzata] (non trovata)'),
            "✅ Cartella → ✂️ Sposta [Avanzata]": self._t('registry_folder_move_ok', '✅ Cartella → ✂️ Sposta [Avanzata]'),
            "❌ Cartella → Sposta [Avanzata] (non trovata)": self._t('registry_folder_move_missing', '❌ Cartella → Sposta [Avanzata] (non trovata)'),
            "❌ Cartella → Menu non registrato": self._t('registry_folder_not_registered', '❌ Cartella → Menu non registrato'),
            "✅ Unità → 📋 Copia [Avanzata]": self._t('registry_drive_copy_ok', '✅ Unità → 📋 Copia [Avanzata]'),
            "❌ Unità → Copia [Avanzata] (non trovata)": self._t('registry_drive_copy_missing', '❌ Unità → Copia [Avanzata] (non trovata)'),
            "✅ Unità → ✂️ Sposta [Avanzata]": self._t('registry_drive_move_ok', '✅ Unità → ✂️ Sposta [Avanzata]'),
            "❌ Unità → Sposta [Avanzata] (non trovata)": self._t('registry_drive_move_missing', '❌ Unità → Sposta [Avanzata] (non trovata)'),
            "❌ Unità → Menu non registrato": self._t('registry_drive_not_registered', '❌ Unità → Menu non registrato'),
            "Errore nel leggere lo stato": self._t('registry_error_reading', 'Errore nel leggere lo stato'),
        }
        
        # Sostituisci le stringhe in italiano con le versioni tradotte
        result = status_text
        for italian_text, translated_text in translations.items():
            result = result.replace(italian_text, translated_text)
        
        return result
    
    def toggle_always_on_top(self):
        """Attiva/disattiva always on top"""
        is_on_top = self.always_on_top_var.get()
        self.config_manager.set('always_on_top', is_on_top)
        self.root.attributes('-topmost', is_on_top)
    
    def restore_window_state(self):
        """Ripristina stato finestra"""
        # Dimensione minima ragionevole (non troppo grande!)
        min_width = 600
        min_height = 500
        
        # Dimensione di default se non c'è config salvato (usa quelle dal config.json)
        default_width = 900
        default_height = 720
        
        size = self.config_manager.get('window_size', {'width': default_width, 'height': default_height})
        window_width = size.get('width', default_width)
        window_height = size.get('height', default_height)
        
        # Imposta dimensione minima finestra (impedisce resize sotto minimo)
        self.root.minsize(min_width, min_height)
        
        # Imposta solo le dimensioni inizialmente (posizione sarà impostata da _center_window)
        self.root.geometry(f"{window_width}x{window_height}")
        
        # Salva le dimensioni per _center_window (evita che update_idletasks le modifichi)
        self._desired_width = window_width
        self._desired_height = window_height
        
        # Il resize sarà bloccato da finalize_window() dopo il caricamento
        self._lock_window_size = False
        
        on_top = self.config_manager.get('always_on_top', False)
        self.root.attributes('-topmost', on_top)
        self.always_on_top_var.set(on_top)
    
    def _center_window(self):
        """Centra la finestra sullo schermo dove si trova il mouse (multi-monitor)"""
        # Usa le dimensioni desiderate (salvate in restore_window_state)
        if hasattr(self, '_desired_width') and hasattr(self, '_desired_height'):
            window_width = self._desired_width
            window_height = self._desired_height
        else:
            # Fallback: calcola dimensioni necessarie
            self.root.update_idletasks()
            window_width = self.root.winfo_width()
            window_height = self.root.winfo_height()
        
        try:
            if sys.platform == 'win32':
                import ctypes
                from ctypes import wintypes

                class POINT(ctypes.Structure):
                    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]

                class RECT(ctypes.Structure):
                    _fields_ = [
                        ("left", wintypes.LONG),
                        ("top", wintypes.LONG),
                        ("right", wintypes.LONG),
                        ("bottom", wintypes.LONG),
                    ]

                class MONITORINFO(ctypes.Structure):
                    _fields_ = [
                        ("cbSize", wintypes.DWORD),
                        ("rcMonitor", RECT),
                        ("rcWork", RECT),
                        ("dwFlags", wintypes.DWORD),
                    ]

                user32 = ctypes.windll.user32

                pt = POINT()
                user32.GetCursorPos(ctypes.byref(pt))
                MONITOR_DEFAULTTONEAREST = 2
                hmon = user32.MonitorFromPoint(pt, MONITOR_DEFAULTTONEAREST)

                mi = MONITORINFO()
                mi.cbSize = ctypes.sizeof(MONITORINFO)
                user32.GetMonitorInfoW(hmon, ctypes.byref(mi))

                work = mi.rcWork
                screen_x = int(work.left)
                screen_y = int(work.top)
                screen_width = int(work.right - work.left)
                screen_height = int(work.bottom - work.top)
            else:
                screen_x = 0
                screen_y = 0
                screen_width = self.root.winfo_screenwidth()
                screen_height = self.root.winfo_screenheight()

            x = screen_x + (screen_width - window_width) // 2
            y = screen_y + int((screen_height - window_height) * 0.4)
        except Exception:
            # Fallback: centra sullo schermo primario
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            x = (screen_width - window_width) // 2
            y = int((screen_height - window_height) * 0.4)
        
        # Applica posizione centrata
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
    
    def _on_closing(self):
        """Salva stato e chiude l'app"""
        # Salva dimensione finestra corrente (resize manuale abilitato)
        try:
            self.root.update_idletasks()
            # Usa geometry() per ottenere dimensioni reali
            geometry = self.root.geometry()
            # Formato: "WIDTHxHEIGHT+X+Y"
            size_part = geometry.split('+')[0]
            width, height = map(int, size_part.split('x'))
        except Exception:
            # Fallback: usa winfo
            try:
                width = self.root.winfo_width()
                height = self.root.winfo_height()
            except Exception:
                width = 900
                height = 720
        
        # Se i valori sono invalidi (es: 1), usa i valori da config precedente
        if width < 600 or height < 500:
            current_size = self.config_manager.get('window_size', {})
            width = current_size.get('width', 900)
            height = current_size.get('height', 720)
        
        self.config_manager.set('window_size', {
            'width': width,
            'height': height
        })
        
        # window_position non viene più salvata - la finestra si posiziona dinamicamente all'avvio
        self.config_manager.set('buffer_size', int(self.buffer_size.get()))
        self.config_manager.set('threads', int(self.threads.get()))
        # Se il checkbox è disabilitato per override (sorgente/dest sul RamDrive),
        # salva la preferenza reale dell'utente, non il False forzato.
        ramdrive_to_save = self._ramdrive_user_pref if self._ramdrive_user_pref is not None else self.ramdrive_enabled.get()
        self.config_manager.set('ramdrive', ramdrive_to_save)
        self.config_manager.set('overwrite', self.overwrite_enabled.get())
        self.config_manager.set('delete_source', self.delete_source_enabled.get())
        
        self.root.destroy()

    def _start_update_check(self):
        """Start async update check in background"""
        try:
            config_path = str(self.config_manager.config_path)
            check_for_update_async(
                config_path,
                on_update_available=self._on_update_available,
                on_error=self._on_update_error
            )
        except Exception as e:
            # Silently fail if update check module not available
            pass

    def _on_update_available(self, version, release_notes):
        """Called when update is available"""
        try:
            def show_update_dialog():
                title = self._t('update_available_title', 'Aggiornamento disponibile')
                message = self._t('update_available_msg', 'Versione {version} disponibile.\n\nNote di rilascio:\n{notes}\n\nDesideri aggiornare adesso?').format(version=version, notes=release_notes)
                
                result = messagebox.askyesno(title, message)
                if result:
                    # Start download and installation (blocking)
                    from src.update_checker import check_and_update
                    try:
                        self._show_update_progress()
                        
                        # Define callback to close app cleanly after launcher script is started
                        def close_app_for_update():
                            """Close the application and exit process to free exe lock"""
                            try:
                                self.root.destroy()
                            except:
                                pass
                            # Force hard exit so the .exe file lock is released
                            # The launcher .cmd is already running and will wait for this PID to disappear
                            import time
                            time.sleep(0.2)
                            os._exit(0)
                        
                        success, msg = check_and_update(
                            str(self.config_manager.config_path),
                            on_download_start=self._on_download_start,
                            on_download_complete=self._on_download_complete,
                            on_close_app=close_app_for_update
                        )
                        # If we reach here, on_close_app was NOT called (error path)
                        if not success:
                            messagebox.showerror(self._t('error_title', 'Errore'), self._t('update_failed', 'Aggiornamento fallito: {msg}').format(msg=msg))
                    except Exception as e:
                        messagebox.showerror(self._t('error_title', 'Errore'), self._t('update_error', "Errore durante l'aggiornamento: {error}").format(error=str(e)))
            
            # Schedule in main thread
            self.root.after(100, show_update_dialog)
        except Exception as e:
            pass

    def _on_update_error(self, error_msg):
        """Called when update check fails"""
        # Silently ignore errors to avoid bothering the user
        pass

    def _show_update_progress(self):
        """Show progress dialog while downloading update"""
        pass  # Can be enhanced with actual progress bar

    def _on_download_start(self):
        """Called when download starts"""
        try:
            self.status_label.configure(text=self._t('downloading_update', 'Download aggiornamento...'))
        except:
            pass

    def _on_download_complete(self, success):
        """Called when download completes"""
        if success:
            try:
                self.status_label.configure(text=self._t('update_ready', 'Aggiornamento pronto'))
            except:
                pass

    def _manual_check_updates(self):
        """Manual check for updates - called from button"""
        try:
            # Disable button while checking
            self.check_updates_btn.configure(state='disabled')
            self.check_updates_btn.configure(text=self._t('checking_updates', '⏳ Controllo in corso...'))
            self.root.update()
            
            from src.update_checker import get_latest_release_info, compare_versions, get_local_version
            
            local_version = get_local_version(str(self.config_manager.config_path))
            release_info = get_latest_release_info()
            
            if not release_info:
                messagebox.showwarning(
                    self._t('update_check_title', 'Controllo Aggiornamenti'),
                    self._t('update_check_failed', 'Impossibile verificare gli aggiornamenti. Verifica la connessione internet.')
                )
                self.check_updates_btn.configure(state='normal')
                self.check_updates_btn.configure(text=self._t('btn_check_updates', '🚀 Controlla Aggiornamenti'))
                return
            
            remote_version = release_info['version']
            cmp_result = compare_versions(local_version, remote_version)
            
            if cmp_result == 0:
                messagebox.showinfo(
                    self._t('update_check_title', 'Controllo Aggiornamenti'),
                    self._t('already_latest', 'Stai già usando la versione più recente (v{version})').format(version=local_version)
                )
            elif cmp_result > 0:
                messagebox.showinfo(
                    self._t('update_check_title', 'Controllo Aggiornamenti'),
                    self._t('version_newer_local', 'Stai usando una versione più recente (v{local}) rispetto a GitHub (v{remote})').format(local=local_version, remote=remote_version)
                )
            else:
                # Update available
                self._on_update_available(remote_version, release_info.get('release_notes', ''))
        
        except Exception as e:
            messagebox.showerror(
                self._t('error_title', 'Errore'),
                self._t('update_check_error', 'Errore durante il controllo degli aggiornamenti: {error}').format(error=str(e))
            )
        finally:
            self.check_updates_btn.configure(state='normal')
            self.check_updates_btn.configure(text=self._t('btn_check_updates', '🚀 Controlla Aggiornamenti'))


def main() -> int:
    """Entry point della GUI.

    Supporta anche modalità non-interattiva per installer:
    - --register-context-menu [--admin]
    - --unregister-context-menu [--admin]
    """
    argv = list(sys.argv or [])

    # Modalità installer: registra/rimuove menu e termina senza avviare Tk
    try:
        if '--register-context-menu' in argv or '--unregister-context-menu' in argv:
            try:
                project_root = str(Path(__file__).resolve().parent.parent)
                if project_root not in sys.path:
                    sys.path.insert(0, project_root)
            except Exception:
                pass

            from registry.context_menu import ContextMenuRegistrar

            use_admin = '--admin' in argv
            registrar = ContextMenuRegistrar(use_admin=use_admin)

            if '--register-context-menu' in argv:
                ok = bool(registrar.register())
            else:
                ok = bool(registrar.unregister())

            return 0 if ok else 1
    except Exception:
        return 1

    # Controllo single-instance: se richiesto e c'è già un'istanza attiva,
    # invia i file via IPC (file condiviso + Named Pipe) e termina silenziosamente.
    if '--single-instance' in argv:
        if not _check_single_instance():
            # C'è già un'istanza in esecuzione: invia file via IPC
            try:
                sources_ipc, op_ipc, _ = _parse_launch_args(argv)
                if sources_ipc and op_ipc:
                    for src in sources_ipc:
                        _ipc_send_file(src, op_ipc)
            except Exception:
                pass
            return 0
        else:
            # Siamo l'istanza principale: pulisci eventuali file pendenti residui
            try:
                _IPC_DIR.mkdir(parents=True, exist_ok=True)
                if _IPC_PENDING_FILE.exists():
                    _IPC_PENDING_FILE.write_text('', encoding='utf-8')
            except Exception:
                pass

    sources, operation_type, from_context_menu = _parse_launch_args(argv)

    # Blocca selezioni su oggetti shell virtuali (Cestino / Questo PC / Rete, ecc.)
    # così non parte accidentalmente e, soprattutto, evita anche il prompt UAC.
    try:
        if from_context_menu and operation_type in ('copy', 'move'):
            bad = [s for s in (sources or []) if _is_shell_namespace_path(s)]
            if bad:
                return 1
    except Exception:
        pass

    # Se avviata dal menu contestuale, auto-eleva (UAC) per avere gli stessi permessi
    # dell'avvio manuale come amministratore, senza passare da PowerShell.
    try:
        if from_context_menu and operation_type in ('copy', 'move') and sys.platform == 'win32':
            if not _is_running_as_admin():
                if _relaunch_elevated(argv):
                    return 0
    except Exception:
        pass

    # Avvio manuale: auto-elevazione opzionale (da impostazione), con guard anti-loop.
    try:
        if (not from_context_menu) and sys.platform == 'win32':
            if ('--no-auto-elevate' not in argv) and (not _is_running_as_admin()):
                enabled = False
                try:
                    enabled = bool(ConfigManager().get('auto_elevate_on_start', False))
                except Exception:
                    enabled = False

                if enabled:
                    argv2 = list(argv)
                    argv2.append('--no-auto-elevate')
                    if _relaunch_elevated(argv2):
                        return 0
    except Exception:
        pass

    # Abilita drag and drop per app con privilegi admin (PRIMA di creare la root)
    if HAS_DND and is_admin():
        enable_drag_drop_for_elevated()

    # Crea root con supporto DnD se disponibile
    root = CTkDnD()
    
    app = AdvancedFileMoverCustomTkinter(
        root,
        initial_sources=sources,
        operation_type=operation_type,
        launched_from_context_menu=from_context_menu,
    )
    
    # Avvia listener IPC per ricevere file da altre istanze (context menu)
    _ipc_start_listener(app)
    
    root.minsize(602, 720)  # Dimensione minima finestra
    root.mainloop()
    return 0


def _parse_launch_args(argv):
    # Supporta:
    # - Avvio manuale: nessun argomento
    # - Vecchio formato: <path> <copy|move>
    # - Nuovo formato (menu contestuale): --from-context-menu <copy|move> <paths...>
    import re

    args = list(argv[1:]) if argv else []
    
    def _split_packed_arg(a: str):
        """Alcuni comandi del menu contestuale possono passare più path in un unico argomento.

        Esempio: '"C:\\A\\file 1.txt" "D:\\B\\file2.txt"'
        """
        if not isinstance(a, str) or not a:
            return []

        # Se contiene più stringhe quotate, estrai quelle.
        if '"' in a:
            parts = re.findall(r'"([^"]+)"', a)
            if len(parts) >= 1:
                return [p for p in parts if p]

        return [a]

    def _reconstruct_split_paths(tokens):
        """Ricostruisce path spezzati in più argv quando contengono spazi.

        Explorer/registry può passare una cartella con spazi come:
        ['U:\\KIT\\HDD', 'Partition\\BOOTABLE']
        Qui ricostruiamo provando join consecutivi e validando con os.path.exists().
        """
        import os

        out = []
        i = 0
        n = len(tokens)
        while i < n:
            best = None
            best_j = None

            # prova fino a 12 token per evitare loop lunghi in casi strani
            max_j = min(n, i + 12)
            for j in range(i + 1, max_j + 1):
                candidate = ' '.join(tokens[i:j])
                try:
                    if os.path.exists(long_path(candidate)):
                        best = candidate
                        best_j = j
                except Exception:
                    pass

                # Se abbiamo già un match e stiamo solo aggiungendo token che rendono il path
                # palesemente impossibile (es: iniziano con '-') possiamo interrompere.
                try:
                    if j < n and isinstance(tokens[j], str) and tokens[j].startswith('-'):
                        break
                except Exception:
                    pass

            if best is not None:
                out.append(best)
                i = best_j
            else:
                out.append(tokens[i])
                i += 1

        return out

    from_context_menu = False
    single_instance = '--single-instance' in args  # Evita multiple istanze dal context menu
    operation_type = None
    sources_raw = []

    if '--from-context-menu' in args:
        from_context_menu = True
        idx = args.index('--from-context-menu')

        # Accetta argomenti anche prima del flag (robustezza)
        pre = args[:idx]
        post = args[idx + 1 :]

        if post and post[0] in ('copy', 'move'):
            operation_type = post[0]
            sources_raw = pre + post[1:]
        else:
            # Flag presente ma formato inatteso
            sources_raw = pre + post
    else:
        # Vecchio formato: <path> <copy|move>
        if len(args) >= 2 and args[-1] in ('copy', 'move'):
            operation_type = args[-1]
            sources_raw = args[:-1]
        else:
            sources_raw = args

    # Espandi eventuali argomenti “impacchettati”
    expanded = []
    for a in sources_raw:
        try:
            expanded.extend(_split_packed_arg(a))
        except Exception:
            if a:
                expanded.append(a)

    # Filtra opzioni/flag e pulisci
    sources = []
    for a in expanded:
        if not a:
            continue
        if isinstance(a, str) and a.startswith('-'):
            continue
        # Normalizza eventuali quote residue
        if isinstance(a, str):
            a = a.strip().strip('"')
        if a:
            sources.append(a)

    # Ricostruisci eventuali path spezzati (spazi) validando su disco
    try:
        sources = _reconstruct_split_paths(sources)
    except Exception:
        pass

    # Heuristica: se arrivano sorgenti + op, è avvio dal menu contestuale
    if sources and operation_type:
        from_context_menu = True
    
    return sources, operation_type, from_context_menu


def _is_shell_namespace_path(path_str: str) -> bool:
    """True se il path è un oggetto shell virtuale (non filesystem).

    Esempi: '::{CLSID}' / '::{CLSID}\\...' / 'shell:RecycleBinFolder'.
    """
    try:
        s = str(path_str or '').strip()
    except Exception:
        return False

    if not s:
        return False

    sl = s.lower()
    if sl.startswith('shell:'):
        return True
    if sl.startswith('::') or '::{' in sl:
        return True

    return False


def _detect_system_language() -> str:
    """Rileva la lingua di sistema e la mappa a una delle lingue supportate."""
    try:
        import locale
        # Prova il locale di sistema (es. 'it_IT', 'en_US', 'fr_FR', 'de_DE', 'es_ES')
        lang_code = locale.getdefaultlocale()[0] or ''
        if not lang_code:
            # Fallback Windows: usa GetUserDefaultUILanguage
            try:
                import ctypes
                windll = ctypes.windll.kernel32
                lang_id = windll.GetUserDefaultUILanguage()
                # Mappa language ID → codice ISO
                _WIN_LANG_MAP = {
                    0x0410: 'it', 0x0810: 'it',  # it-IT, it-CH
                    0x0409: 'en', 0x0809: 'en', 0x0C09: 'en', 0x1009: 'en', 0x1409: 'en',  # en-*
                    0x040C: 'fr', 0x080C: 'fr', 0x0C0C: 'fr', 0x100C: 'fr',  # fr-*
                    0x0407: 'de', 0x0807: 'de', 0x0C07: 'de',  # de-*
                    0x040A: 'es', 0x080A: 'es', 0x0C0A: 'es',  # es-*
                }
                return _WIN_LANG_MAP.get(lang_id, 'en')
            except Exception:
                pass
        # Estrae le prime 2 lettere (es. 'it' da 'it_IT')
        short = lang_code[:2].lower()
        if short in ('it', 'en', 'fr', 'de', 'es'):
            return short
    except Exception:
        pass
    return 'en'  # fallback globale: inglese


def _get_config_language_quick() -> str:
    """Legge la lingua dalla config utente se esiste, senza crearla."""
    try:
        base = Path(os.environ.get('LOCALAPPDATA', str(Path.home() / 'AppData' / 'Local')))
        cfg = base / 'AdvancedFileMover' / 'config.json'
        if cfg.exists():
            with open(cfg, 'r', encoding='utf-8') as f:
                data = json.load(f) or {}
            lang = str(data.get('language', '') or '').lower()
            if lang in ('it', 'en', 'fr', 'de', 'es'):
                return lang
    except Exception:
        pass
    return _detect_system_language()


def _load_translations_for_main(language_code: str) -> dict:
    try:
        code = str(language_code or 'it').strip().lower()
        if code not in ('it', 'en', 'fr', 'de', 'es'):
            code = 'it'

        candidates = []

        # 1) Bundle onefile (sys._MEIPASS)
        try:
            if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
                candidates.append(Path(getattr(sys, '_MEIPASS')) / 'i18n' / f'{code}.json')
        except Exception:
            pass

        # 2) Vicino all'EXE / dist
        try:
            if getattr(sys, 'frozen', False):
                base_dir = Path(sys.executable).parent
            else:
                base_dir = Path(__file__).parent.parent
            candidates.append(base_dir / 'i18n' / f'{code}.json')
        except Exception:
            pass

        # 3) Dev (repo)
        candidates.append(Path(__file__).parent.parent / 'i18n' / f'{code}.json')

        for p in candidates:
            try:
                if p.exists():
                    with open(p, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    return data if isinstance(data, dict) else {}
            except Exception:
                continue
    except Exception:
        pass

    return {}


def _t_main(translations: dict, key: str, default: str) -> str:
    try:
        if isinstance(translations, dict):
            v = translations.get(key)
            if isinstance(v, str) and v:
                return v
    except Exception:
        pass
    return default


def _win_warn(title: str, text: str):
    try:
        if sys.platform == 'win32':
            import ctypes

            ctypes.windll.user32.MessageBoxW(None, str(text), str(title), 0x00000030)
        else:
            print(f"{title}: {text}")
    except Exception:
        pass


def _is_running_as_admin() -> bool:
    try:
        import ctypes

        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


# Variabile globale per mantenere il mutex della single-instance
_GLOBAL_MUTEX_HANDLE = None


def _check_single_instance() -> bool:
    """Verifica se esiste già un'istanza dell'applicazione.
    
    Ritorna True se questa è l'unica istanza, False se ce n'è già una attiva.
    Usa un mutex di sistema Windows per la sincronizzazione.
    """
    global _GLOBAL_MUTEX_HANDLE
    
    if sys.platform != 'win32':
        return True
    
    try:
        import ctypes
        from ctypes import wintypes
        
        # Nome univoco del mutex per questa applicazione
        MUTEX_NAME = 'Global\\AdvancedFileMover_SingleInstance_Mutex'
        
        # Funzioni Win32 API
        kernel32 = ctypes.windll.kernel32
        
        # CreateMutexW
        kernel32.CreateMutexW.argtypes = [
            wintypes.LPVOID,   # lpMutexAttributes
            wintypes.BOOL,     # bInitialOwner
            wintypes.LPCWSTR   # lpName
        ]
        kernel32.CreateMutexW.restype = wintypes.HANDLE
        
        # GetLastError
        kernel32.GetLastError.argtypes = []
        kernel32.GetLastError.restype = wintypes.DWORD
        
        # Crea il mutex
        mutex_handle = kernel32.CreateMutexW(None, True, MUTEX_NAME)
        
        # ERROR_ALREADY_EXISTS = 183
        if kernel32.GetLastError() == 183:
            # Il mutex esiste già = altra istanza in esecuzione
            if mutex_handle:
                kernel32.CloseHandle(mutex_handle)
            return False
        
        # Questa è la prima istanza - SALVA il mutex_handle GLOBALMENTE
        # così il mutex rimane aperto fino alla terminazione del processo
        _GLOBAL_MUTEX_HANDLE = mutex_handle
        return True
        
    except Exception:
        # In caso di errore, permetti l'avvio
        return True


def _relaunch_elevated(argv) -> bool:
    """Rilancia l'app elevata (UAC) con gli stessi argomenti."""
    if sys.platform != 'win32':
        return False

    try:
        import ctypes

        if getattr(sys, 'frozen', False):
            target = sys.executable
            params = subprocess.list2cmdline(argv[1:])
        else:
            # In dev mode: rilancia con pythonw.exe per evitare console.
            python_exe = sys.executable
            pythonw = python_exe.replace('python.exe', 'pythonw.exe')
            if os.path.exists(pythonw):
                python_exe = pythonw

            script_path = str(Path(__file__).resolve())
            target = python_exe
            params = subprocess.list2cmdline([script_path] + argv[1:])

        # ShellExecuteW ritorna > 32 se ok
        rc = ctypes.windll.shell32.ShellExecuteW(None, 'runas', target, params, None, 1)
        return int(rc) > 32
    except Exception:
        return False


if __name__ == '__main__':
    raise SystemExit(main())
