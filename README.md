# Advanced File Mover Pro

[![Version](https://img.shields.io/badge/version-1.0.6-blue.svg)](https://github.com/u064241/advanced-file-mover/releases/latest)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows-lightgrey.svg)](https://www.microsoft.com/windows)

**[📖 Extended Documentation](docs/README_EN.md)**

---

Professional Windows utility for copying/moving files and folders with real-time progress, auto-optimization (buffer/threads), Explorer context menu integration, and **auto-update from GitHub**.

---

## 📦 Installation

### Download Release

Download the latest version from [Releases](https://github.com/u064241/advanced-file-mover/releases/latest):

```text
AdvancedFileMover_1.0.6_Setup.exe
```

### Automatic Installation

1. Run `AdvancedFileMover_1.0.6_Setup.exe`
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
# installer\Output\AdvancedFileMover_1.0.6_Setup.exe
```

### PyInstaller Only Build

```powershell
pyinstaller --clean gui_customtkinter.spec

# Output: dist\AdvancedFileMoverPro\AdvancedFileMoverPro.exe
```

---

## 🔄 Changelog

### v1.0.6 (Latest)

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
