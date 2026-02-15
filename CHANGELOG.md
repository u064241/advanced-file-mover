# Changelog

Tutte le modifiche rilevanti di questo progetto sono documentate in questo file.

## [1.0.0] - 2026-02-15

### ✨ Features

#### 🎯 Core Functionality
- **Drag & Drop Support**: Native tkinterdnd2 integration - trascinare file direttamente sulla listbox sorgente
- **Admin Drag & Drop**: Funziona anche quando l'app esegue con privilegi elevati
- **Multi-file Context Menu via IPC**: Su Named Pipe + file-based aggregation - singola istanza combina tutti i file selezionati
- **Auto-Update da GitHub**: Con launcher script (nessun problema di file lock)
- **Multi-threaded Copy/Move**: Motore configurabile con dimensione buffer regolabile
- **RamDrive Detection**: Riconosce e accelera operazioni su RamDrive
- **Single-Instance Mutex**: Con IPC per integrazione menu contestuale

#### 🎨 Interface & UX
- **CustomTkinter Modern GUI**: Interfaccia moderna e responsive
- **Dark/Light Theme Toggle**: Cambio tema in tempo reale
- **Grid-based Layout**: Sezione progresso sempre ancorata in fondo
- **Non-resizable Window**: Finestra consistente 900×720px
- **High-contrast Progress**: Visualizzazione velocità (MB/s) e ETA
- **Elastic Source Listbox**: Altezza minima 80px, ridimensionabile

#### 🌍 i18n - Multilingua (IT, EN, FR, DE, ES)
- **Auto-detect System Language**: Rileva automaticamente la lingua al primo avvio (fallback: Inglese)
- **Runtime Language Switch**: Tutti i widget, tab, progress bar e dialoghi si aggiornano istantaneamente
- **Context Menu i18n**: Le voci di menu (Copia/Sposta) seguono la lingua dell'app, auto-re-registrazione al cambio lingua
- **Registry Status Translation**: Completa traduzione della sezione "Stato" nel tab "Menu Contestuale"
- **Flag Icons**: Icone bandiera per ogni lingua

#### ⚡ Performance
- **Auto-tuning Buffer/Threads**: Basato su tipo storage (NVMe/SSD/HDD/USB/NAS/RamDrive)
  - NVMe: Buffer 256MB, 12 Thread
  - SSD: Buffer 128MB, 8 Thread
  - HDD: Buffer 80MB, 2 Thread
  - USB: Buffer 64MB, 4 Thread
  - NAS: Buffer 32MB, 2 Thread
  - RamDrive: Buffer 8MB, 16 Thread
- **Faster Startup**: Background tab loading
- **Auto-detect USB/Device**: Polling per insert/removal con refresh automatico Info tab

#### 🔧 Registry & Explorer Integration
- **Windows Explorer Context Menu**: Integrazione (Shift + Right-Click)
- **Submenu con Copy/Move**: Copy [Advanced] e Move [Advanced]
- **Dynamic Registration**: Menu si auto-registra/rimuove al cambio lingua
- **Status Verification**: Verifica stato voci di registro con traduzione multilingua

#### 📦 Installation & Distribution
- **Inno Setup Installer**: Script-based Windows installer con upgrade support
- **PyInstaller One-dir**: Pacchetto senza estrazione temporanea, compatibile con RamDrive
- **Version Auto-sync**: Versione sincronizzata automaticamente in build da `config.json`

### 🐛 Fixes

#### v1.0.0 - Initial Release
- ✅ **Fixed**: Registry status text now fully translatable in all languages (IT, EN, FR, DE, ES)
- ✅ **Fixed**: Menu status section in "Context Menu" tab updates language correctly on language change
- ✅ **Fixed**: All hardcoded Italian strings in registry status are now mapped to i18n keys
- ✅ **Fixed**: Dynamic translation mapping for registry output (copy/copy/move status for File/Folder/Drive)

### 📝 Documentation
- Comprehensive README with installation, usage, and troubleshooting guides
- Detailed changelog (questo file)
- Build instructions per PyInstaller e Inno Setup

### 📂 Project Structure
```
advanced-file-mover/
├── ui/
│   ├── gui_customtkinter.py      # Main GUI
│   └── __init__.py
├── src/
│   ├── file_operations.py         # Copy/move engine
│   ├── update_checker.py          # Auto-update from GitHub
│   ├── ramdrive_handler.py        # RamDrive detection
│   ├── storage_detector.py        # Storage type detection
│   ├── utils.py                   # Utility functions
│   └── __init__.py
├── registry/
│   ├── context_menu.py            # Context menu registration
│   └── __init__.py
├── i18n/
│   ├── it.json                    # Italian
│   ├── en.json                    # English
│   ├── fr.json                    # French
│   ├── de.json                    # German
│   └── es.json                    # Spanish
├── icon/                           # Application icons
├── installer/
│   ├── AdvancedFileMover.iss      # Inno Setup script
│   └── Output/                     # Built installers
├── config.json                     # Application configuration
├── gui_customtkinter.spec         # PyInstaller spec
├── requirements.txt               # Python dependencies
├── build.ps1                      # Build script
├── run_gui.ps1                    # Run GUI script
├── README.md                      # Main documentation
├── CHANGELOG.md                   # This file
└── LICENSE                        # MIT License
```

### 🔄 Known Issues & Limitations
- None at this time. Application is stable for v1.0.0

### 🚀 Next Steps / Future Releases
- GPU acceleration for large file transfers
- Advanced filtering and batch operations
- Network storage optimization
- Plugin system for custom operations

---

## Version History

| Version | Date | Status | Notes |
|---------|------|--------|-------|
| 1.0.0 | 2026-02-15 | Stable | Initial release - Feature complete, all i18n fixes applied |

---

## Guidelines for Updating CHANGELOG.md

1. **Format**: Use [Keep a Changelog](https://keepachangelog.com/) format
2. **Sections**: Features, Fixes, Changed, Deprecated, Removed, Security
3. **Language**: Use English for consistency (Italian comments allowed for clarity)
4. **Date Format**: YYYY-MM-DD
5. **Link Format**: Use [version] in header for GitHub release links

### Example New Entry

```markdown
## [1.0.1] - 2026-02-22

### 🐛 Fixes
- Fixed bug with RamDrive detection on some systems
- Corrected ETA calculation for very large files

### 🔄 Changed
- Updated CustomTkinter to latest version
- Improved performance on USB drives

### ✨ Features
- Added dry-run mode for preview before actual operation
```
