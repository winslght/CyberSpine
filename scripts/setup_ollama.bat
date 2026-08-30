@echo off
setlocal
cd /d "%~dp0"
echo =======================================================
echo   CyberSpine Local AI Model Setup (Ollama + Qwen2.5)
echo =======================================================

echo [1/3] Checking Ollama installation...
where ollama >nul 2>nul
if %errorlevel% neq 0 (
    echo [INFO] Ollama not found in PATH. Installing via winget...
    winget install --id Ollama.Ollama --exact --accept-source-agreements --accept-package-agreements
) else (
    echo [PASS] Ollama is already installed!
)

echo.
echo [2/3] Starting Ollama background service...
start "" ollama serve >nul 2>nul
timeout /t 3 >nul

echo.
echo [3/3] Pulling optimal local SLM Qwen2.5-3B (or 1.5B)...
ollama pull qwen2.5:3b
if %errorlevel% neq 0 (
    echo [FALLBACK] Pulling lightweight Qwen2.5-1.5B...
    ollama pull qwen2.5:1.5b
)

echo.
echo =======================================================
echo   Local AI Model Ready! Launching CyberSpine Cockpit...
echo =======================================================
call "%~dp0start_cockpit.bat"

pause
