$ErrorActionPreference = "Stop"
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    py -3.11 -m venv .venv
}
& ".\.venv\Scripts\python.exe" -m pip install --upgrade pip
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt
if (-not (Get-Command deno -ErrorAction SilentlyContinue)) {
    winget install --id=DenoLand.Deno -e --accept-package-agreements --accept-source-agreements
}
Write-Host "Setup complete. You can also use setup_windows.cmd to avoid ExecutionPolicy issues."
