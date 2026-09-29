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

& $Python -m pip install --upgrade pyinstaller pillow
& $Python tools\generate_version_info.py | Out-Null

if (Test-Path "dist") { Remove-Item "dist" -Recurse -Force }
if (Test-Path "release") { Remove-Item "release" -Recurse -Force }
New-Item -ItemType Directory -Path $ReleaseDir | Out-Null

Write-Host "[1/5] Building Insight Downloader..."
& $Python -m PyInstaller `
    --noconfirm `
    --clean `
    --windowed `
    --name "Insight Downloader" `
    --icon "app\assets\insight.ico" `
    --version-file "installer\windows_version_info.txt" `
    --paths "." `
    --collect-all yt_dlp `
    --collect-all yt_dlp_ejs `
    --collect-submodules yt_dlp_plugins `
    --add-data "app\assets;app\assets" `
    app\main.py

Write-Host "[2/5] Building updater helper..."
& $Python -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --windowed `
    --name "InsightUpdater" `
    --icon "app\assets\insight.ico" `
    app\updater_main.py

Copy-Item "dist\InsightUpdater.exe" "$MainDist\InsightUpdater.exe" -Force

# ------------------------------------------------------------
# Resolve the GitHub repository for the in-app updater.
# Priority:
#   1) INSIGHT_GITHUB_REPOSITORY environment variable
#   2) release_config.json
#   3) git remote origin
#   4) interactive prompt
# ------------------------------------------------------------
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
    Write-Host "Enter it as OWNER/REPOSITORY, for example: InsightDevelopment/InsightDownloader"
    Write-Host "Press Enter to build without automatic updates."
    $Repository = (Read-Host "GitHub repository").Trim()

    if ($Repository) {
        @{ repository = $Repository } |
            ConvertTo-Json |
            Set-Content $ReleaseConfigPath -Encoding UTF8
        Write-Host "Saved repository to $ReleaseConfigPath"
    }
}

if ($Repository) {
    $Repository = $Repository.Trim().TrimEnd('/') -replace "^https?://github\.com/", "" -replace "\.git$", ""
    if ($Repository -notmatch "^[^/\s]+/[^/\s]+$") {
        throw "Invalid GitHub repository '$Repository'. Use OWNER/REPOSITORY."
    }
    Write-Host "Updater repository: $Repository" -ForegroundColor Green
} else {
    Write-Warning "Automatic update checks will be disabled in this build."
    $Repository = ""
}

@{
    repository = $Repository
    channel = "stable"
} | ConvertTo-Json | Set-Content "$MainDist\update_config.json" -Encoding UTF8

Write-Host "[3/5] Copying runtimes..."
New-Item -ItemType Directory -Path "$MainDist\bin" -Force | Out-Null
foreach ($Runtime in @("ffmpeg.exe", "ffprobe.exe", "deno.exe")) {
    $Source = $null
    if (Test-Path "bin\$Runtime") {
        $Source = (Resolve-Path "bin\$Runtime").Path
    } else {
        $CommandName = [System.IO.Path]::GetFileNameWithoutExtension($Runtime)
        $Command = Get-Command $CommandName -ErrorAction SilentlyContinue
        if ($Command) { $Source = $Command.Source }
    }

    if ($Source) {
        Copy-Item $Source "$MainDist\bin\$Runtime" -Force
        Write-Host "  + $Runtime"
    } else {
        Write-Warning "$Runtime was not found. The installer will not be fully standalone without it."
    }
}

Write-Host "[4/5] Creating update package..."
$UpdateZip = "$ReleaseDir\InsightDownloader-update.zip"
Compress-Archive -Path "$MainDist\*" -DestinationPath $UpdateZip -CompressionLevel Optimal
$Hash = (Get-FileHash $UpdateZip -Algorithm SHA256).Hash.ToLowerInvariant()
Set-Content "$UpdateZip.sha256" "$Hash  InsightDownloader-update.zip" -Encoding ASCII

Write-Host "[5/5] Building installer if Inno Setup is available..."

# Force an array here. Without @(...), PowerShell turns a single result into
# a scalar string and $Candidates[0] becomes just the first character ('C').
$CandidatePaths = @(
    $env:INNO_SETUP_PATH
    "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
    "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
)

$Candidates = @(
    $CandidatePaths | Where-Object { $_ -and (Test-Path $_) }
)

$ISCC = $null
if ($Candidates.Count -gt 0) {
    $ISCC = $Candidates[0]
} else {
    $ISCCCommand = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    if ($ISCCCommand) {
        $ISCC = $ISCCCommand.Source
    }
}

if ($ISCC) {
    Write-Host "Using Inno Setup: $ISCC"
    & "$ISCC" "/DMyAppVersion=$Version" "installer\InsightDownloader.iss"
    if ($LASTEXITCODE -ne 0) {
        throw "Inno Setup failed with exit code $LASTEXITCODE."
    }
    Write-Host "Installer created." -ForegroundColor Green
} else {
    Write-Warning "Inno Setup not found. Install it with: winget install --id JRSoftware.InnoSetup -e"
    Write-Warning "The update ZIP was still created successfully."
}

Write-Host ""
Write-Host "Release files:"
Get-ChildItem $ReleaseDir | Select-Object Name, Length | Format-Table -AutoSize
