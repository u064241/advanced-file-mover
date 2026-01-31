# Advanced File Mover Pro

[![Version](https://img.shields.io/badge/version-1.0.8-blue.svg)](https://github.com/u064241/advanced-file-mover/releases/latest)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows-lightgrey.svg)](https://www.microsoft.com/windows)

Professional Windows utility for copying/moving files and folders with real-time progress, auto-optimization (buffer/threads), Explorer context menu integration, and **auto-update from GitHub**.

---

## 📦 Installation

### Download Release

Download the latest version from [Releases](https://github.com/u064241/advanced-file-mover/releases/latest):

```text
AdvancedFileMover_1.0.8_Setup.exe
```

### Automatic Installation

1. Run `AdvancedFileMover_1.0.8_Setup.exe`
2. Follow the installation wizard
3. Context menu will be automatically registered
4. Launch the app from Start Menu or via context menu (Shift + right-click)

### Requirements

- Windows 10/11 (64-bit)
- .NET Framework (included in Windows)
- Administrator rights for installation

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
# Python 3.12
# Virtual environment
python -m venv .venv312
.venv312\Scripts\Activate.ps1

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
# installer\Output\AdvancedFileMover_1.0.8_Setup.exe
```

### PyInstaller Only Build

```powershell
pyinstaller --clean gui_customtkinter.spec

# Output: dist\AdvancedFileMoverPro\AdvancedFileMoverPro.exe
```

---

## 🔄 Changelog

### v1.0.8 (Latest)

- 🐛 **Fix**: Registry DisplayName now shows "v1.0.8" instead of "version 1.0.8"
- 🐛 **Fix**: Improved app termination during update (destroy + sys.exit for immediate closure)
- ⏱️ **Enhancement**: Increased wait time from 1s to 3s to ensure complete app shutdown before installer runs

### v1.0.7

- 🐛 **Fix**: Single-instance mutex for context menu (prevent multiple windows on multi-select)
- 📦 **Update**: PyInstaller added to requirements.txt

### v1.0.6

- 🐛 **Fix**: Auto-update properly closes app before installer runs
- 🐛 **Fix**: Resolved "file in use" error during updates

### v1.0.5

- 📦 Switched to installer-based distribution (one-dir)
- 🚀 **5-10x faster** startup from context menu (<1s vs 5-10s)
- ✅ Fix: Context menu multi-selection (no multiple instances)

### v1.0.3

- ✅ Fix: Multi-selection context menu with MultiSelectModel "Document"

### v1.0.2

- ✨ Auto-update system implemented

### v1.0.1

- 🎨 CustomTkinter GUI interface
- 📂 Context menu integration
- ⚡ Auto-tuning buffer/threads

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
 "version": "1.0.8",
 ...
}
```

### Automatic Synchronization

When you run `.\build.ps1 -Setup`:

- `build.ps1` reads the version from `config.json`
- Automatically updates `installer/AdvancedFileMover.iss`
- Passes it to Inno Setup
- Output Setup will be named: `AdvancedFileMover_{version}_Setup.exe` (e.g., `AdvancedFileMover_1.0.8_Setup.exe`)
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

### Always use `.venv312`

Avoid system `py`/`python` if they point to different versions.

Quick verification:

```powershell
.venv312\Scripts\python.exe --version
.venv312\Scripts\python.exe -c "import customtkinter, psutil; print('✓ GUI deps OK')"
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
