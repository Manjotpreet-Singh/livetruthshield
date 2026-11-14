@echo off
TITLE LiveTruth Shield // Universal Real-Time AI Fact-Checker
color 0B
cls

echo =========================================================================
echo   SHIELD // LiveTruth Universal Real-Time AI Fact-Checking Engine
echo   Powered by live AI search (Gemini / DeepSeek)
echo =========================================================================
echo.
echo [*] Initializing LiveTruth Shield environment...

cd /d "%~dp0backend"

set "PYTHON_EXE=python"
where python >nul 2>&1 || set "PYTHON_EXE=py -3"
echo [*] Installing/checking dependencies (first run takes a minute)...
%PYTHON_EXE% -m pip install -q -r requirements.txt
if errorlevel 1 (
    echo [!] Dependency install failed. Check your internet connection.
    pause
    exit /b 1
)
if not exist ".env" echo [!] No backend\.env found - add GEMINI_API_KEY=... or DEEPSEEK_API_KEY=... or use the dashboard AI Config.

echo [*] Using Python interpreter: %PYTHON_EXE%
echo [*] Freeing port 5000 if previously occupied...

for /f "tokens=5" %%a in ('netstat -aon ^| findstr :5000 ^| findstr LISTENING') do (
    taskkill /F /PID %%a >nul 2>&1
)

echo [*] Starting LiveTruth Shield server on http://localhost:5000 ...
echo [*] Web console and Chrome Extension will connect to port 5000.
echo.
echo =========================================================================
echo   Web Console:      http://localhost:5000
echo   Chrome Extension: Load 'livetruth-shield\extension' in chrome://extensions
echo =========================================================================
echo.

%PYTHON_EXE% main.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [!] LiveTruth server stopped with an error code.
    pause
)

