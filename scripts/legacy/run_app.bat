@echo off
setlocal
cd /d "%~dp0"
set "PYTHON_BIN=C:\Users\winslght\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"

if exist "%PYTHON_BIN%" (
    "%PYTHON_BIN%" cyberspine_cockpit.py %*
) else (
    python cyberspine_cockpit.py %*
)

pause
