from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import py7zr


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    release = root / "release"
    release.mkdir(parents=True, exist_ok=True)
    ffmpeg = root / "bin" / "ffmpeg.exe"
    ffprobe = root / "bin" / "ffprobe.exe"
    if not ffmpeg.is_file() or not ffprobe.is_file():
        raise SystemExit("bin/ffmpeg.exe and bin/ffprobe.exe are required for a production release")

    archive = release / "InsightMediaRuntime.7z"
    if archive.exists():
        archive.unlink()

    with py7zr.SevenZipFile(archive, "w") as z:
        z.write(ffmpeg, arcname="ffmpeg.exe")
        z.write(ffprobe, arcname="ffprobe.exe")

    digest = sha256(archive)
    (release / "InsightMediaRuntime.7z.sha256").write_text(
        f"{digest}  InsightMediaRuntime.7z\n", encoding="ascii"
    )
    print(f"Created {archive} ({archive.stat().st_size / 1024 / 1024:.1f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
