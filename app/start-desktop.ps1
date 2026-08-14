$projectPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$listener = Get-NetTCPConnection -LocalPort 3000 -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $listener) {
    Start-Process -FilePath "node.exe" -ArgumentList "server.js" -WorkingDirectory $projectPath -WindowStyle Hidden
    Start-Sleep -Milliseconds 900
}
Start-Process -FilePath "pythonw.exe" -ArgumentList (Join-Path $projectPath "desktop_app.py") -WorkingDirectory $projectPath
