@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0build_release.ps1"
if errorlevel 1 (
    echo.
    echo Release build failed.
    pause
    exit /b 1
)
echo.
echo Release build completed.
pause
