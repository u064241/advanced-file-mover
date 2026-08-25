# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec per gui_customtkinter.py (GUI app modern, no console)

import os
from PyInstaller.utils.hooks import get_package_paths

# hook-tkinterdnd2 di pyinstaller-hooks-contrib non conosce ancora le cartelle
# "-tcl9" (aggiunte in tkinterdnd2 0.6.x): bundla solo la variante Tcl 8.x.
# Su Python con Tcl/Tk 9 (es. 3.14 free-threading) questo causa
# "RuntimeError: Unable to load tkdnd library." a runtime. Colmiamo qui il gap
# includendo esplicitamente la cartella win-x64-tcl9 se presente nel venv.
_tkdnd_extra_datas = []
_tkdnd_extra_binaries = []
try:
    _, _tkdnd2_pkg_dir = get_package_paths('tkinterdnd2')
    _tkdnd_tcl9_src = os.path.join(_tkdnd2_pkg_dir, 'tkdnd', 'win-x64-tcl9')
    if os.path.isdir(_tkdnd_tcl9_src):
        _tkdnd_tcl9_dest = os.path.join('tkinterdnd2', 'tkdnd', 'win-x64-tcl9')
        for _f in os.listdir(_tkdnd_tcl9_src):
            _full = os.path.join(_tkdnd_tcl9_src, _f)
            if _f.lower().endswith('.dll'):
                _tkdnd_extra_binaries.append((_full, _tkdnd_tcl9_dest))
            else:
                _tkdnd_extra_datas.append((_full, _tkdnd_tcl9_dest))
except Exception:
    pass

a = Analysis(
    ['ui/gui_customtkinter.py'],
    pathex=[],
    binaries=[*_tkdnd_extra_binaries],
    datas=[
        ('i18n\\*.json', 'i18n'),
        ('src\\assets\\flags\\*.png', 'assets\\flags'),
        *_tkdnd_extra_datas,
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
    [],
    name='AdvancedFileMoverPro',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    console=False,  # ← IMPORTANTE: No console (GUI app)
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon/super_icon.ico',
)

# COLLECT per one-dir (cartella con file sciolti, più veloce da eseguire)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='AdvancedFileMoverPro',
)
