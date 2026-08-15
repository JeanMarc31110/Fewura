@echo off
setlocal EnableExtensions EnableDelayedExpansion
title Build FEWURA PROSPECT 1.0.6
cd /d "%~dp0"

where py >nul 2>nul && (set PY=py) || (set PY=python)
%PY% --version >nul 2>nul || (echo Python 3.11+ requis.& pause & exit /b 1)
findstr /C:"1.0.6" app\main.py >nul || (echo ERREUR: app\main.py n'est pas en version 1.0.6.& pause&exit /b 1)

if not exist ".buildvenv" %PY% -m venv .buildvenv
call ".buildvenv\Scripts\activate.bat" || goto :error
python -m pip install --upgrade pip || goto :error
pip install -r requirements-build.txt || goto :error
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist installer\output rmdir /s /q installer\output
pyinstaller --clean --noconfirm installer\prospect.spec || goto :error
powershell -NoProfile -ExecutionPolicy Bypass -File ".\TESTER_EXE_WINDOWS.ps1" -ExePath ".\dist\FEWURA_Prospect\FEWURA_Prospect.exe"
if errorlevel 1 goto :error
set "ISCC="
for /f "delims=" %%I in ('where ISCC.exe 2^>nul') do if not defined ISCC set "ISCC=%%I"
if not defined ISCC if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not defined ISCC if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if not defined ISCC goto :error
"!ISCC!" installer\FEWURA_Prospect.iss || goto :error
if not exist "installer\output\FEWURA_PROSPECT_Setup_1.0.6.exe" goto :error
echo BUILD + TESTS + SETUP 1.0.6 : OK
pause
exit /b 0
:error
echo ECHEC DE CONSTRUCTION. Aucun Setup livrable.
pause
exit /b 1
