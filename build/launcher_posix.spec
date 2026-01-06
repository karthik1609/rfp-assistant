# -*- mode: python ; coding: utf-8 -*-

import pathlib
from PyInstaller.utils.hooks import Tree

project_root = pathlib.Path(__file__).resolve().parents[1]
script_path = project_root / "scripts" / "launch_rfp_assistant.py"

datas = [
    (str(project_root / "docker-compose.yml"), "."),
    (str(project_root / ".env_example"), "."),
    (str(project_root / "backend.Dockerfile"), "."),
    (str(project_root / "frontend.Dockerfile"), "."),
    (str(project_root / "Dockerfile"), "."),
    Tree(str(project_root / "backend"), prefix="backend"),
    Tree(str(project_root / "frontend"), prefix="frontend"),
    Tree(str(project_root / "docs"), prefix="docs"),
]

hiddenimports = []

block_cipher = None

a = Analysis(
    [str(script_path)],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
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
    a.zipfiles,
    a.datas,
    [],
    name="rfp-launcher",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="rfp-launcher",
)

