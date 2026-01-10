# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec per gui_customtkinter.py (GUI app modern, no console)

a = Analysis(
    ['ui/gui_customtkinter.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('i18n\\*.json', 'i18n'),
        ('src\\assets\\flags\\*.png', 'assets\\flags'),
    ],
    hiddenimports=['psutil', 'customtkinter', 'PIL', 'PIL.Image'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludedimports=[],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='AdvancedFileMoverPro',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # ← IMPORTANTE: No console (GUI app)
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon/super_icon.ico',
)

# Niente COLLECT - onefile crea singolo exe
