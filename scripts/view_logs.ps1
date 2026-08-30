$LogPath = Join-Path $PSScriptRoot "..\runtime\logs\heartbeat_ticks.log"
$LogPath = (Resolve-Path $LogPath -ErrorAction SilentlyContinue)

if (-not $LogPath) {
    $LogsDir = Join-Path $PSScriptRoot "..\runtime\logs"
    if (-not (Test-Path $LogsDir)) { New-Item -ItemType Directory -Path $LogsDir -Force | Out-Null }
    $LogPath = Join-Path $LogsDir "heartbeat_ticks.log"
    if (-not (Test-Path $LogPath)) { New-Item -ItemType File -Path $LogPath -Force | Out-Null }
}

Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host "  CyberSpine Physical Pacemaker Live Log Viewer" -ForegroundColor Green
Write-Host "  Log File: $LogPath" -ForegroundColor White
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host "Listening to real hardware pacemaker ticks (Ctrl+C to exit)...`n" -ForegroundColor Yellow

Get-Content -Path $LogPath -Wait -Tail 20
