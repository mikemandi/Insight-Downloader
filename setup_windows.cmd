@echo off
setlocal
cd /d "%~dp0"

echo [Insight Downloader] Preparing environment...

where py >nul 2>&1
if errorlevel 1 (
    echo Python Launcher was not found.
    echo Install Python 3.11 or newer from python.org and run this file again.
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

where deno >nul 2>&1
if errorlevel 1 (
    echo [3/3] Deno was not found. Trying to install it with winget...
    where winget >nul 2>&1
    if errorlevel 1 (
        echo winget is not available. Install Deno manually from deno.com.
    ) else (
        winget install --id DenoLand.Deno -e --accept-package-agreements --accept-source-agreements
    )
) else (
    echo [3/3] Deno is already installed.
)

echo.
echo Setup complete.
echo If Deno was installed just now, restart the terminal before launching YouTube downloads.
echo Run: run.cmd
pause
exit /b 0

:error
echo.
echo Setup failed. See the error above.
pause
exit /b 1
