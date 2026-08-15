@echo off
setlocal
cd /d "%~dp0"
set SETUP=installer\output\FEWURA_PROSPECT_Setup_1.0.0.exe
if not exist "%SETUP%" (echo Setup introuvable.& pause & exit /b 1)
where signtool >nul 2>nul || (echo Windows SDK SignTool requis.& pause & exit /b 1)
if "%FEWURA_CERT_SHA1%"=="" (echo FEWURA_CERT_SHA1 absent.& pause & exit /b 1)
signtool sign /sha1 "%FEWURA_CERT_SHA1%" /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 "%SETUP%" || exit /b 1
signtool verify /pa /v "%SETUP%" || exit /b 1
echo Signature valide.& pause
