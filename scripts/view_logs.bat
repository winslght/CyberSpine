@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0view_logs.ps1"
pause
