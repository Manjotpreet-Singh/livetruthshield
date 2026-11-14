@echo off
TITLE LiveTruth Shield // Universal Real-Time AI Fact-Checker
color 0B
cls

echo =========================================================================
echo   SHIELD // LiveTruth Universal Real-Time AI Fact-Checking Engine
echo   Powered by Google Gemini 3 + Live Search Grounding
echo =========================================================================
echo.
echo [*] Initializing LiveTruth Shield environment...

cd /d "%~dp0backend"

set "PYTHON_EXE=C:\Users\Acer\anaconda3\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=python"

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

"%PYTHON_EXE%" main.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [!] LiveTruth server stopped with an error code.
    pause
)

