$LogPath = Join-Path $PSScriptRoot "..\runtime\logs\window_activity.jsonl"
if (-not (Test-Path $LogPath)) {
    Write-Host "尚未生成窗口感知日志。请先运行 scripts\monitor_window_activity.py。" -ForegroundColor Yellow
    exit 1
}
Write-Host "窗口感知实时日志：$LogPath" -ForegroundColor Cyan
Get-Content -Path $LogPath -Wait -Tail 20
