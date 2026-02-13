# Advanced File Mover Pro

[![Version](https://img.shields.io/badge/version-1.0.4-blue.svg)](https://github.com/u064241/advanced-file-mover/releases/latest)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows-lightgrey.svg)](https://www.microsoft.com/windows)

Professional Windows utility for copying/moving files and folders with real-time progress, auto-optimization (buffer/threads), Explorer context menu integration, and **auto-update from GitHub**.

---

## 📦 Installation

### Download Release

Download the latest version from [Releases](https://github.com/u064241/advanced-file-mover/releases/latest):

```text
AdvancedFileMover_1.0.4_Setup.exe
```

### Automatic Installation

1. Run `AdvancedFileMover_1.0.4_Setup.exe`
2. Follow the installation wizard
3. Context menu will be automatically registered
4. Launch the app from Start Menu or via context menu (Shift + right-click)

### Requirements

- Windows 10/11 (64-bit)
- .NET Framework (included in Windows)
- Administrator rights for installation

### First Time Installation

Run the installer and follow the wizard. The app will be registered in the Windows context menu automatically.

---

## 🚀 Usage

### Context Menu (Quick Method)

1. Select one or more files/folders in Explorer
2. **Shift + Right-Click** → You'll see **"Advanced File Mover"**
3. Choose:
   - **Copy [Advanced]** → Copy with optimization
   - **Move [Advanced]** → Move with optimization

### GUI Interface

1. Launch from Start Menu: **"Advanced File Mover Pro"**
2. Select source (file/folder)
3. Select destination
4. Choose operation (Copy/Move)
5. Click **"Start Operation"**

---

## 🔧 Build from Source

### Prerequisites

```powershell
# Python 3.12+
# Virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Inno Setup 6 (for installer)
# https://jrsoftware.org/isdl.php
```

### Complete Build

```powershell
cd C:\SOURCECODE\PYTHON\ADVANCED_FILE_MOVER

# Build PyInstaller + Inno Setup
.\build.ps1 -Clean -Setup

# Output:
# installer\Output\AdvancedFileMover_1.0.0_Setup.exe
```

### PyInstaller Only Build

```powershell
pyinstaller --clean gui_customtkinter.spec

# Output: dist\AdvancedFileMoverPro\AdvancedFileMoverPro.exe
```

---

## 🔄 Changelog

### v1.0.4

- 🌐 **i18n**: Context menu auto-updates when changing language (no manual re-register needed)
- 🔧 **Engine**: Added `is_registered()` method to detect existing context menu registration

### v1.0.3

- 🌐 **i18n**: Context menu entries (Copy/Move) now follow app language setting
- 🌐 **i18n**: Added `ctx_copy_label` / `ctx_move_label` keys to all 5 language files
- 🔧 **Engine**: Context menu re-registers with translated labels on language change

### v1.0.2

- 🐛 **Bugfix**: Fixed "Failed to load Python DLL" error when TEMP is on RamDrive
- 📦 **Build**: Switched from one-file to proper one-dir PyInstaller build (no temp extraction needed)
- 📦 **Build**: Simplified Inno Setup packaging with single recursive source
- 🚀 **Build**: Added `-Release` flag to build.ps1 for automated GitHub release publishing

### v1.0.1

- 🐛 **Bugfix**: Progress bar and transfer info label no longer hidden below window bottom edge
- 🎨 **UI**: Main tab converted from pack to grid layout — progress section always anchored at bottom
- 🎨 **UI**: Source listbox now expands/contracts with window resize

### v1.0.0

- 🎯 **Feature**: Native drag & drop support (tkinterdnd2) - drop files directly on source listbox
- 🎯 **Feature**: Admin drag & drop - works even when app runs with elevated privileges
- 🎯 **Feature**: Multi-file context menu via IPC (Named Pipe + file-based) - single instance aggregates all selected files
- 🎯 **Feature**: Auto-update from GitHub with launcher script (no file lock issues)
- 🎨 **UI**: CustomTkinter modern interface with dark/light theme toggle
- 🎨 **UI**: Compact layout with simplified progress bar (text above, clean visualization)
- 🎨 **UI**: Non-resizable window (900×720) for consistent UX
- 🎨 **UI**: High-contrast progress text with speed (MB/s) and ETA display
- 🎨 **UI**: Multi-language support (IT, EN, FR, DE, ES) with flag icons
- 🎨 **UI**: Elastic source listbox with minimum 80px height
- ⚡ **Performance**: Auto-tuning buffer/threads based on storage type (NVMe/SSD/HDD/USB/NAS/RamDrive)
- ⚡ **Performance**: Faster startup with background tab loading
- ⚡ **Performance**: Auto-detect USB/device insert/removal (drive polling) with automatic Info tab refresh
- 🔧 **Engine**: Multi-threaded copy/move with configurable buffer size
- 🔧 **Engine**: RamDrive detection and acceleration support
- 🔧 **Engine**: Single-instance mutex with IPC for context menu integration
- 📂 **Context Menu**: Windows Explorer integration (Shift + right-click)
- 📂 **Context Menu**: Submenu with Copy [Advanced] and Move [Advanced]
- 📦 **Installer**: Inno Setup-based Windows installer
- 📦 **Build**: PyInstaller one-dir packaging with automatic version sync

---

## 📝 User Data (config + cache)

- User configuration: `%LOCALAPPDATA%\AdvancedFileMover\config.json`
- Storage detection cache: `%LOCALAPPDATA%\AdvancedFileMover\.storage_cache.json`

On first launch, if `config.json` doesn't exist in LocalAppData, it's created automatically.
If a `config.json` "template" exists near the EXE (e.g., installation), it's used as a base and then saved to LocalAppData.

---

## 🔄 Auto-Update from GitHub

The application automatically checks for updates on startup:

- ✅ Asynchronous check in background (doesn't block the app)
- ✅ Manual **"Check Updates"** button in the Info tab
- ✅ Automatic download and installation (silent setup)
- ✅ Version synced from `config.json`

When an update is found:

1. Dialog with release notes
2. Automatic download of Setup.exe from GitHub Release
3. **App closes cleanly** before installer runs (v1.0.6+)
4. Silent installer execution
5. Automatic app restart

---

## 📐 Versioning

The application version is managed centrally in `config.json`:

```json
{
 "version": "1.0.9",
 ...
}
```

### Automatic Synchronization

When you run `.\build.ps1 -Setup`:

- `build.ps1` reads the version from `config.json`
- Automatically updates `installer/AdvancedFileMover.iss`
- Passes it to Inno Setup
- Output Setup will be named: `AdvancedFileMover_{version}_Setup.exe` (e.g., `AdvancedFileMover_1.0.9_Setup.exe`)
- Version also appears in Windows Control Panel

**To update the version**: modify the `version` field in `config.json` before running the build.

---

## 🎨 Context Menu (Explorer)

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
python.exe .\registry\context_menu.py --register

# unregister
python.exe .\registry\context_menu.py --unregister

# for HKLM (all users) requires admin
python.exe .\registry\context_menu.py --register --admin
```

---

## 🌍 Languages / i18n

- Translations are in `i18n/*.json`
- Flag icons are in `src/assets/flags/*.png`
- Language switching is dynamic and applies to the entire GUI

---

## 🧪 Testing

```powershell
cd .\TEST
python.exe .\run_all_tests.py
```

---

## 📁 Project Structure (essential)

- `ui/gui_customtkinter.py`: Main GUI
- `src/file_operations.py`: Copy/move engine + progress
- `src/update_checker.py`: Auto-update from GitHub
- `src/ramdrive_handler.py` / `src/storage_detector.py`: Storage detection + auto-tuning
- `registry/context_menu.py`: Context menu registration/unregistration

---

## 🐛 Troubleshooting

### Always use `.venv`

Avoid system `py`/`python` if they point to different versions.

Quick verification:

```powershell
.venv\Scripts\python.exe --version
.venv\Scripts\python.exe -c "import customtkinter, psutil; print('✓ GUI deps OK')"
```

### Clean Python cache

```powershell
taskkill /F /IM python.exe
Remove-Item -Recurse -Force .\ui\__pycache__, .\src\__pycache__ -ErrorAction SilentlyContinue
```

---

## 🤝 Contributing

Contributions, issues and feature requests are welcome!

1. Fork the project
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 License

Distributed under MIT License. See `LICENSE` for more information.

---

## 👤 Author

### u064241

- GitHub: [@u064241](https://github.com/u064241)
- Repository: [advanced-file-mover](https://github.com/u064241/advanced-file-mover)

---

## 🙏 Acknowledgments

- [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) - Modern GUI framework
- [PyInstaller](https://www.pyinstaller.org/) - Packaging
- [Inno Setup](https://jrsoftware.org/isinfo.php) - Windows installer

---
