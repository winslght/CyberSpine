@echo off
setlocal
pushd "%~dp0"

set "PYTHON=C:\Users\winslght\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if not exist "%PYTHON%" set "PYTHON=python"

echo =======================================================
echo   CyberSpine Neural Cockpit Launcher (WinUI 3.0)
echo   Working Directory: %CD%
echo =======================================================
echo.

"%PYTHON%" cyberspine_cockpit.py %*
if errorlevel 1 (
    echo.
    echo [ERROR] Application exited with error.
    pause
)
