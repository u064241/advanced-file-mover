# Advanced File Mover Pro

Utility Windows per copiare/spostare file e cartelle con progress, auto‑tuning (buffer/thread) e integrazione nel menu contestuale di Explorer.

## Requirements

- Windows 7+
- Python 3.12 in `.venv312`
- Dipendenze: vedi `requirements.txt` (include `pillow` per le bandiere HiDPI)

## User Data (config + cache)

- User configuration: `%LOCALAPPDATA%\AdvancedFileMover\config.json`
- Storage detection cache: `%LOCALAPPDATA%\AdvancedFileMover\.storage_cache.json`

Al primo avvio, se `config.json` non esiste in LocalAppData, viene creato automaticamente.
Se esiste un `config.json` “template” vicino all’EXE (es. installazione), viene usato come base e poi salvato in LocalAppData.

## Quick Start (GUI)

### Recommended Option: PowerShell

From the `ADVANCED_FILE_MOVER` folder:

```powershell
.\run_gui.ps1
```

### Alternative Option: Direct command

```powershell
C:\SOURCECODE\.venv312\Scripts\python.exe .\ui\gui_customtkinter.py
```

## Versioning

The application version is managed centrally in `config.json`:

```json
{
 "version": "1.0.2",
 ...
}
```

### Sincronizzazione automatica

### Automatic Synchronization

When you run `.\build.ps1 -Setup`:

- `build.ps1` legge la versione da `config.json`
- La passa a Inno Setup (file `.iss`)
- L'output Setup avrà il nome: `AdvancedFileMover_{versione}_Setup.exe` (es. `AdvancedFileMover_1.0.0_Setup.exe`)
- La versione appare anche nel Control Panel di Windows

**To update the version**: modify the `version` field in `config.json` before running the build.

## Build EXE (PyInstaller)

```powershell
# standard build
.\build.ps1

# build with --clean
.\build.ps1 -Clean
```

- Spec: `gui_customtkinter.spec`
- Output: `dist/AdvancedFileMoverPro.exe`

Note: the build also copies runtime resources to `dist/`:

- `dist/i18n/*.json` (translations)
- `dist/assets/flags/*.png` (language flags)

## Installer (Setup.exe)

To create a classic `Setup.exe` with installation folder selection, the simplest option is **Inno Setup**.

1) Compile directly EXE + Setup:

```powershell
.\build.ps1 -Clean -Setup
```

Note: when using `-Setup`, if Setup compilation succeeds the script automatically removes `dist/` (for cleanup).

1) In alternativa, se vuoi mantenere `dist/` (per test/debug), fai solo:

```powershell
.\build.ps1 -Clean
```

Then compile the Inno Setup script:

- Script: `installer\AdvancedFileMover.iss`
- Open it with Inno Setup and press **Compile**, or use `ISCC.exe`.

The installer runs at the end of installation:

- `AdvancedFileMoverPro.exe --register-context-menu`

Così il menu contestuale punta alla posizione esatta dell'eseguibile installato.

## Menu contestuale (Explorer)

Registra il submenu "Advanced File Mover" con le azioni "Copia [Avanzata]" / "Sposta [Avanzata]".

Nota: il menu è in modalità **Extended** → compare solo con **Shift + tasto destro**.

### Modalità consigliata (EXE)

Nota: se hai eseguito `\.\build.ps1 -Setup`, la cartella `dist/` viene rimossa a fine procedura.
In quel caso, per registrare il menu a mano usa l'EXE installato (in `{app}`) oppure rifai un build senza `-Setup`.

```powershell
# register context menu (HKCU)
dist\AdvancedFileMoverPro.exe --register-context-menu

# unregister
dist\AdvancedFileMoverPro.exe --unregister-context-menu
```

### Alternative Mode (script)

```powershell
# register (HKCU)
C:\SOURCECODE\.venv312\Scripts\python.exe .\registry\context_menu.py --register

# unregister
C:\SOURCECODE\.venv312\Scripts\python.exe .\registry\context_menu.py --unregister

# for HKLM (all users) requires admin
C:\SOURCECODE\.venv312\Scripts\python.exe .\registry\context_menu.py --register --admin
```

Se `dist/AdvancedFileMoverPro.exe` esiste, il menu usa l’EXE; altrimenti lancia la GUI via `pythonw.exe` su `ui/gui_customtkinter.py`.

## Lingue / i18n

- Le traduzioni stanno in `i18n/*.json`.
- Le bandiere stanno in `src/assets/flags/*.png`.
- Il cambio lingua è dinamico e si applica all’intera GUI.

## Testing

```powershell
cd .\TEST
C:\SOURCECODE\.venv312\Scripts\python.exe .\run_all_tests.py
```

## Project Structure (essential)

- `ui/gui_customtkinter.py`: GUI principale
- `src/file_operations.py`: motore copia/sposta + progress
- `src/ramdrive_handler.py` / `src/storage_detector.py`: rilevamento storage + auto‑tuning
- `registry/context_menu.py`: installazione/rimozione menu contestuale

## Troubleshooting

### Always use `.venv312`

Evita `py`/`python` “di sistema” se puntano a versioni diverse.

Quick verification:

```powershell
C:\SOURCECODE\.venv312\Scripts\python.exe --version
C:\SOURCECODE\.venv312\Scripts\python.exe -c "import customtkinter, psutil; print('✓ GUI deps OK')"
```

### Clean Python cache

```powershell
taskkill /F /IM python.exe
Remove-Item -Recurse -Force .\ui\__pycache__, .\src\__pycache__ -ErrorAction SilentlyContinue
```
