$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$Python = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { throw "Run setup_windows.cmd first." }
$Version = (& $Python -c "from app import __version__; print(__version__)").Trim()
$Tag = "v$Version"

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    throw "GitHub CLI (gh) not found. Install it and run 'gh auth login'."
}

$Setup = "release\InsightDownloaderSetup-v$Version.exe"
$UpdateZip = "release\InsightDownloader-update.zip"
$Checksum = "release\InsightDownloader-update.zip.sha256"

if (-not (Test-Path $UpdateZip)) {
    throw "Release files not found. Run build_release.cmd first."
}

$Assets = @($UpdateZip, $Checksum)
if (Test-Path $Setup) { $Assets += $Setup }

& gh release create $Tag @Assets --title "Insight Downloader $Tag" --generate-notes
Write-Host "Release $Tag published."
