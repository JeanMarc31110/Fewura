# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all
datas=[('app/templates','app/templates'),('app/static','app/static'),('config','config'),('.env.example','.'),('README.md','.')]
hiddenimports=['uvicorn.logging','uvicorn.loops.auto','uvicorn.protocols.http.auto','uvicorn.protocols.websockets.auto','uvicorn.lifespan.on','multipart']
for package in ['fastapi','starlette','jinja2','pydantic','httpx','bs4','lxml','dns','openpyxl']:
    try:
        d,b,h=collect_all(package); datas+=d; hiddenimports+=h
    except Exception: pass
a=Analysis(['prospect_launcher.py'],pathex=[],binaries=[],datas=datas,hiddenimports=hiddenimports,hookspath=[],hooksconfig={},runtime_hooks=[],excludes=[],noarchive=False)
pyz=PYZ(a.pure)
exe=EXE(pyz,a.scripts,[],exclude_binaries=True,name='FEWURA_Prospect',debug=False,bootloader_ignore_signals=False,strip=False,upx=False,console=False,disable_windowed_traceback=False,argv_emulation=False,icon=None)
coll=COLLECT(exe,a.binaries,a.datas,strip=False,upx=False,upx_exclude=[],name='FEWURA_Prospect')
