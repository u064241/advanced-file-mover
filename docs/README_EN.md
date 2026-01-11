# Advanced File Mover Pro

Windows utility for copying/moving files and folders with progress, auto-tuning (buffer/threads), Explorer context menu integration, and **auto-update from GitHub**.

## Requirements

- Windows 7+
- Python 3.12 in `.venv312`
- Dependencies: see `requirements.txt` (includes `pillow` for HiDPI flag icons, `requests` for auto-update)

## User Data (config + cache)

- User configuration: `%LOCALAPPDATA%\AdvancedFileMover\config.json`
- Storage detection cache: `%LOCALAPPDATA%\AdvancedFileMover\.storage_cache.json`

On first launch, if `config.json` doesn't exist in LocalAppData, it's created automatically.
If a `config.json` "template" exists near the EXE (e.g., installation), it's used as a base and then saved to LocalAppData.

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

## Auto-Update from GitHub

The application automatically checks for updates on startup:

- ✅ Asynchronous check in background (doesn't block the app)
- ✅ Manual **"Check Updates"** button in the Info tab
- ✅ Automatic download and installation (silent setup)
- ✅ Version synced from `config.json`

When an update is found:

1. Dialog with release notes
2. Automatic download of Setup.exe from GitHub Release
3. Silent installer execution
4. Automatic app restart

## Versioning

The application version is managed centrally in `config.json`:

```json
{
 "version": "1.0.2",
 ...
}
```

### Automatic Synchronization

When you run `.\build.ps1 -Setup`:

- `build.ps1` reads the version from `config.json`
- Automatically updates `installer/AdvancedFileMover.iss`
- Passes it to Inno Setup
- Output Setup will be named: `AdvancedFileMover_{version}_Setup.exe` (e.g., `AdvancedFileMover_1.0.2_Setup.exe`)
- Version also appears in Windows Control Panel

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

1) Alternatively, if you want to keep `dist/` (for testing/debugging), just do:

```powershell
.\build.ps1 -Clean
```

Then compile the Inno Setup script:

- Script: `installer\AdvancedFileMover.iss`
- Open it with Inno Setup and press **Compile**, or use `ISCC.exe`.

The installer runs at the end of installation:

- `AdvancedFileMoverPro.exe --register-context-menu`

This way the context menu points to the exact location of the installed executable.

## Release on GitHub

To create a new release:

1. Update version in `config.json`
2. Run `.\build.ps1 -Setup` (automatically syncs versions)
3. Create tag and push: `git tag -a vX.Y.Z -m "Release vX.Y.Z" && git push origin vX.Y.Z`
4. Upload `installer/Output/AdvancedFileMover_X.Y.Z_Setup.exe` as an asset in the GitHub release
5. Publish the release

Users will automatically receive update notifications!

## Context Menu (Explorer)

Registers the "Advanced File Mover" submenu with "Copy [Advanced]" / "Move [Advanced]" actions.

Note: the menu is in **Extended** mode → appears only with **Shift + right-click**.

### Recommended Mode (EXE)

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

## Languages / i18n

- Translations are in `i18n/*.json`
- Flag icons are in `src/assets/flags/*.png`
- Language switching is dynamic and applies to the entire GUI

## Testing

```powershell
cd .\TEST
C:\SOURCECODE\.venv312\Scripts\python.exe .\run_all_tests.py
```

## Project Structure (essential)

- `ui/gui_customtkinter.py`: Main GUI
- `src/file_operations.py`: Copy/move engine + progress
- `src/update_checker.py`: Auto-update from GitHub
- `src/ramdrive_handler.py` / `src/storage_detector.py`: Storage detection + auto-tuning
- `registry/context_menu.py`: Context menu registration/unregistration

## Troubleshooting

### Always use `.venv312`

Avoid system `py`/`python` if they point to different versions.

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
