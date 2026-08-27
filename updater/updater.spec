# -*- mode: python ; coding: utf-8 -*-

import sys


executable_name = "Aggiorna-GPS-Windows" if sys.platform == "win32" else "Aggiorna GPS"

a = Analysis(
    ["updater.py"],
    pathex=[],
    binaries=[],
    datas=[],
    # certifi non e' importato al livello del modulo, ma serve incluso: porta
    # l'elenco dei certificati HTTPS, che il Python del pacchetto non trova nel
    # sistema (su macOS senza di esso ogni download falliva).
    hiddenimports=["tkinter", "tkinter.messagebox", "tkinter.ttk", "certifi"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name=executable_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

if sys.platform == "darwin":
    app = BUNDLE(
        exe,
        name="Aggiorna GPS.app",
        icon=None,
        bundle_identifier="com.indiegala.gps.updater",
        version="1.2.0",
        info_plist={
            "CFBundleDisplayName": "Aggiorna GPS",
            "LSMinimumSystemVersion": "11.0",
            "NSHighResolutionCapable": True,
        },
    )
