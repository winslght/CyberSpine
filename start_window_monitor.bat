@echo off
setlocal enabledelayedexpansion
title CyberSpine - Window Activity Perceptor

:: 1. Force switch to repository root directory dynamically
cd /d "%~dp0"

:: 2. Resolve virtualenv python binary
set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"

if not exist "!PYTHON_EXE!" (
    echo [WARN] Virtual environment python not found at !PYTHON_EXE!
    echo [WARN] Falling back to system python...
    set "PYTHON_EXE=python"
)

echo ======================================================================
echo  [CyberSpine] Event-Driven Window Activity Monitor
echo  Working Dir : %cd%
echo  Python Path : !PYTHON_EXE!
echo  Exit Hint   : Press Ctrl+C to stop. Window will remain open.
echo ======================================================================
echo.

:: 3. Execute monitor script safely
"!PYTHON_EXE!" "%~dp0scripts\monitor_window_activity.py" --input-monitor %*

echo.
echo ======================================================================
echo  [CyberSpine] Process finished or terminated.
echo ======================================================================
pause
