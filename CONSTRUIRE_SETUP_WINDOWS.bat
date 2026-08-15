@echo off
setlocal EnableExtensions EnableDelayedExpansion
title Build FEWURA PROSPECT 1.0.2
cd /d "%~dp0"

where py >nul 2>nul && (set PY=py) || (set PY=python)
%PY% --version >nul 2>nul || (echo Python 3.11+ requis.& pause & exit /b 1)

findstr /C:"from app.paths import database_path" app\db.py >nul || (
  echo ERREUR: app\db.py local n'est pas a jour. Lancez git pull.
  pause
  exit /b 1
)
findstr /C:"log_config=None" prospect_launcher.py >nul || (
  echo ERREUR: prospect_launcher.py local n'est pas a jour. Lancez git pull.
  pause
  exit /b 1
)
findstr /C:"1.0.2" app\main.py >nul || (
  echo ERREUR: app\main.py local n'est pas en version 1.0.2. Lancez git pull.
  pause
  exit /b 1
)

if not exist ".buildvenv" %PY% -m venv .buildvenv
call ".buildvenv\Scripts\activate.bat" || goto :error
python -m pip install --upgrade pip || goto :error
pip install -r requirements-build.txt || goto :error

if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist installer\output rmdir /s /q installer\output

pyinstaller --clean --noconfirm installer\prospect.spec || goto :error

if not exist "dist\FEWURA_Prospect\FEWURA_Prospect.exe" (
  echo ERREUR: l'EXE PyInstaller n'a pas ete cree.
  goto :error
)

echo.
echo === TEST DU VRAI EXE COMPILE ===
powershell -NoProfile -ExecutionPolicy Bypass -File ".\TESTER_EXE_WINDOWS.ps1" -ExePath ".\dist\FEWURA_Prospect\FEWURA_Prospect.exe"
if errorlevel 1 (
  echo ERREUR: le binaire compile a echoue aux tests. Aucun Setup ne sera produit.
  goto :error
)

set "ISCC="
for /f "delims=" %%I in ('where ISCC.exe 2^>nul') do if not defined ISCC set "ISCC=%%I"
if not defined ISCC if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not defined ISCC if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if not defined ISCC if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
if not defined ISCC if defined ChocolateyInstall if exist "%ChocolateyInstall%\bin\ISCC.exe" set "ISCC=%ChocolateyInstall%\bin\ISCC.exe"

if not defined ISCC if defined ChocolateyInstall (
  for /r "%ChocolateyInstall%" %%I in (ISCC.exe) do if not defined ISCC set "ISCC=%%I"
)
if not defined ISCC (
  for /r "%ProgramFiles%" %%I in (ISCC.exe) do if not defined ISCC set "ISCC=%%I"
)
if not defined ISCC if defined ProgramFiles(x86) (
  for /r "%ProgramFiles(x86)%" %%I in (ISCC.exe) do if not defined ISCC set "ISCC=%%I"
)
if not defined ISCC if exist "%LOCALAPPDATA%" (
  for /r "%LOCALAPPDATA%" %%I in (ISCC.exe) do if not defined ISCC set "ISCC=%%I"
)

if not defined ISCC (
  echo Inno Setup 6 est installe mais ISCC.exe reste introuvable.
  goto :error
)

echo Inno Setup: !ISCC!
"!ISCC!" installer\FEWURA_Prospect.iss || goto :error

if not exist "installer\output\FEWURA_PROSPECT_Setup_1.0.2.exe" (
  echo ERREUR: le Setup 1.0.2 attendu n'a pas ete cree.
  goto :error
)

echo.
echo ========================================
echo BUILD + EXE SMOKE TEST + SETUP : OK
echo installer\output\FEWURA_PROSPECT_Setup_1.0.2.exe
echo ========================================
pause
exit /b 0

:error
echo.
echo ECHEC DE CONSTRUCTION. Le Setup n'est pas considere livrable.
pause
exit /b 1
