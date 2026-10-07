@echo off
setlocal
cd /d "%~dp0"

echo [Insight Downloader] Preparing development environment...

where py >nul 2>&1
if errorlevel 1 (
    echo Python Launcher was not found.
    echo Install Python 3.11 or newer and run this file again.
    pause
    exit /b 1
)

py -3.11 --version >nul 2>&1
if errorlevel 1 (
    echo Python 3.11 is not installed.
    echo Try: py install 3.11
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo [1/3] Creating virtual environment...
    py -3.11 -m venv .venv
)

echo [2/3] Installing Python dependencies...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto :error
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :error

echo [3/3] Preparing lightweight QuickJS runtime...
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\tools\fetch_qjs.ps1"
if errorlevel 1 goto :error

echo.
echo Setup complete.
echo Run: run.cmd
pause
exit /b 0

:error
echo.
echo Setup failed. See the error above.
pause
exit /b 1
