<#
.SYNOPSIS
    Kills all running LibreOffice processes.
#>

$processes = @("soffice", "soffice.bin", "soffice.exe", "oosplash")
$killed = 0

foreach ($name in $processes) {
    $procs = Get-Process -Name $name -ErrorAction SilentlyContinue
    foreach ($p in $procs) {
        Write-Host "[OK] Killing $($p.Name) (PID $($p.Id))" -ForegroundColor Yellow
        Stop-Process -Id $p.Id -Force
        $killed++
    }
}

if ($killed -eq 0) {
    Write-Host "[OK] No LibreOffice process running." -ForegroundColor Green
} else {
    Write-Host "[OK] Killed $killed process(es)." -ForegroundColor Green
}
