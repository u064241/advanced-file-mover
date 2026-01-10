"""
Registrazione nel menu contestuale di Windows
"""
import sys
import os
import winreg
import subprocess
import argparse
from pathlib import Path


class ContextMenuRegistrar:
    """Gestisce registrazione nel menu contestuale di Windows"""
    
    # Percorso applicazione
    APP_DIR = Path(__file__).parent.parent
    APP_EXE = APP_DIR / "dist" / "AdvancedFileMoverPro.exe"  # Dopo PyInstaller
    LAUNCHER_PY = APP_DIR / "launcher.py"
    
    # Chiavi registro
    COPY_KEY_PATH = r"Software\Classes\*\shell\AdvancedFileMover_Copy"
    MOVE_KEY_PATH = r"Software\Classes\*\shell\AdvancedFileMover_Move"
    FOLDER_COPY_KEY = r"Software\Classes\Folder\shell\AdvancedFileMover_Copy"
    FOLDER_MOVE_KEY = r"Software\Classes\Folder\shell\AdvancedFileMover_Move"
    # Nota: "Folder" include anche elementi virtuali (This PC/Network/Recycle Bin ecc.).
    # Per i filesystem folder usare "Directory"; per le unità usare "Drive".
    RECYCLE_BIN_BASE = r"Software\Classes\CLSID\{645FF040-5081-101B-9F08-00AA002F954E}\shell"
    RECYCLE_BIN_KEY = RECYCLE_BIN_BASE + r"\Z_AdvancedFileMover"  # nome ordinato verso il basso senza essere l'ultimo assoluto
    LEGACY_RECYCLE_BIN_KEY = RECYCLE_BIN_BASE + r"\AdvancedFileMover"  # cleanup versioni precedenti
    
    def __init__(self, use_admin=False):
        """
        Inizializza registrar
        
        Args:
            use_admin: Se True, usa HKEY_LOCAL_MACHINE, altrimenti HKEY_CURRENT_USER
        """
        self.use_admin = use_admin
        self.root = winreg.HKEY_LOCAL_MACHINE if use_admin else winreg.HKEY_CURRENT_USER
        self.base_path = f"HKEY_{'LOCAL_MACHINE' if use_admin else 'CURRENT_USER'}"

    def _resolve_gui_exe(self) -> Path | None:
        """Restituisce il percorso dell'eseguibile GUI se disponibile.

        - In modalità PyInstaller (frozen): usa sys.executable (percorso reale installato).
        - In dev: preferisce dist/AdvancedFileMoverPro.exe se esiste.
        """
        try:
            if getattr(sys, 'frozen', False):
                exe = Path(sys.executable)
                if exe.exists():
                    return exe
        except Exception:
            pass

        try:
            dev_exe = self.APP_DIR / "dist" / "AdvancedFileMoverPro.exe"
            if dev_exe.exists():
                return dev_exe
        except Exception:
            pass

        return None

    def _resolve_exe_dir(self) -> Path:
        """Directory dove cercare Icon e file correlati all'app."""
        exe = self._resolve_gui_exe()
        if exe is not None:
            return exe.parent

        dist_dir = self.APP_DIR / "dist"
        if dist_dir.exists():
            return dist_dir

        return self.APP_DIR

    
    def register(self) -> bool:
        """Registra submenu stile PowerShell 7"""
        try:
            # Cleanup chiavi legacy troppo "ampie" (Folder include oggetti virtuali)
            self._unregister_submenu(r"Software\Classes\Folder\shell\AdvancedFileMover")

            # File - Submenu con MUIVerb
            self._register_powershell_submenu(
                r"Software\Classes\*\shell\AdvancedFileMover",
                "Advanced File Mover"
            )
            
            # Cartelle (solo filesystem) - Submenu con MUIVerb
            self._register_powershell_submenu(
                r"Software\Classes\Directory\shell\AdvancedFileMover",
                "Advanced File Mover"
            )

            # Unità (C:, D:, ...) - Submenu con MUIVerb
            self._register_powershell_submenu(
                r"Software\Classes\Drive\shell\AdvancedFileMover",
                "Advanced File Mover"
            )

            # Cleanup eventuali entry legacy sul Cestino (evita duplicati)
            self._remove_recycle_bin_entry()
            
            return True
        
        except Exception as e:
            return False
    
    def unregister(self) -> bool:
        """Rimuove submenu stile PowerShell 7"""
        try:
            self._unregister_submenu(r"Software\Classes\*\shell\AdvancedFileMover")
            # Rimuove sia le chiavi nuove (Directory/Drive) sia le legacy (Folder)
            self._unregister_submenu(r"Software\Classes\Directory\shell\AdvancedFileMover")
            self._unregister_submenu(r"Software\Classes\Drive\shell\AdvancedFileMover")
            self._unregister_submenu(r"Software\Classes\Folder\shell\AdvancedFileMover")
            self._remove_recycle_bin_entry()
            return True
        
        except Exception as e:
            return False
    
    def _register_powershell_submenu(self, parent_key_path: str, menu_label: str):
        """Registra un submenu stile PowerShell 7 usando MUIVerb + shell interno"""
        try:
            gui_exe = self._resolve_gui_exe()
            exe_dir = self._resolve_exe_dir()
            
            # Creare key principale del submenu
            parent_key = winreg.CreateKey(self.root, parent_key_path)
            
            # MUIVerb = Nome visualizzato nel menu (invece di default value)
            winreg.SetValueEx(parent_key, "MUIVerb", 0, winreg.REG_SZ, menu_label)

            # Mostra il menu solo con SHIFT + tasto destro (Extended menu)
            winreg.SetValueEx(parent_key, "Extended", 0, winreg.REG_SZ, "")
            
            # Assicura che la posizione resti di default (rimuove eventuale valore residuo)
            try:
                winreg.DeleteValue(parent_key, "Position")
            except FileNotFoundError:
                pass

            # Icona principale del submenu - usa super_icon.ico
            icon_path = exe_dir / "Icon" / "super_icon.ico"
            if not icon_path.exists():
                # Fallback se non trovato in dist/Icon (dev mode)
                icon_path = self.APP_DIR / "icon" / "super_icon.ico"
            
            if icon_path.exists():
                winreg.SetValueEx(parent_key, "Icon", 0, winreg.REG_SZ, str(icon_path.resolve()))
            
            # SubCommands = "" indica che le sub-voci sono in \\shell\\
            winreg.SetValueEx(parent_key, "SubCommands", 0, winreg.REG_SZ, "")
            
            # Creare shell subkey per le voci cascata
            shell_key = winreg.CreateKey(parent_key, "shell")
            
            # Sub-voce 1: Copia (NO emoji nel MUIVerb, l'icona verrà dalle .ico)
            self._register_powershell_subcommand(shell_key, "Copy", "Copia [Avanzata]", "copy", exe_dir)
            
            # Sub-voce 2: Sposta (NO emoji nel MUIVerb, l'icona verrà dalle .ico)
            self._register_powershell_subcommand(shell_key, "Move", "Sposta [Avanzata]", "move", exe_dir)
            
            winreg.CloseKey(shell_key)
            winreg.CloseKey(parent_key)
        
        except Exception as e:
            print(f"Errore durante registrazione submenu {menu_label}: {e}")
            raise

    def _remove_recycle_bin_entry(self):
        """Rimuove l'entry dal CLSID del Cestino."""
        try:
            for recycle_key_path in (self.RECYCLE_BIN_KEY, self.LEGACY_RECYCLE_BIN_KEY):
                try:
                    winreg.DeleteKey(self.root, recycle_key_path + "\\command")
                except FileNotFoundError:
                    pass
                try:
                    winreg.DeleteKey(self.root, recycle_key_path)
                except FileNotFoundError:
                    pass
        except FileNotFoundError:
            pass
        except Exception:
            pass
    
    def _register_powershell_subcommand(self, shell_key, sub_name: str, label: str, operation: str, exe_dir):
        """Registra una sub-voce nel submenu PowerShell-style"""
        try:
            sub_key = winreg.CreateKey(shell_key, sub_name)
            
            # MUIVerb per il nome visualizzato
            winreg.SetValueEx(sub_key, "MUIVerb", 0, winreg.REG_SZ, label)

            # Abilita multi-selezione (usa %V nel command)
            try:
                winreg.SetValueEx(sub_key, "MultiSelectModel", 0, winreg.REG_SZ, "Player")
            except Exception:
                pass
            
            # Icone sulle sub-voci (come PowerShell 7)
            if operation == 'copy':
                icon_path = exe_dir / "Icon" / "copy_icon.ico"
            else:
                icon_path = exe_dir / "Icon" / "move_icon.ico"
            
            if not icon_path.exists():
                # Fallback se non trovato in dist/Icon (dev mode)
                icon_path = self.APP_DIR / "icon" / ("copy_icon.ico" if operation == 'copy' else "move_icon.ico")
            
            winreg.SetValueEx(sub_key, "Icon", 0, winreg.REG_SZ, str(icon_path.resolve()))
            
            # Comando per la sub-voce
            command_key = winreg.CreateKey(sub_key, "command")
            gui_exe = self._resolve_gui_exe()

            if gui_exe is None:
                gui_script = self.APP_DIR / "ui" / "gui_customtkinter.py"
                python_exe = sys.executable.replace('python.exe', 'pythonw.exe')
                if not os.path.exists(python_exe):
                    python_dir = os.path.dirname(sys.executable)
                    python_exe = os.path.join(python_dir, 'pythonw.exe')

                command = f'"{python_exe}" "{gui_script}" --from-context-menu {operation} %V'
            else:
                command = f'"{str(gui_exe.resolve())}" --from-context-menu {operation} %V'
            
            winreg.SetValueEx(command_key, "", 0, winreg.REG_SZ, command)
            
            winreg.CloseKey(command_key)
            winreg.CloseKey(sub_key)
        
        except Exception as e:
            print(f"Errore durante registrazione sub-voce {label}: {e}")
            raise
    
    def _register_direct_menu(self, key_path: str, label: str, operation: str):
        """Registra una voce diretta nel menu contestuale"""
        try:
            gui_exe = self.APP_DIR / "dist" / "AdvancedFileMoverPro.exe"
            exe_dir = gui_exe.parent if gui_exe.exists() else self.APP_DIR / "dist"
            
            # Creare key principale
            key = winreg.CreateKey(self.root, key_path)
            
            # Impostare label
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, label)
            
            # Icona
            if operation == 'copy':
                icon_path = exe_dir / "Icon" / "copy_icon.ico"
            elif operation == 'move':
                icon_path = exe_dir / "Icon" / "move_icon.ico"
            else:
                icon_path = exe_dir / "Icon" / "icon.ico"
            
            if not icon_path.exists():
                icon_path = self.APP_DIR / "icon" / ("copy_icon.ico" if operation == 'copy' else "move_icon.ico")
            
            winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, str(icon_path.resolve()))
            
            # Comando
            command_key = winreg.CreateKey(key, "command")
            
            if not gui_exe.exists():
                gui_script = self.APP_DIR / "ui" / "gui_customtkinter.py"
                python_exe = sys.executable.replace('python.exe', 'pythonw.exe')
                if not os.path.exists(python_exe):
                    python_dir = os.path.dirname(sys.executable)
                    python_exe = os.path.join(python_dir, 'pythonw.exe')

                command = f'"{python_exe}" "{gui_script}" --from-context-menu {operation} %V'
            else:
                command = f'"{str(gui_exe.resolve())}" --from-context-menu {operation} %V'
            
            winreg.SetValueEx(command_key, "", 0, winreg.REG_SZ, command)
            
            winreg.CloseKey(command_key)
            winreg.CloseKey(key)
        
        except Exception as e:
            print(f"Errore durante registrazione {label}: {e}")
            raise
    
    def _unregister_direct_menu(self, key_path: str):
        """Rimuove una voce diretta dal menu contestuale"""
        try:
            # Rimuovere subkey command
            try:
                winreg.DeleteKey(self.root, f"{key_path}\\command")
            except FileNotFoundError:
                pass
            
            # Rimuovere key principale
            try:
                winreg.DeleteKey(self.root, key_path)
            except FileNotFoundError:
                pass
        
        except Exception as e:
            print(f"Avviso durante rimozione {key_path}: {e}")
    
    def _register_submenu(self, parent_key_path: str, menu_label: str, item_type: str):
        """Registra un submenu con Copia e Sposta nel menu contestuale"""
        try:
            gui_exe = self._resolve_gui_exe()
            exe_dir = self._resolve_exe_dir()
            
            # Creare key principale del submenu
            parent_key = winreg.CreateKey(self.root, parent_key_path)
            
            # Impostare label del menu principale
            winreg.SetValueEx(parent_key, "", 0, winreg.REG_SZ, menu_label)
            
            # Escludere Cestino con AppliesTo
            winreg.SetValueEx(parent_key, "AppliesTo", 0, winreg.REG_SZ, 
                             "NOT ClassName=\"Folder.Recycle.Bin\"")
            
            # Icona principale (cartella/file a seconda del tipo)
            if item_type == "folder":
                icon_path = exe_dir / "Icon" / "copy_icon.ico"
            else:
                icon_path = exe_dir / "Icon" / "copy_icon.ico"
            
            if not icon_path.exists():
                icon_path = gui_exe if gui_exe is not None else self.APP_EXE
            
            winreg.SetValueEx(parent_key, "Icon", 0, winreg.REG_SZ, str(icon_path.resolve()))
            
            # Creare shell subkey per le voci cascata
            shell_key = winreg.CreateKey(parent_key, "shell")
            
            # Sub-voce 1: Copia
            self._register_sub_operation(shell_key, "Copy", "Copia [Avanzata]", "copy", exe_dir)
            
            # Sub-voce 2: Sposta
            self._register_sub_operation(shell_key, "Move", "Sposta [Avanzata]", "move", exe_dir)
            
            winreg.CloseKey(shell_key)
            winreg.CloseKey(parent_key)
        
        except Exception as e:
            print(f"Errore durante registrazione submenu {menu_label}: {e}")
            raise
    
    def _register_sub_operation(self, shell_key, sub_name: str, label: str, operation: str, exe_dir):
        """Registra una sub-voce (Copia o Sposta) nel submenu"""
        try:
            sub_key = winreg.CreateKey(shell_key, sub_name)
            winreg.SetValueEx(sub_key, "", 0, winreg.REG_SZ, label)

            # Abilita multi-selezione (usa %V nel command)
            try:
                winreg.SetValueEx(sub_key, "MultiSelectModel", 0, winreg.REG_SZ, "Player")
            except Exception:
                pass
            
            # Icona per la sub-voce
            if operation == 'copy':
                icon_path = exe_dir / "Icon" / "copy_icon.ico"
            else:
                icon_path = exe_dir / "Icon" / "move_icon.ico"
            
            if not icon_path.exists():
                icon_path = self.APP_DIR / "icon" / ("copy_icon.ico" if operation == 'copy' else "move_icon.ico")
            
            winreg.SetValueEx(sub_key, "Icon", 0, winreg.REG_SZ, str(icon_path.resolve()))
            
            # Comando per la sub-voce
            command_key = winreg.CreateKey(sub_key, "command")
            gui_exe = self._resolve_gui_exe()

            if gui_exe is None:
                gui_script = self.APP_DIR / "ui" / "gui_customtkinter.py"
                python_exe = sys.executable.replace('python.exe', 'pythonw.exe')
                if not os.path.exists(python_exe):
                    python_dir = os.path.dirname(sys.executable)
                    python_exe = os.path.join(python_dir, 'pythonw.exe')
                command = f'"{python_exe}" "{gui_script}" --from-context-menu {operation} %V'
            else:
                command = f'"{str(gui_exe.resolve())}" --from-context-menu {operation} %V'
            
            winreg.SetValueEx(command_key, "", 0, winreg.REG_SZ, command)
            
            winreg.CloseKey(command_key)
            winreg.CloseKey(sub_key)
        
        except Exception as e:
            print(f"Errore durante registrazione sub-voce {label}: {e}")
            raise
    
    def _unregister_submenu(self, key_path: str):
        """Rimuove ricorsivamente un submenu e tutte le sub-voci"""
        try:
            def delete_tree(key, path):
                """Elimina ricorsivamente tutte le subkey"""
                try:
                    while True:
                        subkey_name = winreg.EnumKey(key, 0)
                        sub_key = winreg.OpenKey(key, subkey_name)
                        delete_tree(sub_key, f"{path}\\{subkey_name}")
                        winreg.CloseKey(sub_key)
                        winreg.DeleteKey(key, subkey_name)
                except OSError:
                    # No more subkeys
                    pass
            
            # Prova ad aprire la chiave - se non esiste, ignora silenziosamente
            try:
                key = winreg.OpenKey(self.root, key_path)
                delete_tree(key, key_path)
                winreg.CloseKey(key)
                winreg.DeleteKey(self.root, key_path)
            except FileNotFoundError:
                # La chiave non esiste, già rimossa o mai registrata - OK
                pass
        
        except Exception as e:
            # Altri errori (non FileNotFoundError) vengono loggati ma non bloccano
            print(f"Avviso durante rimozione submenu {key_path}: {e}")
            raise
        
    def get_status(self) -> str:
        """Verifica lo stato del menu contestuale nel registro"""
        try:
            status = f"🔍 Stato Menu Contestuale ({self.base_path})\n"
            status += "="*47 + "\n\n"
            
            # Verifica i submenu PowerShell-style
            file_submenu = r"Software\Classes\*\shell\AdvancedFileMover"
            folder_submenu = r"Software\Classes\Directory\shell\AdvancedFileMover"
            drive_submenu = r"Software\Classes\Drive\shell\AdvancedFileMover"
            
            # Controlla File Submenu
            try:
                key = winreg.OpenKey(self.root, file_submenu)
                # Controlla se le sub-voci esistono
                try:
                    copy_sub = winreg.OpenKey(key, "shell\\Copy")
                    winreg.CloseKey(copy_sub)
                    status += f"✅ File → 📋 Copia [Avanzata]\n"
                except FileNotFoundError:
                    status += f"❌ File → Copia [Avanzata] (non trovata)\n"
                
                try:
                    move_sub = winreg.OpenKey(key, "shell\\Move")
                    winreg.CloseKey(move_sub)
                    status += f"✅ File → ✂️ Sposta [Avanzata]\n"
                except FileNotFoundError:
                    status += f"❌ File → Sposta [Avanzata] (non trovata)\n"
                
                winreg.CloseKey(key)
            except FileNotFoundError:
                status += f"❌ File → Menu non registrato\n"
            
            status += "\n"
            
            # Controlla Folder Submenu
            try:
                key = winreg.OpenKey(self.root, folder_submenu)
                # Controlla se le sub-voci esistono
                try:
                    copy_sub = winreg.OpenKey(key, "shell\\Copy")
                    winreg.CloseKey(copy_sub)
                    status += f"✅ Cartella → 📋 Copia [Avanzata]\n"
                except FileNotFoundError:
                    status += f"❌ Cartella → Copia [Avanzata] (non trovata)\n"
                
                try:
                    move_sub = winreg.OpenKey(key, "shell\\Move")
                    winreg.CloseKey(move_sub)
                    status += f"✅ Cartella → ✂️ Sposta [Avanzata]\n"
                except FileNotFoundError:
                    status += f"❌ Cartella → Sposta [Avanzata] (non trovata)\n"
                
                winreg.CloseKey(key)
            except FileNotFoundError:
                status += f"❌ Cartella → Menu non registrato\n"

            status += "\n"

            # Controlla Drive Submenu
            try:
                key = winreg.OpenKey(self.root, drive_submenu)
                try:
                    copy_sub = winreg.OpenKey(key, "shell\\Copy")
                    winreg.CloseKey(copy_sub)
                    status += f"✅ Unità → 📋 Copia [Avanzata]\n"
                except FileNotFoundError:
                    status += f"❌ Unità → Copia [Avanzata] (non trovata)\n"

                try:
                    move_sub = winreg.OpenKey(key, "shell\\Move")
                    winreg.CloseKey(move_sub)
                    status += f"✅ Unità → ✂️ Sposta [Avanzata]\n"
                except FileNotFoundError:
                    status += f"❌ Unità → Sposta [Avanzata] (non trovata)\n"

                winreg.CloseKey(key)
            except FileNotFoundError:
                status += f"❌ Unità → Menu non registrato\n"
            
            status += "\n" + "="*47 + "\n"
            status += f"📝 Nota: Submenu stile PowerShell 7\n"
            status += "   Click su 'Advanced File Mover' → Copia/Sposta\n"
            
            return status
        
        except Exception as e:
            return f"Errore nel leggere lo stato: {str(e)}"


def main():
    """Funzione principale"""
    parser = argparse.ArgumentParser(description="Gestisce registrazione menu contestuale")
    parser.add_argument(
        "--register",
        action="store_true",
        help="Registra nel menu contestuale"
    )
    parser.add_argument(
        "--unregister",
        action="store_true",
        help="Rimuove dal menu contestuale"
    )
    parser.add_argument(
        "--admin",
        action="store_true",
        help="Usa HKEY_LOCAL_MACHINE (richiede admin)"
    )
    parser.add_argument(
        "--operation",
        help="Operazione da eseguire (copy/move) - lanciato dal context menu"
    )
    parser.add_argument(
        "--path",
        help="Percorso del file/cartella - lanciato dal context menu"
    )
    
    args = parser.parse_args()
    
    # Se lanciato dal context menu con --operation e --path
    if args.operation and args.path:
        # Lancia la GUI con i parametri senza console
        import subprocess
        gui_script = Path(__file__).parent.parent / "ui" / "gui_customtkinter.py"
        try:
            # Usa pythonw.exe per evitare console e CREATE_NO_WINDOW
            python_exe = sys.executable.replace('python.exe', 'pythonw.exe')
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            subprocess.Popen(
                [python_exe, str(gui_script), args.path, args.operation],
                cwd=str(Path(__file__).parent.parent),
                startupinfo=startupinfo,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            return 0
        except Exception as e:
            print(f"Errore nel lanciare la GUI: {e}")
            return 1
    
    # Se nessun argomento, mostrare help
    if not args.register and not args.unregister:
        parser.print_help()
        return 1
    
    registrar = ContextMenuRegistrar(use_admin=args.admin)
    
    if args.register:
        success = registrar.register()
    else:
        success = registrar.unregister()
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
