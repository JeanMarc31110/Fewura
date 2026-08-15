param(
    [Parameter(Mandatory=$true)]
    [string]$ExePath
)

$ErrorActionPreference = 'Stop'
$exe = (Resolve-Path $ExePath).Path
$port = Get-Random -Minimum 18100 -Maximum 18999
$dataRoot = Join-Path $env:TEMP ("FEWURA_PROSPECT_SMOKE_" + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Force -Path $dataRoot | Out-Null

$oldPort = $env:FEWURA_PORT
$oldNoBrowser = $env:FEWURA_NO_BROWSER
$oldData = $env:FEWURA_DATA_DIR
$env:FEWURA_PORT = [string]$port
$env:FEWURA_NO_BROWSER = '1'
$env:FEWURA_DATA_DIR = $dataRoot

$proc = $null
try {
    $proc = Start-Process -FilePath $exe -PassThru
    $health = $null
    for ($i = 0; $i -lt 80; $i++) {
        if ($proc.HasExited) { throw "Le binaire s'est arrete pendant le test avec le code $($proc.ExitCode)." }
        try {
            $health = Invoke-RestMethod -Uri ("http://127.0.0.1:{0}/health" -f $port) -TimeoutSec 1
            if ($health.ok -eq $true) { break }
        } catch {}
        Start-Sleep -Milliseconds 250
    }
    if (-not $health -or $health.ok -ne $true) { throw 'Le endpoint /health du binaire compile ne repond pas.' }
    if ($health.version -ne '1.0.4') { throw "Version inattendue du binaire: $($health.version)" }

    Invoke-WebRequest -UseBasicParsing -Uri ("http://127.0.0.1:{0}/" -f $port) -TimeoutSec 5 | Out-Null
    Invoke-WebRequest -UseBasicParsing -Uri ("http://127.0.0.1:{0}/export/csv" -f $port) -TimeoutSec 10 -OutFile (Join-Path $dataRoot 'download.csv')
    Invoke-WebRequest -UseBasicParsing -Uri ("http://127.0.0.1:{0}/export/xlsx" -f $port) -TimeoutSec 10 -OutFile (Join-Path $dataRoot 'download.xlsx')

    $db = Join-Path $dataRoot 'data\prospect.db'
    $csv = Join-Path $dataRoot 'exports\prospects.csv'
    $xlsx = Join-Path $dataRoot 'exports\prospects.xlsx'
    foreach ($required in @($db, $csv, $xlsx)) {
        if (-not (Test-Path $required)) { throw "Fichier attendu non cree: $required" }
    }
    Write-Host 'EXE SMOKE TEST OK' -ForegroundColor Green
    exit 0
}
catch {
    Write-Host ('EXE SMOKE TEST ECHEC: ' + $_.Exception.Message) -ForegroundColor Red
    $log = Join-Path $dataRoot 'logs\startup-error.log'
    if (Test-Path $log) {
        Write-Host '--- startup-error.log ---'
        Get-Content $log
        Write-Host '-------------------------'
    }
    exit 1
}
finally {
    if ($proc -and -not $proc.HasExited) {
        Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
        try { $proc.WaitForExit() } catch {}
    }
    if ($null -eq $oldPort) { Remove-Item Env:FEWURA_PORT -ErrorAction SilentlyContinue } else { $env:FEWURA_PORT = $oldPort }
    if ($null -eq $oldNoBrowser) { Remove-Item Env:FEWURA_NO_BROWSER -ErrorAction SilentlyContinue } else { $env:FEWURA_NO_BROWSER = $oldNoBrowser }
    if ($null -eq $oldData) { Remove-Item Env:FEWURA_DATA_DIR -ErrorAction SilentlyContinue } else { $env:FEWURA_DATA_DIR = $oldData }
}
