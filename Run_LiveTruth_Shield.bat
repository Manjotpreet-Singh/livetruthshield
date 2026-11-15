@echo off
TITLE LiveTruth Shield // Universal Real-Time AI Fact-Checker
color 0B
cls

echo =========================================================================
echo   SHIELD // LiveTruth Universal Real-Time AI Fact-Checking Engine
echo   Powered by live AI search (Gemini / DeepSeek / Groq)
echo =========================================================================
echo.
echo [*] Initializing LiveTruth Shield environment...

if exist "%~dp0Live Shield\backend" (
    cd /d "%~dp0Live Shield\backend"
) else if exist "%~dp0backend" (
    cd /d "%~dp0backend"
) else (
    cd /d "%~dp0backend"
)

set "PATH=%CD%;%~dp0backend;%PATH%"

set "PYTHON_EXE=python"
where python >nul 2>&1 || set "PYTHON_EXE=py -3"

%PYTHON_EXE% -c "import fastapi, uvicorn, httpx, dotenv" >nul 2>&1
if errorlevel 1 (
    echo [*] Installing missing dependencies...
    %PYTHON_EXE% -m pip install -q -r requirements.txt
    if errorlevel 1 (
        echo [!] Dependency install failed. Check your internet connection.
        pause
        exit /b 1
    )
) else (
    echo [*] Python environment and core dependencies verified.
)

if exist "ffmpeg.exe" (
    echo [+] ffmpeg audio engine verified and active.
) else (
    where ffmpeg >nul 2>&1 && (
        echo [+] ffmpeg audio engine verified and active.
    ) || (
        echo [*] Note: ffmpeg optional for non-captioned videos.
    )
)
if not exist ".env" echo [!] No backend\.env found - add GEMINI_API_KEY=... or GROQ_API_KEY=...

echo [*] Using Python interpreter: %PYTHON_EXE%
echo [*] Checking port 5000...

for /f "tokens=5" %%a in ('netstat -aon ^| findstr :5000 ^| findstr LISTENING') do (
    taskkill /F /PID %%a >nul 2>&1
)

echo [*] Starting LiveTruth Shield server on http://localhost:5000 ...
echo.
echo =========================================================================
echo   Web Console:      http://localhost:5000
echo   Chrome Extension: Load 'Live Shield\extension' in chrome://extensions
echo =========================================================================
echo.

%PYTHON_EXE% main.py

echo.
echo [!] LiveTruth server has stopped.
pause
