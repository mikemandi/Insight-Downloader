from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

import py7zr
from PySide6.QtCore import QThread, Signal

from app import __version__
from app.config import GITHUB_API_VERSION
from app.core.runtime import media_runtime_dir
from app.core.update_service import configured_repository

RUNTIME_ASSET_NAME = "InsightMediaRuntime.7z"
RUNTIME_CHECKSUM_NAME = f"{RUNTIME_ASSET_NAME}.sha256"


class RuntimeInstallError(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _github_json(url: str) -> dict:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": GITHUB_API_VERSION,
            "User-Agent": f"InsightDownloader/{__version__}",
        },
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.load(response)


def _runtime_release_payload(repository: str) -> dict:
    """Use this app version's runtime when available, otherwise reuse latest.

    Insight Media Runtime is intentionally version-independent. Falling back to
    the latest published runtime also makes pre-release installer testing work
    before the new GitHub Release itself has been published.
    """
    tag = f"v{__version__}"
    tagged_url = f"https://api.github.com/repos/{repository}/releases/tags/{tag}"
    try:
        payload = _github_json(tagged_url)
        if any(a.get("name") == RUNTIME_ASSET_NAME for a in payload.get("assets") or []):
            return payload
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            raise
    except Exception:
        # A latest-release retry below gives a more useful result for the user.
        pass

    latest_url = f"https://api.github.com/repos/{repository}/releases/latest"
    return _github_json(latest_url)


def _release_asset_info() -> tuple[str, str | None, int]:
    repository = configured_repository()
    if not repository:
        raise RuntimeInstallError(
            "В этой сборке не настроен GitHub-репозиторий для загрузки медиадвижка."
        )

    try:
        payload = _runtime_release_payload(repository)
    except Exception as exc:
        raise RuntimeInstallError(f"Не удалось получить данные Insight Media Runtime: {exc}") from exc

    assets = payload.get("assets") or []
    asset = next((a for a in assets if a.get("name") == RUNTIME_ASSET_NAME), None)
    if not asset:
        release_name = str(payload.get("tag_name") or payload.get("name") or "latest")
        raise RuntimeInstallError(
            f"В GitHub Release {release_name} нет файла {RUNTIME_ASSET_NAME}."
        )

    digest = str(asset.get("digest") or "")
    sha256 = digest.split(":", 1)[1] if digest.startswith("sha256:") else None

    if not sha256:
        checksum_asset = next((a for a in assets if a.get("name") == RUNTIME_CHECKSUM_NAME), None)
        if checksum_asset and checksum_asset.get("browser_download_url"):
            try:
                req = urllib.request.Request(
                    str(checksum_asset["browser_download_url"]),
                    headers={"User-Agent": f"InsightDownloader/{__version__}"},
                )
                with urllib.request.urlopen(req, timeout=10) as response:
                    candidate = response.read(4096).decode("ascii", errors="ignore").split()[0]
                if len(candidate) == 64 and all(ch in "0123456789abcdefABCDEF" for ch in candidate):
                    sha256 = candidate
            except Exception:
                pass

    return (
        str(asset.get("browser_download_url") or ""),
        sha256,
        int(asset.get("size") or 0),
    )


class MediaRuntimeInstallWorker(QThread):
    progress = Signal(int, int)
    status = Signal(str)
    succeeded = Signal(str)
    failed = Signal(str)

    def run(self) -> None:
        work_dir = Path(tempfile.mkdtemp(prefix="insight-runtime-"))
        try:
            url, expected_sha, expected_size = _release_asset_info()
            if not url:
                raise RuntimeInstallError("У runtime asset отсутствует URL загрузки.")

            archive = work_dir / RUNTIME_ASSET_NAME
            self.status.emit("Скачиваем медиадвижок…")
            request = urllib.request.Request(
                url,
                headers={"User-Agent": f"InsightDownloader/{__version__}"},
            )

            downloaded = 0
            with urllib.request.urlopen(request, timeout=45) as response, archive.open("wb") as output:
                total = int(response.headers.get("Content-Length") or expected_size or 0)
                while True:
                    chunk = response.read(256 * 1024)
                    if not chunk:
                        break
                    output.write(chunk)
                    downloaded += len(chunk)
                    self.progress.emit(downloaded, total)

            if expected_sha:
                self.status.emit("Проверяем целостность…")
                actual = _sha256(archive)
                if actual.lower() != expected_sha.lower():
                    raise RuntimeInstallError("SHA-256 медиадвижка не совпал.")

            self.status.emit("Устанавливаем медиадвижок…")
            unpack_dir = work_dir / "unpacked"
            unpack_dir.mkdir(parents=True, exist_ok=True)
            with py7zr.SevenZipFile(archive, mode="r") as seven_zip:
                seven_zip.extractall(path=unpack_dir)

            ffmpeg = next(unpack_dir.rglob("ffmpeg.exe"), None)
            ffprobe = next(unpack_dir.rglob("ffprobe.exe"), None)
            if not ffmpeg or not ffprobe:
                raise RuntimeInstallError("В runtime archive не найдены ffmpeg.exe и ffprobe.exe.")

            target = media_runtime_dir()
            target.mkdir(parents=True, exist_ok=True)

            # Copy atomically enough for the app not to observe a half-written
            # executable while a first download is started during bootstrap.
            ffmpeg_tmp = target / "ffmpeg.exe.part"
            ffprobe_tmp = target / "ffprobe.exe.part"
            shutil.copy2(ffmpeg, ffmpeg_tmp)
            shutil.copy2(ffprobe, ffprobe_tmp)
            ffmpeg_tmp.replace(target / "ffmpeg.exe")
            ffprobe_tmp.replace(target / "ffprobe.exe")

            self.succeeded.emit(str(target))
        except Exception as exc:
            self.failed.emit(str(exc))
        finally:
            shutil.rmtree(work_dir, ignore_errors=True)
