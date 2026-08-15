@echo off
setlocal EnableExtensions
title Build FEWURA PROSPECT
cd /d "%~dp0"

where py >nul 2>nul && (set PY=py) || (set PY=python)
%PY% --version >nul 2>nul || (echo Python 3.11+ requis.& pause & exit /b 1)

findstr /C:"from app.paths import database_path" app\db.py >nul || (
  echo ERREUR: le code local n'est pas a jour. Lancez: git pull
  pause
  exit /b 1
)

if not exist ".buildvenv" %PY% -m venv .buildvenv
call ".buildvenv\Scripts\activate.bat"
python -m pip install --upgrade pip || goto :error
pip install -r requirements-build.txt || goto :error

if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist installer\output rmdir /s /q installer\output

pyinstaller --clean --noconfirm installer\prospect.spec || goto :error

set ISCC=
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
if not defined ISCC (
  for /r "%LOCALAPPDATA%\Programs" %%I in (ISCC.exe) do if not defined ISCC set "ISCC=%%I"
)
if not defined ISCC (echo Inno Setup 6 requis ou introuvable.& pause & exit /b 2)

echo Inno Setup: %ISCC%
"%ISCC%" installer\FEWURA_Prospect.iss || goto :error

echo Setup cree : installer\output\FEWURA_PROSPECT_Setup_1.0.1.exe
if exist installer\output\FEWURA_PROSPECT_Setup_1.0.1.exe (
  echo BUILD OK
) else (
  echo ERREUR: le Setup attendu n'a pas ete cree.
  goto :error
)
pause & exit /b 0

:error
echo ECHEC DE CONSTRUCTION.
pause & exit /b 1
