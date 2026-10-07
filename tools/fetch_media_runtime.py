from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
import urllib.request
from pathlib import Path

import py7zr

from app import __version__
from app.config import GITHUB_API_VERSION, UPDATE_REPOSITORY

ASSET_NAME = "InsightMediaRuntime.7z"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    bin_dir = root / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    target_ffmpeg = bin_dir / "ffmpeg.exe"
    target_ffprobe = bin_dir / "ffprobe.exe"

    if not args.force and target_ffmpeg.is_file() and target_ffprobe.is_file():
        print("Media runtime already present in bin/.")
        return 0

    repository = UPDATE_REPOSITORY.strip()
    if not repository:
        raise SystemExit("UPDATE_REPOSITORY is not configured")

    api_url = f"https://api.github.com/repos/{repository}/releases/latest"
    request = urllib.request.Request(
        api_url,
        headers={
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": GITHUB_API_VERSION,
            "User-Agent": f"InsightDownloaderBuild/{__version__}",
        },
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        payload = json.load(response)

    asset = next((a for a in payload.get("assets") or [] if a.get("name") == ASSET_NAME), None)
    if not asset:
        raise SystemExit(f"Latest GitHub Release does not contain {ASSET_NAME}")

    url = str(asset.get("browser_download_url") or "")
    if not url:
        raise SystemExit("Media runtime asset has no download URL")

    digest = str(asset.get("digest") or "")
    expected_sha = digest.split(":", 1)[1] if digest.startswith("sha256:") else None

    work = Path(tempfile.mkdtemp(prefix="insight-build-runtime-"))
    try:
        archive = work / ASSET_NAME
        print(f"Downloading {ASSET_NAME} from {payload.get('tag_name') or 'latest'}...")
        req = urllib.request.Request(url, headers={"User-Agent": f"InsightDownloaderBuild/{__version__}"})
        with urllib.request.urlopen(req, timeout=60) as response, archive.open("wb") as output:
            shutil.copyfileobj(response, output, length=1024 * 1024)

        if expected_sha:
            actual = sha256(archive)
            if actual.lower() != expected_sha.lower():
                raise SystemExit("Media runtime SHA-256 mismatch")

        unpacked = work / "unpacked"
        unpacked.mkdir()
        with py7zr.SevenZipFile(archive, "r") as seven_zip:
            seven_zip.extractall(path=unpacked)

        ffmpeg = next(unpacked.rglob("ffmpeg.exe"), None)
        ffprobe = next(unpacked.rglob("ffprobe.exe"), None)
        if not ffmpeg or not ffprobe:
            raise SystemExit("Downloaded runtime does not contain ffmpeg.exe and ffprobe.exe")

        shutil.copy2(ffmpeg, target_ffmpeg)
        shutil.copy2(ffprobe, target_ffprobe)
        print("Media runtime prepared: bin/ffmpeg.exe + bin/ffprobe.exe")
        return 0
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
