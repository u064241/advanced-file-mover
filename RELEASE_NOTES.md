# Advanced File Mover Pro - v1.0.0

**Release Date**: 2026-02-15  
**Status**: ✅ Stable Release

---

## 🎉 Welcome to v1.0.0 - Stable Release!

This is the first stable release of **Advanced File Mover Pro** with complete feature set, full internationalization (i18n) support, and comprehensive documentation.

---

## ✨ Features Included

### 🎯 Core Functionality
- **Drag & Drop Files**: Native tkinterdnd2 integration - drop files directly onto the source listbox
- **Multi-threaded Engine**: Efficient copy/move with configurable buffer and thread settings
- **RamDrive Support**: Auto-detection and acceleration for RamDrive operations
- **Single-Instance IPC**: Named Pipe integration for context menu
- **Auto-Update from GitHub**: Automatic checking and silent installation of updates

### 🎨 Modern Interface
- **CustomTkinter GUI**: Modern, responsive dark/light theme
- **Real-time Progress**: Speed (MB/s) and ETA display
- **Responsive Layout**: Consistent 900×720px window with grid-based design
- **Drag & Drop Support**: Even works with elevated privileges

### 🌍 Complete Internationalization (NEW)
- **5 Supported Languages**: 
  - 🇮🇹 Italiano (Italian)
  - 🇬🇧 English
  - 🇫🇷 Français (French)
  - 🇩🇪 Deutsch (German)
  - 🇪🇸 Español (Spanish)
- **Auto-detect System Language**: Automatically detects and uses system language on first launch
- **Runtime Language Switching**: Change language instantly - entire GUI updates dynamically
- **Fully Translatable Registry Status**: Context menu status messages now translate correctly ✨ NEW

### ⚡ Performance Optimization
- **Smart Auto-tuning**: Automatically adjusts buffer and thread count based on storage type
  - 🚀 NVMe: 256MB buffer, 12 threads
  - ⚡ SSD: 128MB buffer, 8 threads
  - 💾 HDD: 80MB buffer, 2 threads
  - 🔌 USB: 64MB buffer, 4 threads
  - 🌐 NAS: 32MB buffer, 2 threads
  - 💻 RamDrive: 8MB buffer, 16 threads
- **Background Tab Loading**: Faster startup times
- **Device Auto-detection**: Monitors for USB and storage device changes

### 🔧 Windows Integration
- **Context Menu**: Right-click on files/folders in Explorer (Shift + Right-Click)
- **Smart Status Display**: Real-time status of registered menu items with language support
- **Dynamic Menu Registration**: Menu automatically updates when changing language

### 📦 Installation & Distribution
- **Inno Setup Installer**: Professional Windows installer with upgrade support
- **One-directory Build**: PyInstaller packaging compatible with RamDrive
- **Portable Friendly**: Minimal system dependencies

---

## 🐛 Bug Fixes in v1.0.0

✅ **Registry Status Fully Translatable**
- All text in "Menu Status" section now respects language settings
- Status messages for Copy/Move operations correctly translate to selected language
- Dynamic mapping system ensures no hardcoded strings remain

✅ **Context Menu i18n**
- Menu labels automatically update when changing language
- Auto-re-registers menu entries with correct language labels

✅ **Complete Language Coverage**
- All UI elements, dialogs, and system messages support 5 languages
- Registry status, progress bar, and file operation messages all translated

---

## 📖 Documentation

### For Users
- **[README.md](README.md)**: Complete usage guide, installation instructions, and troubleshooting
- **[CHANGELOG.md](CHANGELOG.md)**: Detailed changelog with all features and fixes

### For Developers
- **Build Instructions**: `.\build.ps1 -Clean -Setup` creates installer
- **Project Structure**: Well-organized codebase with clear separation of concerns
- **Contributing**: Full guidelines for forks and pull requests

---

## 📥 Installation Options

### Option 1: Installer (Recommended)
```powershell
# Download and run the installer
AdvancedFileMover_1.0.0_Setup.exe

# Follow the installation wizard
# Context menu will be automatically registered
```

### Option 2: Build from Source
```powershell
# Clone the repository
git clone https://github.com/u064241/advanced-file-mover.git
cd advanced-file-mover

# Create virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Run the application
.\run_gui.ps1

# Or build installer
.\build.ps1 -Clean -Setup
```

---

## 🚀 Quick Start

### Via Context Menu
1. Select file(s) or folder(s) in Windows Explorer
2. **Shift + Right-Click** → Select **"Advanced File Mover"**
3. Choose **"Copy [Advanced]"** or **"Move [Advanced]"**
4. Select destination in the GUI
5. Operation completes with real-time progress

### Via GUI
1. Launch from Start Menu or run `AdvancedFileMoverPro.exe`
2. Drag files onto the source list (or use "Add File/Folder" buttons)
3. Enter destination folder
4. Select operation (Copy/Move)
5. Click "Start" and watch the real-time progress

---

## 🌐 Language Support

**Supported Languages**: Italian, English, French, German, Spanish

To change language:
1. Open the app
2. Go to **View** tab → **🌐 Interface Language**
3. Select desired language
4. All UI elements update instantly
5. Context menu automatically re-registers with new language labels

---

## 🔄 Auto-Update Feature

The application automatically checks for updates:
- ✅ Daily check on app startup (background)
- ✅ Manual check via **"Check Updates"** button in Info tab
- ✅ Automatic silent installation when update found
- ✅ One-click download from GitHub releases

---

## 🆘 System Requirements

- **OS**: Windows 10/11 (64-bit)
- **RAM**: 4GB minimum (8GB+ recommended)
- **Storage**: 50MB free space for installation
- **Administrator Rights**: Required for initial installation and context menu registration

---

## 🤝 Support & Contributing

### Report Issues
- GitHub Issues: [Report a bug](https://github.com/u064241/advanced-file-mover/issues)
- Include detailed description and screenshots

### Contribute
- Fork the repository
- Create feature branch: `git checkout -b feature/YourfeatureName`
- Commit changes: `git commit -m "Add new feature"`
- Push: `git push origin feature/YourFeatureName`
- Create Pull Request

---

## 📄 License

**MIT License** - See [LICENSE](LICENSE) file for details

Free to use, modify, and distribute!

---

## 👤 About

**Advanced File Mover Pro** is developed and maintained by **u064241**

- 📍 GitHub: [@u064241](https://github.com/u064241)
- 📦 Repository: [advanced-file-mover](https://github.com/u064241/advanced-file-mover)
- 🔗 Issues: [GitHub Issues](https://github.com/u064241/advanced-file-mover/issues)

---

## 🙏 Acknowledgments

Special thanks to the open-source community:
- **CustomTkinter** - Modern GUI toolkit
- **PyInstaller** - Application packaging
- **Inno Setup** - Windows installer creation
- **psutil** - System monitoring
- **tkinterdnd2** - Drag & drop support

---

## 📈 What's Next?

Future releases may include:
- 🎯 Advanced batch operations
- 🎯 Network storage optimization
- 🎯 GPU acceleration for large transfers
- 🎯 Plugin system for custom operations

Stay tuned! 🚀

---

**Thank you for using Advanced File Mover Pro!**

*For updates, follow the GitHub repository and enable notifications.*
