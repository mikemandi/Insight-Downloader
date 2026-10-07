$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$Python = ".\.venv\Scripts\python.exe"
$MainDist = "dist\Insight Downloader"
$ReleaseDir = "release"
$ReleaseConfigPath = "release_config.json"

if (-not (Test-Path $Python)) {
    throw "Virtual environment not found. Run setup_windows.cmd first."
}

$Version = (& $Python -c "from app import __version__; print(__version__)").Trim()

Write-Host "[0/7] Preparing build tools..."
& $Python -m pip install --upgrade pyinstaller pillow py7zr
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\tools\fetch_qjs.ps1"
& $Python tools\generate_version_info.py | Out-Null

if (-not (Test-Path "bin\qjs.exe")) {
    throw "bin\qjs.exe is missing. QuickJS is required for YouTube support."
}
if (-not (Test-Path "bin\ffmpeg.exe") -or -not (Test-Path "bin\ffprobe.exe")) {
    throw "bin\ffmpeg.exe and bin\ffprobe.exe are required to create InsightMediaRuntime.7z."
}

if (Test-Path "dist") { Remove-Item "dist" -Recurse -Force }
if (Test-Path "release") { Remove-Item "release" -Recurse -Force }
New-Item -ItemType Directory -Path $ReleaseDir | Out-Null

Write-Host "[1/7] Building lightweight desktop app..."
& $Python -m PyInstaller `
    --noconfirm `
    --clean `
    --windowed `
    --optimize 2 `
    --name "Insight Downloader" `
    --icon "app\assets\insight.ico" `
    --version-file "installer\windows_version_info.txt" `
    --paths "." `
    --collect-submodules yt_dlp_plugins `
    --collect-data yt_dlp_ejs `
    --hidden-import yt_dlp_ejs `
    --exclude-module tkinter `
    --add-data "app\assets;app\assets" `
    app\main.py
if ($LASTEXITCODE -ne 0) { throw "Main app PyInstaller build failed." }

Write-Host "[2/7] Building updater helper..."
& $Python -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --windowed `
    --optimize 2 `
    --name "InsightUpdater" `
    --icon "app\assets\insight.ico" `
    app\updater_main.py
if ($LASTEXITCODE -ne 0) { throw "Updater PyInstaller build failed." }
Copy-Item "dist\InsightUpdater.exe" "$MainDist\InsightUpdater.exe" -Force

# Resolve GitHub repository: env -> config -> git origin -> prompt
$Repository = $env:INSIGHT_GITHUB_REPOSITORY
if (-not $Repository -and (Test-Path $ReleaseConfigPath)) {
    try {
        $ReleaseConfig = Get-Content $ReleaseConfigPath -Raw | ConvertFrom-Json
        $Repository = [string]$ReleaseConfig.repository
    } catch {
        Write-Warning "Could not read $ReleaseConfigPath."
    }
}
if (-not $Repository) {
    try {
        $Remote = (& git config --get remote.origin.url 2>$null)
        if ($Remote) {
            $Remote = $Remote.Trim()
            if ($Remote -match "github\.com[/:](?<repo>[^/\s]+/[^/\s]+?)(?:\.git)?$") {
                $Repository = ($Matches.repo -replace "\.git$", "")
            }
        }
    } catch {}
}
if (-not $Repository) {
    Write-Host ""
    Write-Host "GitHub repository was not detected." -ForegroundColor Yellow
    Write-Host "Enter OWNER/REPOSITORY, or press Enter to build without updates/runtime bootstrap."
    $Repository = (Read-Host "GitHub repository").Trim()
    if ($Repository) {
        @{ repository = $Repository } | ConvertTo-Json | Set-Content $ReleaseConfigPath -Encoding UTF8
    }
}
if ($Repository) {
    $Repository = $Repository.Trim().TrimEnd('/') -replace "^https?://github\.com/", "" -replace "\.git$", ""
    if ($Repository -notmatch "^[^/\s]+/[^/\s]+$") {
        throw "Invalid GitHub repository '$Repository'. Use OWNER/REPOSITORY."
    }
    Write-Host "Updater repository: $Repository" -ForegroundColor Green
} else {
    Write-Warning "Automatic updates and first-run media runtime download will be disabled."
    $Repository = ""
}

@{
    repository = $Repository
    channel = "stable"
} | ConvertTo-Json | Set-Content "$MainDist\update_config.json" -Encoding UTF8

Write-Host "[3/7] Adding compact JavaScript runtime..."
New-Item -ItemType Directory -Path "$MainDist\bin" -Force | Out-Null
Copy-Item "bin\qjs.exe" "$MainDist\bin\qjs.exe" -Force
Write-Host "  + qjs.exe"
Write-Host "  - FFmpeg is intentionally NOT bundled in the installer."

Write-Host "[4/7] Packaging media runtime separately..."
& $Python tools\package_runtime.py
if ($LASTEXITCODE -ne 0) { throw "Media runtime packaging failed." }

Write-Host "[5/7] Creating app update package..."
$UpdateZip = "$ReleaseDir\InsightDownloader-update.zip"
Compress-Archive -Path "$MainDist\*" -DestinationPath $UpdateZip -CompressionLevel Optimal
$Hash = (Get-FileHash $UpdateZip -Algorithm SHA256).Hash.ToLowerInvariant()
Set-Content "$UpdateZip.sha256" "$Hash  InsightDownloader-update.zip" -Encoding ASCII

Write-Host "[6/7] Building installer..."
$CandidatePaths = @(
    $env:INNO_SETUP_PATH
    "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
    "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
)
$Candidates = @($CandidatePaths | Where-Object { $_ -and (Test-Path $_) })
$ISCC = $null
if ($Candidates.Count -gt 0) {
    $ISCC = $Candidates[0]
} else {
    $ISCCCommand = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    if ($ISCCCommand) { $ISCC = $ISCCCommand.Source }
}
if ($ISCC) {
    Write-Host "Using Inno Setup: $ISCC"
    & "$ISCC" "/DMyAppVersion=$Version" "installer\InsightDownloader.iss"
    if ($LASTEXITCODE -ne 0) { throw "Inno Setup failed with exit code $LASTEXITCODE." }
} else {
    Write-Warning "Inno Setup not found. Install it with: winget install --id JRSoftware.InnoSetup -e"
}

Write-Host "[7/7] Measuring output..."
$InstalledBytes = (Get-ChildItem "$MainDist" -Recurse -File | Measure-Object Length -Sum).Sum
$InstalledMB = [Math]::Round($InstalledBytes / 1MB, 1)
Write-Host "Core installed size (without FFmpeg runtime): $InstalledMB MB" -ForegroundColor Cyan
Write-Host ""
Write-Host "Release files:"
Get-ChildItem $ReleaseDir | Select-Object Name, @{N='MB';E={[Math]::Round($_.Length / 1MB, 1)}} | Format-Table -AutoSize
Write-Host ""
Write-Host "Production release completed." -ForegroundColor Green
