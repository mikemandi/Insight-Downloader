$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

$TargetDir = "bin"
$Target = Join-Path $TargetDir "qjs.exe"
New-Item -ItemType Directory -Path $TargetDir -Force | Out-Null

if (Test-Path $Target) {
    Write-Host "QuickJS already present: $Target"
    exit 0
}

$Headers = @{
    "Accept" = "application/vnd.github+json"
    "X-GitHub-Api-Version" = "2026-03-10"
    "User-Agent" = "InsightDownloader-build"
}
$Release = Invoke-RestMethod -Headers $Headers -Uri "https://api.github.com/repos/quickjs-ng/quickjs/releases/latest"
$Asset = $Release.assets | Where-Object { $_.name -eq "qjs-windows-x86_64.exe" } | Select-Object -First 1
if (-not $Asset) {
    throw "QuickJS Windows x64 asset was not found in the latest release."
}

$Temp = "$Target.download"
Invoke-WebRequest -Headers @{"User-Agent"="InsightDownloader-build"} -Uri $Asset.browser_download_url -OutFile $Temp

$Digest = [string]$Asset.digest
if ($Digest.StartsWith("sha256:")) {
    $Expected = $Digest.Substring(7).ToLowerInvariant()
    $Actual = (Get-FileHash $Temp -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($Actual -ne $Expected) {
        Remove-Item $Temp -Force -ErrorAction SilentlyContinue
        throw "QuickJS SHA-256 verification failed."
    }
}

Move-Item $Temp $Target -Force
Write-Host "QuickJS downloaded: $Target"
