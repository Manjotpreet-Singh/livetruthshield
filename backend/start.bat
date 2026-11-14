@echo off
TITLE LiveTruth Shield Backend
cd /d "%~dp0"
echo ===================================================
echo     LiveTruth Shield - AI Real-Time Fact Checker
echo ===================================================
echo.
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
echo [*] Starting LiveTruth Shield Server on http://localhost:5000 ...
%PYTHON_EXE% main.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [!] Server exited with an error.
)
pause
