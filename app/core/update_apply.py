from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

from app.core.runtime import app_base_dir


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def updater_path() -> Path:
    return app_base_dir() / "InsightUpdater.exe"


def can_self_update() -> bool:
    return is_frozen() and os.name == "nt" and updater_path().is_file()


def launch_self_update(archive: str | Path, version: str) -> None:
    if not can_self_update():
        raise RuntimeError("Самообновление доступно только в установленной Windows-сборке.")

    archive = Path(archive).resolve()
    if not archive.is_file():
        raise RuntimeError("Архив обновления не найден.")

    source_updater = updater_path()
    temp_root = Path(tempfile.gettempdir()) / "InsightDownloaderUpdater" / str(uuid.uuid4())
    temp_root.mkdir(parents=True, exist_ok=True)
    temp_updater = temp_root / "InsightUpdater.exe"
    shutil.copy2(source_updater, temp_updater)

    target_dir = app_base_dir().resolve()
    exe_name = Path(sys.executable).name

    creationflags = 0
    if os.name == "nt":
        creationflags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP

    subprocess.Popen(
        [
            str(temp_updater),
            "--pid", str(os.getpid()),
            "--archive", str(archive),
            "--target", str(target_dir),
            "--exe", exe_name,
            "--version", version,
        ],
        cwd=str(temp_root),
        close_fds=True,
        creationflags=creationflags,
    )
