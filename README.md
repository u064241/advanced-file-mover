# Advanced File Mover Pro

Utility Windows per copiare/spostare file e cartelle con progress, auto‑tuning (buffer/thread) e integrazione nel menu contestuale di Explorer.

## Requisiti

- Windows
- Python 3.12 in `.venv312`
- Dipendenze: vedi `requirements.txt` (include `pillow` per le bandiere HiDPI)

## Dati utente (config + cache)

- Configurazione utente: `%LOCALAPPDATA%\AdvancedFileMover\config.json`
- Cache rilevamento storage: `%LOCALAPPDATA%\AdvancedFileMover\.storage_cache.json`

Al primo avvio, se `config.json` non esiste in LocalAppData, viene creato automaticamente.
Se esiste un `config.json` “template” vicino all’EXE (es. installazione), viene usato come base e poi salvato in LocalAppData.

## Avvio rapido (GUI)

### Opzione consigliata: PowerShell

Dalla cartella `ADVANCED_FILE_MOVER`:

```powershell
.\run_gui.ps1
```

### Opzione alternativa: comando diretto

```powershell
C:\SOURCECODE\.venv312\Scripts\python.exe .\ui\gui_customtkinter.py
```

## Versioning

La versione dell'applicazione è gestita centralmente in `config.json`:

```json
{
 "version": "1.0.0",
 ...
}
```

Quando esegui `.\build.ps1 -Setup`:

- `build.ps1` legge la versione da `config.json`
- La passa a Inno Setup (file `.iss`)
- L'output Setup avrà il nome: `AdvancedFileMover_{versione}_Setup.exe` (es. `AdvancedFileMover_1.0.0_Setup.exe`)
- La versione appare anche nel Control Panel di Windows

**Per aggiornare la versione**: modifica il campo `version` in `config.json` prima di eseguire il build.

## Build EXE (PyInstaller)

```powershell
# build standard
.\build.ps1

# build con --clean
.\build.ps1 -Clean
```

- Spec: `gui_customtkinter.spec`
- Output: `dist/AdvancedFileMoverPro.exe`

Nota: la build copia anche risorse runtime in `dist/`:

- `dist/i18n/*.json` (traduzioni)
- `dist/assets/flags/*.png` (bandiere lingua)

## Installer (Setup.exe)

Per creare un `Setup.exe` classico con scelta cartella di installazione, l'opzione più semplice è **Inno Setup**.

1) Compila direttamente EXE + Setup:

```powershell
\.\build.ps1 -Clean -Setup
```

Nota: quando usi `-Setup`, se la compilazione del Setup va a buon fine lo script rimuove automaticamente `dist/` (per pulizia).

1) In alternativa, se vuoi mantenere `dist/` (per test/debug), fai solo:

```powershell
\.\build.ps1 -Clean
```

Poi compila lo script Inno Setup:

- Script: `installer\AdvancedFileMover.iss`
- Aprilo con Inno Setup e premi **Compile**, oppure usa `ISCC.exe`.

L'installer esegue a fine installazione:

- `AdvancedFileMoverPro.exe --register-context-menu`

Così il menu contestuale punta alla posizione esatta dell'eseguibile installato.

## Menu contestuale (Explorer)

Registra il submenu "Advanced File Mover" con le azioni "Copia [Avanzata]" / "Sposta [Avanzata]".

Nota: il menu è in modalità **Extended** → compare solo con **Shift + tasto destro**.

### Modalità consigliata (EXE)

Nota: se hai eseguito `\.\build.ps1 -Setup`, la cartella `dist/` viene rimossa a fine procedura.
In quel caso, per registrare il menu a mano usa l'EXE installato (in `{app}`) oppure rifai un build senza `-Setup`.

```powershell
# registra menu contestuale (HKCU)
dist\AdvancedFileMoverPro.exe --register-context-menu

# rimuove
dist\AdvancedFileMoverPro.exe --unregister-context-menu
```

### Modalità alternativa (script)

```powershell
# registra (HKCU)
C:\SOURCECODE\.venv312\Scripts\python.exe .\registry\context_menu.py --register

# rimuove
C:\SOURCECODE\.venv312\Scripts\python.exe .\registry\context_menu.py --unregister

# per HKLM (tutti gli utenti) richiede admin
C:\SOURCECODE\.venv312\Scripts\python.exe .\registry\context_menu.py --register --admin
```

Se `dist/AdvancedFileMoverPro.exe` esiste, il menu usa l’EXE; altrimenti lancia la GUI via `pythonw.exe` su `ui/gui_customtkinter.py`.

## Lingue / i18n

- Le traduzioni stanno in `i18n/*.json`.
- Le bandiere stanno in `src/assets/flags/*.png`.
- Il cambio lingua è dinamico e si applica all’intera GUI.

## Test

```powershell
cd .\TEST
C:\SOURCECODE\.venv312\Scripts\python.exe .\run_all_tests.py
```

## Struttura progetto (essenziale)

- `ui/gui_customtkinter.py`: GUI principale
- `src/file_operations.py`: motore copia/sposta + progress
- `src/ramdrive_handler.py` / `src/storage_detector.py`: rilevamento storage + auto‑tuning
- `registry/context_menu.py`: installazione/rimozione menu contestuale

## Troubleshooting

### Usa sempre `.venv312`

Evita `py`/`python` “di sistema” se puntano a versioni diverse.

Verifica rapida:

```powershell
C:\SOURCECODE\.venv312\Scripts\python.exe --version
C:\SOURCECODE\.venv312\Scripts\python.exe -c "import customtkinter, psutil; print('✓ GUI deps OK')"
```

### Pulizia cache Python

```powershell
taskkill /F /IM python.exe
Remove-Item -Recurse -Force .\ui\__pycache__, .\src\__pycache__ -ErrorAction SilentlyContinue
```
