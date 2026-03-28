# Advanced File Mover Pro

[![Version](https://img.shields.io/badge/version-1.0.6-blue.svg)](https://github.com/u064241/advanced-file-mover/releases/latest)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows-lightgrey.svg)](https://www.microsoft.com/windows)

Professional Windows utility for copying and moving files and folders with real-time progress, hardware auto-optimization (buffer/threads), Windows Explorer context menu integration, and automatic updates from GitHub.

**Version**: 1.0.6 (Stable)
**Release Date**: 2026-03-28
**Status**: ✅ Production Ready

---

## 🎯 Key Features

### ⚡ Performance & Optimization
- **Smart Auto-tuning**: Automatically adjusts buffer size and thread count based on storage type
  - NVMe: 256MB buffer, 12 threads
  - SSD: 128MB buffer, 8 threads
  - HDD: 80MB buffer, 2 threads
  - USB: 64MB buffer, 4 threads
  - NAS: 32MB buffer, 2 threads
  - RamDrive: 8MB buffer, 16 threads
- **Long Path Support**: Full support for paths exceeding 260 characters (Windows MAX_PATH limit)
- **RamDrive Detection**: Auto-detect and accelerate operations on RamDrive
- **Multi-threaded Engine**: Efficient concurrent copy/move operations
- **Real-time Progress**: Display speed (MB/s) and ETA
- **Device Auto-detection**: Monitor for USB and storage device changes

### 🎨 Modern User Interface
- **CustomTkinter GUI**: Modern, responsive design with dark/light theme toggle
- **Real-time Progress Display**: Continuous speed and ETA updates
- **Responsive Layout**: Consistent 900×720px non-resizable window with grid-based design
- **Elastic Listbox**: Flexible source file list with minimum 80px height
- **Drag & Drop Support**: Native tkinterdnd2 integration - even works with elevated privileges

### 🌍 Complete Internationalization
- **5 Supported Languages**: Italian, English, French, German, Spanish
- **Auto-detect System Language**: Automatically detects and uses system language on first launch
- **Runtime Language Switching**: Change language instantly - entire GUI updates dynamically
- **Fully Translatable UI**: All dialogs, progress messages, and system text support all languages
- **Registry Status Translation**: Context menu status messages now translate to all supported languages

### 🔧 Windows Explorer Integration
- **Context Menu**: Right-click access via Shift + Right-Click in Windows Explorer
- **Submenu with Copy/Move**: "Copy [Advanced]" and "Move [Advanced]" options
- **Smart Status Display**: Real-time verification of registered menu items with language support
- **Dynamic Menu Registration**: Menu automatically updates when changing language
- **Single-Instance IPC**: Named Pipe integration for efficient multi-selection aggregation

### 🚀 Auto-Update System
- **Automatic Update Checking**: Checks for updates on application startup (background)
- **Manual Update Check**: "Check Updates" button in the Info tab
- **Silent Installation**: Automatic download and installation of updates
- **Version Synchronization**: Version synced from `config.json` automatically

### 📦 Installation & Distribution
- **Inno Setup Installer**: Professional Windows installer with upgrade support
- **PyInstaller One-Dir**: RamDrive-compatible, no temporary extraction
- **Portable Friendly**: Minimal system dependencies required

---

## 📥 Installation

### Download Release (Recommended)

Download the latest version from [GitHub Releases](https://github.com/u064241/advanced-file-mover/releases/latest):

```text
AdvancedFileMover_1.0.6_Setup.exe
```

### Automatic Installation

1. Download `AdvancedFileMover_1.0.6_Setup.exe`
2. Run the installer
3. Follow the installation wizard
4. Context menu will be automatically registered
5. Launch from Start Menu or via context menu (Shift + Right-Click)

### Requirements

- **OS**: Windows 10/11 (64-bit)
- **Runtime**: .NET Framework (included in Windows)
- **Permissions**: Administrator rights required for installation
- **RAM**: 4GB minimum (8GB+ recommended)
- **Storage**: 50MB free space

### Build from Source

#### Prerequisites

```powershell
# Python 3.12+
python --version

# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Install Inno Setup 6 (for creating installer)
# https://jrsoftware.org/isdl.php
```

#### Build Options

**Complete Build (PyInstaller + Installer)**
```powershell
cd C:\SOURCECODE\PYTHON\advanced-file-mover

.\build.ps1 -Clean -Setup

# Output: installer\Output\AdvancedFileMover_1.0.6_Setup.exe
```

**PyInstaller Only (Executable)**
```powershell
pyinstaller --clean gui_customtkinter.spec

# Output: dist\AdvancedFileMoverPro\AdvancedFileMoverPro.exe
```

---

## 🚀 Usage

### Quick Start via Context Menu

1. Select one or more files/folders in Windows Explorer
2. **Shift + Right-Click** → Select **"Advanced File Mover"**
3. Choose operation:
   - **Copy [Advanced]** - Copy with optimization
   - **Move [Advanced]** - Move with optimization
4. Select destination in the GUI
5. Operation begins with real-time progress display

### GUI Interface

1. Launch from Start Menu: **"Advanced File Mover Pro"**
2. Add source files/folders:
   - Click **"Add File"** or **"Add Folder"** buttons
   - Or drag & drop files directly onto the source list
3. Select destination folder (click **"Browse"**)
4. Configure options:
   - **Use RamDrive**: Enable for ultra-fast transfers to/from RamDrive
   - **Overwrite**: Replace existing files at destination
   - **Delete Source**: Remove original files after move operation
5. Choose operation: **Copy** or **Move**
6. Monitor real-time progress with speed and ETA

### Info Tab

- **System Information**: CPU, RAM, and system details
- **RamDrive Status**: Detection and statistics
- **Storage Detection**: Identifies storage type and location
- **Auto-tuning Parameters**: Shows recommended buffer/threads for selected paths
- **Check Updates**: Manual update checking

### View Tab

- **Theme Selection**: Switch between Dark and Light themes
- **Language Selection**: Choose from 5 supported languages
- **Auto-elevate Options**: Configure UAC behavior
- **Always on Top**: Keep window above other windows

---

## 🔄 Version & Changelog

### v1.0.6 (2026-03-28) - Bug Fix Release

#### 🐛 Bug Fixes
- **Progress bar stuck at ~50% on batch MOVE**: When moving multiple files, the progress bar would stop at a fraction of 100% (e.g. 50% for 2 files, 33% for 3 files) instead of completing. The root cause was that `_batch_completed_bytes` was only updated via `os.path.isfile(source)` *after* the operation — but MOVE deletes the source, so that check always returned `False` and the accumulator stayed permanently at 0. The fix captures the source file size *before* calling `file_engine.move()` and uses that pre-captured value to update `_batch_completed_bytes` on success, regardless of whether the source still exists

---

### v1.0.5 (2026-03-18) - Feature & Bug Fix Release

#### ✨ New Features
- **Overwrite conflict dialog**: When the "Overwrite existing files" checkbox is **disabled** and a destination file already exists, a dialog is now shown instead of silently skipping. The user can choose:
  - **Overwrite** — overwrite this file only, keep asking for subsequent conflicts
  - **Skip** — skip this file only
  - **Overwrite all** — overwrite this and all remaining conflicts without further prompts
  - **Skip all** — skip this and all remaining conflicts without further prompts
  - Closing the dialog with the × button is equivalent to *Skip*
  
  When the checkbox is **enabled** the operation proceeds automatically as before. The per-operation flags are reset at the start of each new operation. Fully translated into all 5 supported languages (it, en, de, es, fr)

#### 🐛 Bug Fixes
- **Progress bar frozen at 100% when files added during operation**: When additional files were dragged into the source list while a copy/move was already running, the progress bar would jump to 100 % and stay there while those late-arriving files were still being processed. The root cause was that `_batch_total_size` and `_batch_file_count` were computed once at the start of `_operation_worker` and never updated. `_add_source_paths()` now increments both counters by the size (bytes) and count of every file that is appended while an operation is in progress, keeping the byte-based progress calculation accurate for the full dynamic queue

---

### v1.0.4 (2026-03-07) - Bug Fix Release

#### 🐛 Bug Fixes
- **Context menu hidden beyond 15 files**: The "Advanced File Mover" entry in the Windows Explorer Shift+Right-Click menu was not appearing when 16 or more files were selected. `MultiSelectModel = "Player"` is now set both on the **parent verb** (`*\shell\AdvancedFileMover`) — which is where Windows evaluates it to decide whether to render the cascading menu — and on each sub-command (`Copy`/`Move`). Without it, Windows defaults to `"Document"` behaviour which caps display at 15 items. The fix is propagated to all three registration paths (files `*`, directories `Directory`, drives `Drive`); the existing `--single-instance` IPC mechanism handles aggregation for any number of files

---

### v1.0.3 (2026-02-25) - Bug Fix Release

#### 🐛 Bug Fixes
- **RamDrive preference persistence**: The "Use RamDrive" checkbox state is now correctly preserved across sessions. Previously, when the source or destination was on the RamDrive (forcing the checkbox off), the forced `False` value was saved to `config.json` — so on next launch the option remained disabled even with unrelated paths. A separate `_ramdrive_user_pref` field now tracks the real user preference independently from the forced override
- **Destination RamDrive check**: `_update_ramdrive_option_state()` now also checks the destination path, not only the sources (both source and destination on RamDrive must disable the checkbox)
- **Preference restored on path change**: When source/destination no longer reside on the RamDrive, the user's original preference is automatically restored into the checkbox

---

### v1.0.2 (2026-02-23) - Bug Fix Release

#### 🐛 Bug Fixes: All updates to `processed_size` in the copy/move engine are now protected by `threading.Lock`, eliminating race conditions during parallel transfers
- **`on_complete` called exactly once**: Callback was previously invoked once per file in `_handle_file`; moved to `_perform_operation` so it fires a single time at the end of the operation
- **Missing `_log_info()` method**: Absent method caused silent `AttributeError` when logging informational events; stub now defined alongside `_log_error()`
- **MOVE cross-drive space check**: Free-space validation for cross-drive moves now correctly uses `total_size` as the required space (was always `0`)
- **`overwrite` parameter wired end-to-end**: `FileOperationEngine` now accepts and propagates `overwrite: bool = True`; GUI forwards the user toggle at engine construction and before each operation
- **Overwrite check in `_copy_via_ramdrive`**: RamDrive-buffered copies now honour the `overwrite` flag (files were silently overwritten regardless)
- **Temp file name collision in `_copy_via_ramdrive`**: Temporary files now use `id(source)` as prefix, preventing concurrent threads from clobbering each other's staging file
- **Dead code removed from `_copy_file_internal`**: Unreachable `if self.on_complete` / `return True` block and orphaned `except` clause removed
- **`_handle_directory` unified**: Legacy stub now delegates entirely to `_handle_directory_with_ramdrive`, eliminating duplicate directory-traversal logic
- **Parallel directory copy**: `_handle_directory_with_ramdrive` reimplemented with `concurrent.futures.ThreadPoolExecutor`; destination directories are pre-created single-threaded to avoid race conditions; error propagation via `threading.Event`
- **Tkinter thread safety**: Remaining tabs (Options, Stats, Info) are now loaded on the main thread via `root.after(500, …)` instead of a background `threading.Thread`, preventing widget-creation crashes
- **`_auto_profile_parameters` duplicate removed**: Method was an exact copy of `_auto_tune_parameters`; now replaced by a one-line delegation, eliminating 20+ lines of diverged dead code
- **`_progress_monitor` dead code removed**: Method was defined but never started as a thread; removed entirely
- **IPC atomic rename**: `_poll_pending_files` now atomically renames the pending file before reading, eliminating the TOCTOU race where a second Explorer process could append data between the read and the clear
- **RamDrive false-positive detection**: Volume-label heuristic no longer matches "temp", "volatile", or "memory" labels (false positives on USB "Memory Card" or SSD "Temp Work" partitions); only labels equal to "ram" or starting with "ram" are accepted
- **Unused `StorageDetector` import cleaned up**: Instance and import removed from `gui_customtkinter.py` (class was instantiated but never used)

---

### v1.0.1 (2026-02-18) - Patch Release

#### 🐛 Bug Fixes
- **Long Path Support**: Added `\\?\` prefix to all filesystem operations, fixing failures on paths exceeding Windows MAX_PATH (260 characters)
- All `os.walk`, `os.makedirs`, `open()`, `os.remove`, `os.path.exists` calls in the copy/move engine now support paths > 260 characters
- Drag & drop path validation now works correctly with long paths
- CLI argument path reconstruction (context menu) handles long paths properly
- Error messages display clean paths (without `\\?\` prefix) for readability

#### ✨ Improvements
- New utility functions: `long_path()` and `strip_long_path_prefix()` in `src/utils.py`
- `is_path_accessible()`, `is_path_writable()`, `get_file_size()`, `create_directory_if_not_exists()` now support long paths
- Works on all Windows systems regardless of `LongPathsEnabled` registry setting

---

### v1.0.0 (2026-02-15) - Stable Release

#### ✨ New Features
- Native drag & drop support (tkinterdnd2) - drop files directly on source listbox
- Admin drag & drop - works even when app runs with elevated privileges
- Multi-file context menu via IPC (Named Pipe + file-based aggregation)
- Auto-update from GitHub with launcher script (no file lock issues)
- CustomTkinter modern interface with dark/light theme toggle
- Grid-based main tab layout - progress section always anchored at bottom
- High-contrast progress text with speed (MB/s) and ETA display
- Multi-language support (Italian, English, French, German, Spanish) with flag icons
- Elastic source listbox with minimum 80px height
- Auto-detect system language on first launch (fallback: English)
- Full runtime language switch - all widgets update instantly
- Context menu entries follow app language with auto-re-registration
- Multi-threaded copy/move with configurable buffer size
- RamDrive detection and acceleration support
- Single-instance mutex with IPC for context menu integration
- Auto-tuning buffer/threads based on storage type
- Faster startup with background tab loading
- Auto-detect USB/device insert/removal with automatic Info tab refresh
- Inno Setup-based Windows installer with clean upgrade support
- PyInstaller one-dir packaging (no temp extraction, RamDrive compatible)

#### 🐛 Bug Fixes
- ✅ Registry status text now fully translatable in all languages
- ✅ Menu status section updates language correctly on language change
- ✅ All hardcoded Italian strings in registry status mapped to i18n keys
- ✅ Dynamic translation mapping for registry output (copy/move/missing status)

#### 📋 Improvements
- Complete i18n support for all UI elements, dialogs, and system messages
- Comprehensive documentation with installation and troubleshooting guides
- Professional Inno Setup installer with upgrade support
- Development-friendly project structure with clear separation of concerns

---

## 📂 Project Structure

```
advanced-file-mover/
├── ui/
│   ├── gui_customtkinter.py      # Main GUI application
│   └── __init__.py
├── src/
│   ├── file_operations.py         # Multi-threaded copy/move engine
│   ├── update_checker.py          # Auto-update from GitHub
│   ├── ramdrive_handler.py        # RamDrive detection & acceleration
│   ├── storage_detector.py        # Storage type detection engine
│   ├── utils.py                   # Utility functions
│   └── __init__.py
├── registry/
│   ├── context_menu.py            # Context menu registration
│   └── __init__.py
├── i18n/
│   ├── it.json                    # Italian translations
│   ├── en.json                    # English translations
│   ├── fr.json                    # French translations
│   ├── de.json                    # German translations
│   └── es.json                    # Spanish translations
├── icon/                          # Application icons
├── installer/
│   ├── AdvancedFileMover.iss      # Inno Setup script
│   └── Output/                    # Built installers
├── config.json                    # Application configuration
├── gui_customtkinter.spec         # PyInstaller spec file
├── requirements.txt               # Python package dependencies
├── build.ps1                      # Build automation script
├── run_gui.ps1                    # Launch GUI script
├── README.md                      # This file
└── LICENSE                        # MIT License
```

---

## 🎛️ Configuration

Application settings are stored in `%LOCALAPPDATA%\AdvancedFileMover\config.json`:

```json
{
  "version": "1.0.2",
  "theme": "dark",
  "always_on_top": true,
  "window_size": {
    "width": 900,
    "height": 720
  },
  "buffer_size": 100,
  "threads": 4,
  "ramdrive": true,
  "overwrite": true,
  "delete_source": true,
  "language": "en",
  "auto_elevate_on_start": false
}
```

### Configuration Options

- **version**: Application version (auto-synced)
- **theme**: Interface theme ("dark" or "light")
- **always_on_top**: Keep window above other windows (true/false)
- **window_size**: Window dimensions (width × height)
- **buffer_size**: File operation buffer in MB (50-256)
- **threads**: Number of concurrent threads (1-16)
- **ramdrive**: Enable RamDrive acceleration (true/false)
- **overwrite**: Automatically overwrite existing files (true/false)
- **delete_source**: Delete original files after move (true/false)
- **language**: Interface language ("it", "en", "fr", "de", "es")
- **auto_elevate_on_start**: Auto-elevate UAC on startup (true/false)

### User Data Location

- **Configuration**: `%LOCALAPPDATA%\AdvancedFileMover\config.json`
- **Cache**: `%LOCALAPPDATA%\AdvancedFileMover\.storage_cache.json`

On first launch, if `config.json` doesn't exist, it's created automatically.

---

## 🌐 Supported Languages

| Language | Code | Status |
|----------|------|--------|
| 🇮🇹 Italiano (Italian) | it | ✅ Complete |
| 🇬🇧 English | en | ✅ Complete |
| 🇫🇷 Français (French) | fr | ✅ Complete |
| 🇩🇪 Deutsch (German) | de | ✅ Complete |
| 🇪🇸 Español (Spanish) | es | ✅ Complete |

To change language:
1. Open the application
2. Click the **View** tab
3. Select desired language from **🌐 Interface Language** dropdown
4. All UI elements update instantly
5. Context menu automatically re-registers with new language

---

## 🔧 Advanced Options

### Context Menu Registration (Command Line)

**Register via EXE:**
```powershell
dist\AdvancedFileMoverPro.exe --register-context-menu
```

**Unregister via EXE:**
```powershell
dist\AdvancedFileMoverPro.exe --unregister-context-menu
```

**Register via Python (HKCU - Current User):**
```powershell
python.exe .\registry\context_menu.py --register
```

**Register for All Users (HKLM - Requires Admin):**
```powershell
python.exe .\registry\context_menu.py --register --admin
```

**Unregister via Python:**
```powershell
python.exe .\registry\context_menu.py --unregister
```

### Version Management

Version is centrally managed in `config.json`:

```json
{
  "version": "1.0.2",
  ...
}
```

**To update version:**
1. Modify `version` field in `config.json`
2. Run `.\build.ps1 -Clean -Setup`
3. Build script automatically updates installer version
4. Output filename reflects new version: `AdvancedFileMover_X.X.X_Setup.exe`
5. Version appears in Windows Control Panel

---

## 🐛 Troubleshooting

### Issue: Drag & Drop Not Working

**Solution**: Ensure you have tkinterdnd2 installed:
```powershell
pip install tkinterdnd2
```

If still not working with Administrator privileges, the app handles this automatically with fallback methods.

### Issue: Python Cache Errors

**Solution**: Clear Python cache:
```powershell
taskkill /F /IM python.exe
Remove-Item -Recurse -Force .\ui\__pycache__, .\src\__pycache__ -ErrorAction SilentlyContinue
```

### Issue: Context Menu Not Appearing

**Solution**: Verify registration and check Windows Registry:
1. Run the application as Administrator
2. Go to the **Context Menu** tab
3. Click **"Check Status"** button
4. If not registered, click **"Register Menu"**

### Issue: Update Not Downloading

**Solution**: Check internet connection and verify GitHub releases:
1. Go to the **Info** tab
2. Click **"Check Updates"**
3. Ensure you have internet connectivity
4. Check [GitHub Releases](https://github.com/u064241/advanced-file-mover/releases)

### Issue: RamDrive Not Detected

**Solution**: Ensure RamDrive is properly installed and mounted:
1. Go to the **Info** tab
2. Check **RamDrive** section for drive letter and status
3. Verify drive is mounted in Windows Disk Management
4. Try refreshing the Info tab

### Getting Help

For additional support:
- **GitHub Issues**: [Report a bug](https://github.com/u064241/advanced-file-mover/issues)
- **GitHub Discussions**: [Ask a question](https://github.com/u064241/advanced-file-mover/discussions)

---

## 🤝 Contributing

Contributions, issues and feature requests are welcome!

### Development Setup

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR-USERNAME/advanced-file-mover.git`
3. Create virtual environment: `python -m venv .venv`
4. Activate: `.venv\Scripts\Activate.ps1`
5. Install dependencies: `pip install -r requirements.txt`
6. Create feature branch: `git checkout -b feature/YourFeature`
7. Make your changes
8. Commit: `git commit -m "Add YourFeature"`
9. Push: `git push origin feature/YourFeature`
10. Create Pull Request

### Code Style

- Follow PEP 8 conventions
- Use meaningful variable and function names
- Add comments for complex logic
- Update documentation for new features

### Testing

Before submitting a PR:
```powershell
# Run the GUI
.\run_gui.ps1

# Build without installer
pyinstaller --clean gui_customtkinter.spec

# Test installer build
.\build.ps1 -Clean -Setup
```

---

## 📦 Dependencies

### Core Dependencies

```
customtkinter>=5.0.0        # Modern GUI framework
psutil>=5.9.0               # System monitoring
tkinterdnd2>=0.3.0          # Drag and drop support
```

### Optional Dependencies

```
pyinstaller>=6.0            # For building executables
inno-setup                  # For creating Windows installer (system-wide)
```

See `requirements.txt` for complete dependency list.

---

## 📄 License

Distributed under the MIT License. See [LICENSE](LICENSE) file for details.

MIT License - Free to use, modify, and distribute!

---

## 🙏 Acknowledgments

- [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) - Modern GUI framework for Python
- [PyInstaller](https://www.pyinstaller.org/) - Application packaging and distribution
- [Inno Setup](https://jrsoftware.org/isinfo.php) - Professional Windows installer creation
- [psutil](https://github.com/giampaolo/psutil) - Cross-platform system monitoring
- [tkinterdnd2](https://github.com/pmgagne/tkinterdnd2) - Drag and drop support

---

## 👤 Author

**Advanced File Mover Pro** is developed and maintained by **u064241**

- 🔗 GitHub: [@u064241](https://github.com/u064241)
- 📦 Repository: [advanced-file-mover](https://github.com/u064241/advanced-file-mover)
- 🐛 Issues: [GitHub Issues](https://github.com/u064241/advanced-file-mover/issues)

---

## 📈 Roadmap

Future releases may include:

- GPU acceleration for large file transfers
- Advanced batch operations and scheduling
- Network storage optimization
- Plugin system for custom operations
- Cloud storage integration
- Compression during transfer

---

**Thank you for using Advanced File Mover Pro!**

*For updates and information, visit the [GitHub Repository](https://github.com/u064241/advanced-file-mover)*
