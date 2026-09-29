@echo off
setlocal
cd /d "%~dp0"
if "%~1"=="" (
    echo Usage: set_version.cmd 0.5.1
    exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
    echo Run setup_windows.cmd first.
    exit /b 1
)
".venv\Scripts\python.exe" tools\set_version.py %1
