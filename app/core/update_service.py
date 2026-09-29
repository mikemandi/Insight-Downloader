from __future__ import annotations

import hashlib
import json
import tempfile
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from packaging.version import InvalidVersion, Version
from PySide6.QtCore import QThread, Signal

from app import __version__
from app.config import GITHUB_API_VERSION, UPDATE_ASSET_NAME, UPDATE_REPOSITORY
from app.core.runtime import app_base_dir


@dataclass(slots=True)
class UpdateInfo:
    version: str
    tag: str
    name: str
    notes: str
    page_url: str
    download_url: str
    size: int
    sha256: str | None


class UpdateError(RuntimeError):
    pass


def configured_repository() -> str:
    external = app_base_dir() / "update_config.json"
    if external.is_file():
        try:
            payload = json.loads(external.read_text(encoding="utf-8"))
            value = str(payload.get("repository") or "").strip()
            if value:
                return value
        except Exception:
            pass
    return UPDATE_REPOSITORY.strip()


def updates_configured() -> bool:
    value = configured_repository()
    return bool(value and "/" in value and not value.startswith("CHANGE_ME"))


def _normalize_version(value: str) -> Version:
    return Version(value.strip().lstrip("vV"))


def fetch_latest_update() -> UpdateInfo | None:
    if not updates_configured():
        return None

    repository = configured_repository()
    url = f"https://api.github.com/repos/{repository}/releases/latest"
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": GITHUB_API_VERSION,
            "User-Agent": f"InsightDownloader/{__version__}",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=12) as response:
            payload = json.load(response)
    except Exception as exc:
        raise UpdateError(f"Не удалось проверить обновления: {exc}") from exc

    tag = str(payload.get("tag_name") or "").strip()
    if not tag:
        raise UpdateError("GitHub Release не содержит tag_name.")

    try:
        latest = _normalize_version(tag)
        current = _normalize_version(__version__)
    except InvalidVersion as exc:
        raise UpdateError(f"Некорректная версия релиза: {tag}") from exc

    if latest <= current:
        return None

    asset = next(
        (item for item in payload.get("assets", []) if item.get("name") == UPDATE_ASSET_NAME),
        None,
    )
    if asset is None:
        raise UpdateError(
            f"В релизе {tag} нет файла {UPDATE_ASSET_NAME}. "
            "Соберите update ZIP перед публикацией релиза."
        )

    digest = str(asset.get("digest") or "")
    sha256 = digest.split(":", 1)[1] if digest.startswith("sha256:") else None

    if not sha256:
        checksum_name = f"{UPDATE_ASSET_NAME}.sha256"
        checksum_asset = next(
            (item for item in payload.get("assets", []) if item.get("name") == checksum_name),
            None,
        )
        if checksum_asset and checksum_asset.get("browser_download_url"):
            try:
                checksum_request = urllib.request.Request(
                    str(checksum_asset["browser_download_url"]),
                    headers={"User-Agent": f"InsightDownloader/{__version__}"},
                )
                with urllib.request.urlopen(checksum_request, timeout=10) as checksum_response:
                    checksum_text = checksum_response.read(4096).decode("ascii", errors="ignore").strip()
                candidate = checksum_text.split()[0].strip()
                if len(candidate) == 64 and all(ch in "0123456789abcdefABCDEF" for ch in candidate):
                    sha256 = candidate
            except Exception:
                pass

    return UpdateInfo(
        version=str(latest),
        tag=tag,
        name=str(payload.get("name") or tag),
        notes=str(payload.get("body") or ""),
        page_url=str(payload.get("html_url") or ""),
        download_url=str(asset.get("browser_download_url") or ""),
        size=int(asset.get("size") or 0),
        sha256=sha256,
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class UpdateCheckWorker(QThread):
    found = Signal(object)
    up_to_date = Signal()
    failed = Signal(str)

    def run(self) -> None:
        try:
            info = fetch_latest_update()
            if info is None:
                self.up_to_date.emit()
            else:
                self.found.emit(info)
        except Exception as exc:
            self.failed.emit(str(exc))


class UpdateDownloadWorker(QThread):
    progress = Signal(int, int)
    status = Signal(str)
    succeeded = Signal(str)
    failed = Signal(str)

    def __init__(self, info: UpdateInfo, parent=None) -> None:
        super().__init__(parent)
        self.info = info

    def run(self) -> None:
        try:
            if not self.info.download_url:
                raise UpdateError("У релиза отсутствует URL файла обновления.")

            update_dir = Path(tempfile.gettempdir()) / "InsightDownloader" / "updates"
            update_dir.mkdir(parents=True, exist_ok=True)
            target = update_dir / f"InsightDownloader-{self.info.version}.zip"
            temp_target = target.with_suffix(".zip.part")

            request = urllib.request.Request(
                self.info.download_url,
                headers={"User-Agent": f"InsightDownloader/{__version__}"},
            )

            self.status.emit("Скачиваем обновление…")
            downloaded = 0
            with urllib.request.urlopen(request, timeout=30) as response, temp_target.open("wb") as output:
                total = int(response.headers.get("Content-Length") or self.info.size or 0)
                while True:
                    chunk = response.read(256 * 1024)
                    if not chunk:
                        break
                    output.write(chunk)
                    downloaded += len(chunk)
                    self.progress.emit(downloaded, total)

            if self.info.sha256:
                self.status.emit("Проверяем целостность…")
                actual = _sha256(temp_target)
                if actual.lower() != self.info.sha256.lower():
                    raise UpdateError("SHA-256 обновления не совпал. Файл удалён.")

            temp_target.replace(target)
            self.succeeded.emit(str(target))
        except Exception as exc:
            self.failed.emit(str(exc))
