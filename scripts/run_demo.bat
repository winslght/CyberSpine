@echo off
setlocal
cd /d "%~dp0"
set "PYTHON_BIN=C:\Users\winslght\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"

if exist "%PYTHON_BIN%" (
    "%PYTHON_BIN%" demo_minimal_loop.py %*
) else (
    python demo_minimal_loop.py %*
)

pause
