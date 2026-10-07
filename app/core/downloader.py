from __future__ import annotations

import os
import subprocess
import threading
import time
from pathlib import Path
from typing import Any

from PySide6.QtCore import QThread, Signal
from yt_dlp import YoutubeDL

from app.core.runtime import find_ffmpeg_dir
from app.core.yt_options import common_options, friendly_error


class DownloadCancelled(Exception):
    pass


class DownloadWorker(QThread):
    progress = Signal(dict)
    status = Signal(str)
    succeeded = Signal(str)
    failed = Signal(str)
    cancelled = Signal()

    def __init__(
        self,
        *,
        url: str,
        output_dir: Path,
        mode: str,
        height: int | None = None,
        audio_quality: str | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.url = url
        self.output_dir = output_dir
        self.mode = mode
        self.height = height
        self.audio_quality = audio_quality or "best"
        self._cancel_event = threading.Event()
        self._process: subprocess.Popen[str] | None = None

    def cancel(self) -> None:
        self._cancel_event.set()
        proc = self._process
        if proc and proc.poll() is None:
            try:
                proc.terminate()
            except Exception:
                pass

    def run(self) -> None:
        try:
            ffmpeg_dir = find_ffmpeg_dir()
            if ffmpeg_dir is None:
                raise RuntimeError("FFmpeg не найден.")

            self.output_dir.mkdir(parents=True, exist_ok=True)
            options: dict[str, Any] = common_options(self.url)
            options.update(
                {
                    "outtmpl": str(self.output_dir / "%(title).180B [%(id)s].%(ext)s"),
                    "windowsfilenames": True,
                    "progress_hooks": [self._progress_hook],
                    "ffmpeg_location": str(ffmpeg_dir),
                    "overwrites": False,
                }
            )

            if self.mode in {"mp3", "wav"}:
                options["format"] = "bestaudio/best"
            else:
                options.update(self._video_options())

            self.status.emit("Подготавливаем загрузку…")
            with YoutubeDL(options) as ydl:
                info = ydl.extract_info(self.url, download=True)
                source_path = self._resolve_downloaded_source(ydl, info)

            if self._cancel_event.is_set():
                raise DownloadCancelled()

            if self.mode in {"mp3", "wav"}:
                final_path = self._convert_audio(source_path, ffmpeg_dir)
            else:
                final_path = self._resolve_video_path(source_path)

            if self._cancel_event.is_set():
                raise DownloadCancelled()

            self.succeeded.emit(str(final_path))
        except DownloadCancelled:
            self.cancelled.emit()
        except Exception as exc:
            if self._cancel_event.is_set():
                self.cancelled.emit()
            else:
                self.failed.emit(friendly_error(str(exc)))

    def _video_options(self) -> dict[str, Any]:
        if self.height:
            selector = f"bestvideo[height<={self.height}]+bestaudio/best[height<={self.height}]/best"
        else:
            selector = "bestvideo+bestaudio/best"
        return {
            "format": selector,
            "merge_output_format": "mp4",
        }

    def _convert_audio(self, source: Path, ffmpeg_dir: Path) -> Path:
        ffmpeg_name = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
        ffmpeg = ffmpeg_dir / ffmpeg_name
        if not ffmpeg.exists():
            raise RuntimeError("FFmpeg не найден.")

        target = source.with_suffix(f".{self.mode}")
        same_path = source.resolve() == target.resolve()
        encode_target = (
            source.with_name(f"{source.stem}.insight.{self.mode}")
            if same_path
            else target
        )
        self.status.emit("Конвертируем аудио…")

        command = [str(ffmpeg), "-y", "-i", str(source), "-vn"]

        if self.mode == "mp3":
            bitrate = self.audio_quality if self.audio_quality in {"320", "256", "192", "128"} else "320"
            command += ["-map_metadata", "0", "-c:a", "libmp3lame", "-b:a", f"{bitrate}k", str(encode_target)]
        else:
            # WAV presets represent real PCM output settings rather than a fake bitrate label.
            wav_presets: dict[str, list[str]] = {
                "source": ["-c:a", "pcm_s16le"],
                "48k24": ["-c:a", "pcm_s24le", "-ar", "48000"],
                "48k16": ["-c:a", "pcm_s16le", "-ar", "48000"],
                "44k16": ["-c:a", "pcm_s16le", "-ar", "44100"],
            }
            command += wav_presets.get(self.audio_quality, wav_presets["source"])
            command.append(str(encode_target))

        creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" and hasattr(subprocess, "CREATE_NO_WINDOW") else 0
        self._process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=creationflags,
        )

        while self._process.poll() is None:
            if self._cancel_event.is_set():
                try:
                    self._process.terminate()
                except Exception:
                    pass
                raise DownloadCancelled()
            time.sleep(0.08)

        stdout, stderr = self._process.communicate()
        return_code = self._process.returncode
        self._process = None

        if return_code != 0 or not encode_target.exists():
            detail = (stderr or stdout or "FFmpeg завершился с ошибкой.").strip()
            if len(detail) > 1200:
                detail = detail[-1200:]
            raise RuntimeError(detail)

        if same_path:
            try:
                source.unlink()
            except OSError:
                pass
            encode_target.replace(target)
        elif source.exists():
            try:
                source.unlink()
            except OSError:
                pass

        return target

    def _progress_hook(self, data: dict[str, Any]) -> None:
        if self._cancel_event.is_set():
            raise DownloadCancelled()

        if data.get("status") == "downloading":
            self.progress.emit(
                {
                    "downloaded": data.get("downloaded_bytes"),
                    "total": data.get("total_bytes") or data.get("total_bytes_estimate"),
                    "speed": data.get("speed"),
                    "eta": data.get("eta"),
                }
            )
        elif data.get("status") == "finished":
            self.status.emit("Обрабатываем файл…")

    def _resolve_downloaded_source(self, ydl: YoutubeDL, info: dict[str, Any]) -> Path:
        requested = info.get("requested_downloads") or []
        for item in requested:
            filepath = item.get("filepath")
            if filepath:
                return Path(filepath)
        return Path(ydl.prepare_filename(info))

    def _resolve_video_path(self, prepared: Path) -> Path:
        if prepared.suffix.lower() == ".mp4" and prepared.exists():
            return prepared
        candidate = prepared.with_suffix(".mp4")
        return candidate if candidate.exists() else prepared
