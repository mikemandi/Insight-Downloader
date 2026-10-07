from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

from PySide6.QtCore import QStandardPaths


def app_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def resource_path(*parts: str) -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS).joinpath(*parts)
    return app_base_dir().joinpath(*parts)


def app_data_dir() -> Path:
    location = QStandardPaths.writableLocation(QStandardPaths.AppLocalDataLocation)
    if location:
        path = Path(location)
    else:
        path = Path.home() / "AppData" / "Local" / "Insight Downloader"
    path.mkdir(parents=True, exist_ok=True)
    return path


def media_runtime_dir() -> Path:
    path = app_data_dir() / "runtime" / "media"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _runtime_candidates(name: str) -> list[Path]:
    filename = f"{name}.exe" if os.name == "nt" else name
    return [
        media_runtime_dir() / filename,
        app_base_dir() / "bin" / filename,
    ]


def find_executable(name: str) -> Path | None:
    for candidate in _runtime_candidates(name):
        if candidate.is_file():
            return candidate
    found = shutil.which(name)
    return Path(found).resolve() if found else None


def find_ffmpeg_dir() -> Path | None:
    ffmpeg = find_executable("ffmpeg")
    ffprobe = find_executable("ffprobe")
    if ffmpeg and ffprobe and ffmpeg.parent == ffprobe.parent:
        return ffmpeg.parent
    return None


def find_qjs() -> Path | None:
    return find_executable("qjs")


def find_chrome() -> Path | None:
    candidates: list[Path] = []
    if os.name == "nt":
        for base in (
            os.environ.get("PROGRAMFILES"),
            os.environ.get("PROGRAMFILES(X86)"),
            os.environ.get("LOCALAPPDATA"),
        ):
            if base:
                candidates.append(Path(base) / "Google/Chrome/Application/chrome.exe")
                candidates.append(Path(base) / "Chromium/Application/chrome.exe")
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    for name in ("chrome", "google-chrome", "chromium", "chromium-browser"):
        found = shutil.which(name)
        if found:
            return Path(found).resolve()
    return None


def is_youtube_url(url: str) -> bool:
    try:
        host = (urlparse(url).hostname or "").lower()
    except Exception:
        return False
    return host in {
        "youtube.com",
        "www.youtube.com",
        "m.youtube.com",
        "music.youtube.com",
        "youtu.be",
    } or host.endswith(".youtube.com")


def open_path(path: str | Path) -> None:
    path = Path(path)
    if os.name == "nt":
        os.startfile(path)
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])
