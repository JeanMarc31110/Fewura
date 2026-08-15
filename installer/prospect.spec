# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
from PyInstaller.utils.hooks import collect_all

ROOT = Path(SPECPATH).resolve().parent


datas = [
    (str(ROOT / 'app' / 'templates'), 'app/templates'),
    (str(ROOT / 'app' / 'static'), 'app/static'),
    (str(ROOT / 'config'), 'config'),
    (str(ROOT / '.env.example'), '.'),
    (str(ROOT / 'README.md'), '.'),
]
binaries = []
hiddenimports = []

# Ces paquets utilisent des imports dynamiques. On les collecte explicitement
# pour que le binaire Windows teste soit autonome et reproductible.
for package in [
    'uvicorn',
    'fastapi',
    'starlette',
    'jinja2',
    'pydantic',
    'httpx',
    'bs4',
    'lxml',
    'dns',
    'openpyxl',
    'multipart',
    'ddgs',
]:
    try:
        d, b, h = collect_all(package)
        datas += d
        binaries += b
        hiddenimports += h
    except Exception:
        pass

hiddenimports += [
    'uvicorn.logging',
    'uvicorn.loops.asyncio',
    'uvicorn.loops.auto',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.http.h11_impl',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.lifespan.on',
    'multipart',
    'ddgs',
]


a = Analysis(
    [str(ROOT / 'prospect_launcher.py')],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
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
    [],
    exclude_binaries=True,
    name='FEWURA_Prospect',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    icon=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='FEWURA_Prospect',
)
