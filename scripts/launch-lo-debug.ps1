# Launch LibreOffice with debug logging
# Usage: .\launch-lo-debug.ps1 [-Full] [-NoRestore]
#   -Full      : verbose SAL_LOG (+INFO, slow startup)
#   -NoRestore : skip document recovery on startup

param(
    [switch]$Full,
    [switch]$NoRestore
)

$logFile = Join-Path $HOME "soffice-debug.log"
$pluginLog = Join-Path $HOME "mcp-extension.log"

if ($Full) {
    $env:SAL_LOG = "+INFO+WARN+ERROR"
    Write-Host "[!] Full SAL_LOG - expect slow startup" -ForegroundColor Yellow
} else {
    $env:SAL_LOG = "+WARN+ERROR"
}

Write-Host "SAL_LOG    = $env:SAL_LOG"
Write-Host "LO stderr  -> $logFile"
Write-Host "Plugin log -> $pluginLog"

# Kill existing instances
Get-Process soffice*, soffice.bin -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 2

$loArgs = "--norestore"
if (-not $NoRestore) {
    Write-Host "Recovery disabled (--norestore, use -NoRestore:`$false to enable)"
}

Write-Host "Launching LibreOffice..."
cmd /c "start /b `"`" `"C:\Program Files\LibreOffice\program\soffice.exe`" $loArgs 2>`"$logFile`""
Write-Host "LibreOffice launched. Tail log: Get-Content -Wait $logFile"
