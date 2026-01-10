# Build script per GUI CustomTkinter con PyInstaller
# Pulizia automatica e compilazione

param(
    [switch]$Clean = $false,
    [switch]$Setup = $false,
    [string]$IsccPath = 'C:\Program Files (x86)\Inno Setup 6\ISCC.exe',
    [switch]$Help = $false
)

# Assicura working dir corretto (la cartella del progetto)
try {
    if ($PSScriptRoot) {
        Set-Location $PSScriptRoot
    }
} catch {
}

# Usa preferibilmente Python della venv (stessa della GUI)
$VenvPython = 'C:\SOURCECODE\.venv312\Scripts\python.exe'
$PythonExe = if (Test-Path $VenvPython) { $VenvPython } else { 'python' }

# Colori
$Green = 'Green'
$Yellow = 'Yellow'
$Red = 'Red'
$Cyan = 'Cyan'

# Help
if ($Help) {
    $InnerWidth = 42
    $Title = "Advanced File Mover - BUILD"
    $Pad = [Math]::Max(0, $InnerWidth - $Title.Length)
    $LeftPad = [Math]::Floor($Pad / 2)
    $RightPad = $Pad - $LeftPad

    $Top = "╔" + ("═" * $InnerWidth) + "╗"
    $Mid = "║" + (" " * $LeftPad) + $Title + (" " * $RightPad) + "║"
    $Bot = "╚" + ("═" * $InnerWidth) + "╝"

    Write-Host "`n$Top" -ForegroundColor $Cyan
    Write-Host $Mid -ForegroundColor $Cyan
    Write-Host "$Bot`n" -ForegroundColor $Cyan
    
    Write-Host "UTILIZZO:`n" -ForegroundColor $Yellow
    Write-Host "  .\build.ps1              - Build normale (pulizia cartelle dist/build)" -ForegroundColor $Green
    Write-Host "  .\build.ps1 -Clean       - Build con --clean per PyInstaller" -ForegroundColor $Green
    Write-Host "  .\build.ps1 -Setup       - Dopo il build, compila anche Setup.exe (Inno Setup) e rimuove ./dist se OK" -ForegroundColor $Green
    Write-Host "  .\build.ps1 -Setup -IsccPath <percorso\\ISCC.exe> - Override percorso ISCC.exe" -ForegroundColor $Green
    Write-Host "  .\build.ps1 -Help        - Mostra questo help`n" -ForegroundColor $Green
    
    Write-Host "RISULTATO:`n" -ForegroundColor $Yellow
    Write-Host "  ✓ dist/AdvancedFileMoverPro.exe   - Eseguibile compilato (singolo file)" -ForegroundColor $Green
    Write-Host "  ✓ installer/Output/*Setup*.exe    - Setup.exe generato da Inno Setup (se usi -Setup)" -ForegroundColor $Green
    Write-Host "  ✓ build/                 - Build temporanei (rimosso dopo)" -ForegroundColor $Green
    exit
}

$BuildTitle = "Building Advanced File Mover..."
$BuildInnerWidth = 40
$BuildLeftPad = [math]::Floor(($BuildInnerWidth - $BuildTitle.Length) / 2)
if ($BuildLeftPad -lt 0) { $BuildLeftPad = 0 }
$BuildRightPad = $BuildInnerWidth - $BuildTitle.Length - $BuildLeftPad
if ($BuildRightPad -lt 0) { $BuildRightPad = 0 }
$BuildTop = "╔" + ("═" * $BuildInnerWidth) + "╗"
$BuildMid = "║" + (" " * $BuildLeftPad) + $BuildTitle + (" " * $BuildRightPad) + "║"
$BuildBot = "╚" + ("═" * $BuildInnerWidth) + "╝"
Write-Host "`n$BuildTop" -ForegroundColor $Cyan
Write-Host $BuildMid -ForegroundColor $Cyan
Write-Host "$BuildBot`n" -ForegroundColor $Cyan

# Pulizia cartelle dist e build
Write-Host "[1/3] 🧹 Pulizia cartelle precedenti..." -ForegroundColor $Yellow

if (Test-Path 'dist') {
    Write-Host "     Rimuovo ./dist" -ForegroundColor $Cyan
    Remove-Item -Recurse -Force 'dist'
}

if (Test-Path 'build') {
    Write-Host "     Rimuovo ./build" -ForegroundColor $Cyan
    Remove-Item -Recurse -Force 'build'
}

if (Test-Path '*.spec.build') {
    Write-Host "     Rimuovo *.spec.build" -ForegroundColor $Cyan
    Remove-Item -Force '*.spec.build'
}

Write-Host "     ✓ Pulizia completata`n" -ForegroundColor $Green

# Verifica PyInstaller
Write-Host "[2/3] 🔍 Verifica PyInstaller..." -ForegroundColor $Yellow

$PyInstaller = & $PythonExe -m pip show pyinstaller 2>&1 | Select-String "Name: pyinstaller"
if (-not $PyInstaller) {
    Write-Host "     ❌ PyInstaller non installato!`n" -ForegroundColor $Red
    Write-Host "     Installa con: pip install pyinstaller`n" -ForegroundColor $Yellow
    exit 1
}

Write-Host "     ✓ PyInstaller trovato`n" -ForegroundColor $Green

# Build con PyInstaller
Write-Host "[3/3] 🔨 Compilazione con PyInstaller..." -ForegroundColor $Yellow

$BuildArgs = @('--noconfirm', 'gui_customtkinter.spec')
if ($Clean) {
    $BuildArgs = @('--clean') + $BuildArgs
    Write-Host "     Flag --clean attivato`n" -ForegroundColor $Cyan
}

& $PythonExe -m PyInstaller @BuildArgs

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✅ BUILD COMPLETATO CON SUCCESSO!`n" -ForegroundColor $Green
    Write-Host "📦 Output: dist/AdvancedFileMoverPro.exe" -ForegroundColor $Green
    Write-Host "📍 Dimensione: $(if (Test-Path 'dist/AdvancedFileMoverPro.exe') { "{0:N0} KB" -f ((Get-Item 'dist/AdvancedFileMoverPro.exe').Length / 1KB) } else { 'N/A' })`n" -ForegroundColor $Green
    
    # Copia config.json vicino all'exe
    Write-Host "📋 Copia config.json in dist/..." -ForegroundColor $Yellow
    if (Test-Path 'config.json') {
        Copy-Item 'config.json' -Destination 'dist/config.json' -Force
        Write-Host "   ✓ config.json copiato" -ForegroundColor $Green
    }
    
    # Copia icone in dist/Icon/ (cartella ordinata)
    Write-Host "🎨 Copia icone in dist/Icon/..." -ForegroundColor $Yellow
    $IconDir = 'dist/Icon'
    if (-not (Test-Path $IconDir)) {
        New-Item -ItemType Directory -Path $IconDir -Force | Out-Null
        Write-Host "   ✓ Cartella Icon creata" -ForegroundColor $Green
    }
    
    $SourceIconDir = 'icon'
    if (Test-Path "$SourceIconDir/copy_icon.ico") {
        Copy-Item "$SourceIconDir/copy_icon.ico" -Destination "$IconDir/copy_icon.ico" -Force
        Write-Host "   ✓ copy_icon.ico copiato" -ForegroundColor $Green
    }
    if (Test-Path "$SourceIconDir/move_icon.ico") {
        Copy-Item "$SourceIconDir/move_icon.ico" -Destination "$IconDir/move_icon.ico" -Force
        Write-Host "   ✓ move_icon.ico copiato" -ForegroundColor $Green
    }
    if (Test-Path "$SourceIconDir/super_icon.ico") {
        Copy-Item "$SourceIconDir/super_icon.ico" -Destination "$IconDir/super_icon.ico" -Force
        Write-Host "   ✓ super_icon.ico copiato" -ForegroundColor $Green
    }

    # Copia traduzioni (i18n) in dist/i18n/
    Write-Host "🌐 Copia traduzioni in dist/i18n/..." -ForegroundColor $Yellow
    $I18nDir = 'dist/i18n'
    if (-not (Test-Path $I18nDir)) {
        New-Item -ItemType Directory -Path $I18nDir -Force | Out-Null
    }
    $SourceI18nDir = 'i18n'
    if (Test-Path $SourceI18nDir) {
        Copy-Item "$SourceI18nDir\*.json" -Destination $I18nDir -Force
        Write-Host "   ✓ i18n copiato" -ForegroundColor $Green
    } else {
        Write-Host "   ⚠️ Cartella i18n non trovata" -ForegroundColor $Yellow
    }

    # Copia bandiere (assets/flags) in dist/assets/flags/
    Write-Host "🏳️ Copia bandiere in dist/assets/flags/..." -ForegroundColor $Yellow
    $FlagsDir = 'dist/assets/flags'
    if (-not (Test-Path $FlagsDir)) {
        New-Item -ItemType Directory -Path $FlagsDir -Force | Out-Null
    }
    $SourceFlagsDir = 'src/assets/flags'
    if (Test-Path $SourceFlagsDir) {
        Copy-Item "$SourceFlagsDir\*.png" -Destination $FlagsDir -Force
        Write-Host "   ✓ bandiere copiate" -ForegroundColor $Green
    } else {
        Write-Host "   ⚠️ Cartella src/assets/flags non trovata" -ForegroundColor $Yellow
    }

    # (Opzionale) Compila installer Inno Setup
    if ($Setup) {
        Write-Host "`n[4/4] 📦 Compilazione Setup.exe (Inno Setup)..." -ForegroundColor $Yellow

        $IssFile = Join-Path $PSScriptRoot 'installer\AdvancedFileMover.iss'
        if (-not (Test-Path $IssFile)) {
            Write-Host "     ❌ Script .iss non trovato: $IssFile" -ForegroundColor $Red
            exit 1
        }

        if (-not (Test-Path $IsccPath)) {
            Write-Host "     ❌ ISCC.exe non trovato: $IsccPath" -ForegroundColor $Red
            Write-Host "     Suggerimento: installa Inno Setup o passa -IsccPath con il percorso corretto." -ForegroundColor $Yellow
            exit 1
        }

        # Leggi versione da config.json e passala a Inno Setup
        $ConfigFile = Join-Path $PSScriptRoot 'config.json'
        $AppVersion = "1.0.0"
        if (Test-Path $ConfigFile) {
            try {
                $Config = Get-Content $ConfigFile | ConvertFrom-Json
                if ($Config.version) {
                    $AppVersion = $Config.version
                    Write-Host "     📋 Versione letta da config.json: $AppVersion" -ForegroundColor $Cyan
                }
            } catch {
                Write-Host "     ⚠️ Errore lettura config.json, uso versione di default: $AppVersion" -ForegroundColor $Yellow
            }
        }

        & "$IsccPath" "/D{#MyAppVersion=$AppVersion" "$IssFile"
        if ($LASTEXITCODE -eq 0) {
            Write-Host "     ✓ Setup.exe compilato" -ForegroundColor $Green

            # Cleanup: dist viene rigenerata ad ogni build, quindi se Setup.exe è OK la rimuoviamo.
            try {
                if (Test-Path 'dist') {
                    Write-Host "     🧹 Rimuovo ./dist (Setup.exe creato con successo)..." -ForegroundColor $Yellow
                    Remove-Item -Recurse -Force 'dist'
                    Write-Host "     ✓ dist rimosso" -ForegroundColor $Green
                }
            } catch {
                Write-Host "     ⚠️ Impossibile rimuovere ./dist: $($_.Exception.Message)" -ForegroundColor $Yellow
            }
        } else {
            Write-Host "     ❌ Compilazione Setup.exe fallita" -ForegroundColor $Red
            exit 1
        }
    }

} else {
    Write-Host "`n❌ BUILD FALLITO!" -ForegroundColor $Red
    exit 1
}

# Pulizia build folder
if (Test-Path 'build') {
    Write-Host "🧹 Rimuovo cartella build temporanea..." -ForegroundColor $Yellow
    Remove-Item -Recurse -Force 'build'
    Write-Host "   ✓ Rimosso`n" -ForegroundColor $Green
}

Write-Host "════════════════════════════════════════`n" -ForegroundColor $Cyan
