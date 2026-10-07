$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$Python = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { throw "Run setup_windows.cmd first." }
$Version = (& $Python -c "from app import __version__; print(__version__)").Trim()
$Tag = "v$Version"

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    throw "GitHub CLI (gh) not found. Install it and run 'gh auth login'."
}

$Assets = @(
    "release\InsightDownloader-update.zip",
    "release\InsightDownloader-update.zip.sha256",
    "release\InsightMediaRuntime.7z",
    "release\InsightMediaRuntime.7z.sha256"
)
$Setup = "release\InsightDownloaderSetup-v$Version.exe"
if (Test-Path $Setup) { $Assets += $Setup }

foreach ($Asset in $Assets) {
    if (-not (Test-Path $Asset)) { throw "Missing release asset: $Asset. Run build_release.cmd first." }
}

$NotesArgs = @("--generate-notes")
if (Test-Path "CHANGELOG.md") {
    $NotesArgs = @("--notes-file", "CHANGELOG.md")
}

& gh release create $Tag @Assets --title "Insight Downloader $Tag" @NotesArgs
if ($LASTEXITCODE -ne 0) { throw "GitHub release publish failed." }
Write-Host "Release $Tag published." -ForegroundColor Green
