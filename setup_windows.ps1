$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    py -3.11 -m venv .venv
}

& ".\.venv\Scripts\python.exe" -m pip install --upgrade pip
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\tools\fetch_qjs.ps1"

Write-Host "Setup complete."
Write-Host "QuickJS replaces the much larger Deno runtime in v0.6."
