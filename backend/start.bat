@echo off
TITLE LiveTruth Shield Backend
cd /d "%~dp0"
set "PATH=%~dp0;%PATH%"
echo ===================================================
echo     LiveTruth Shield - AI Real-Time Fact Checker
echo ===================================================
echo.
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

for /f "tokens=5" %%a in ('netstat -aon ^| findstr :5000 ^| findstr LISTENING') do (
    taskkill /F /PID %%a >nul 2>&1
)

echo [*] Starting LiveTruth Shield Server on http://localhost:5000 ...
%PYTHON_EXE% main.py
echo.
echo [!] Server exited.
pause
