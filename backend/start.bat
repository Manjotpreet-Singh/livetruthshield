@echo off
TITLE LiveTruth Shield Backend
cd /d "%~dp0"
echo ===================================================
echo     LiveTruth Shield - AI Real-Time Fact Checker
echo ===================================================
echo.
set "PYTHON_EXE=C:\Users\Acer\anaconda3\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=python"
echo [*] Starting LiveTruth Shield Server on http://localhost:5000 ...
"%PYTHON_EXE%" main.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [!] Server exited with an error.
)
pause
