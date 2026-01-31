; Inno Setup script - Advanced File Mover Pro
; Build prerequisites:
; 1) Esegui .\build.ps1 per generare dist\AdvancedFileMoverPro.exe + Icon\ + config.json
; 2) Compila con ISCC.exe (Inno Setup)
; Nota: versione letta automaticamente da config.json durante build.ps1

#ifndef MyAppVersion
  #define MyAppVersion "1.0.12"
#endif

[Setup]
AppName=Advanced File Mover Pro
AppVersion={#MyAppVersion}
AppVerName=Advanced File Mover Pro v{#MyAppVersion}
OutputBaseFilename=AdvancedFileMover_{#MyAppVersion}_Setup
DefaultDirName={autopf}\Advanced File Mover Pro
DefaultGroupName=Advanced File Mover Pro
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
SetupIconFile={#SourcePath}\..\dist\Icon\super_icon.ico
CloseApplications=yes
RestartApplications=no

[Files]
Source: "{#SourcePath}\..\dist\AdvancedFileMoverPro.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourcePath}\..\dist\config.json"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourcePath}\..\dist\Icon\*"; DestDir: "{app}\Icon"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#SourcePath}\..\dist\i18n\*"; DestDir: "{app}\i18n"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#SourcePath}\..\dist\assets\flags\*"; DestDir: "{app}\assets\flags"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Advanced File Mover Pro"; Filename: "{app}\AdvancedFileMoverPro.exe"
Name: "{commondesktop}\Advanced File Mover Pro"; Filename: "{app}\AdvancedFileMoverPro.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Crea un collegamento sul Desktop"; GroupDescription: "Collegamenti:"; Flags: unchecked

[Run]
; Registra il menu contestuale alla fine dell'installazione.
; Nota: il menu è "Extended" → compare solo con Shift + tasto destro.
Filename: "{app}\AdvancedFileMoverPro.exe"; Parameters: "--register-context-menu"; Description: "Registra il menu contestuale di Windows (Shift + tasto destro)"; Flags: postinstall waituntilterminated

[UninstallRun]
; Rimuove il menu contestuale prima della disinstallazione
Filename: "{app}\AdvancedFileMoverPro.exe"; Parameters: "--unregister-context-menu"; Flags: waituntilterminated; RunOnceId: "UnregisterContextMenu"













