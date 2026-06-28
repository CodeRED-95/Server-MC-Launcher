# -*- mode: python ; coding: utf-8 -*-

import os

block_cipher = None
project_dir = os.getcwd()

datas = [
    (os.path.join(project_dir, "assets"), "assets"),
]

a = Analysis(
    ["main.py"],
    pathex=[project_dir],
    binaries=[],
    datas=datas,
    hiddenimports=[
        "PyQt6.QtCore",
        "PyQt6.QtGui",
        "PyQt6.QtWidgets",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="ServerMCLauncher",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(project_dir, "assets", "app_icon.png") if os.path.exists(os.path.join(project_dir, "assets", "app_icon.png")) else None,
)
