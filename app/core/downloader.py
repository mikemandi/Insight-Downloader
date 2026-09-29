from __future__ import annotations

import threading
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
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.url = url
        self.output_dir = output_dir
        self.mode = mode
        self.height = height
        self._cancel_event = threading.Event()

    def cancel(self) -> None:
        self._cancel_event.set()

    def run(self) -> None:
        try:
            ffmpeg_dir = find_ffmpeg_dir()
            if ffmpeg_dir is None:
                raise RuntimeError('FFmpeg не найден. Положите ffmpeg.exe и ffprobe.exe в папку bin.')

            self.output_dir.mkdir(parents=True, exist_ok=True)
            options: dict[str, Any] = common_options(self.url)
            options.update(
                {
                    'outtmpl': str(self.output_dir / '%(title).180B [%(id)s].%(ext)s'),
                    'windowsfilenames': True,
                    'progress_hooks': [self._progress_hook],
                    'ffmpeg_location': str(ffmpeg_dir),
                    'overwrites': False,
                }
            )

            if self.mode == 'mp3':
                options.update(
                    {
                        'format': 'bestaudio/best',
                        'postprocessors': [
                            {
                                'key': 'FFmpegExtractAudio',
                                'preferredcodec': 'mp3',
                                'preferredquality': '0',
                            },
                            {'key': 'FFmpegMetadata', 'add_metadata': True},
                        ],
                    }
                )
            elif self.mode == 'wav':
                options.update(
                    {
                        'format': 'bestaudio/best',
                        'postprocessors': [
                            {
                                'key': 'FFmpegExtractAudio',
                                'preferredcodec': 'wav',
                            }
                        ],
                    }
                )
            else:
                options.update(self._video_options())

            self.status.emit('Подготавливаем загрузку…')
            with YoutubeDL(options) as ydl:
                info = ydl.extract_info(self.url, download=True)
                final_path = self._resolve_final_path(ydl, info)

            if self._cancel_event.is_set():
                self.cancelled.emit()
                return

            self.succeeded.emit(final_path)
        except DownloadCancelled:
            self.cancelled.emit()
        except Exception as exc:
            if self._cancel_event.is_set():
                self.cancelled.emit()
            else:
                self.failed.emit(friendly_error(str(exc)))

    def _video_options(self) -> dict[str, Any]:
        if self.height:
            selector = f'bestvideo[height<={self.height}]+bestaudio/best[height<={self.height}]/best'
        else:
            selector = 'bestvideo+bestaudio/best'
        return {
            'format': selector,
            'merge_output_format': 'mp4',
        }

    def _progress_hook(self, data: dict[str, Any]) -> None:
        if self._cancel_event.is_set():
            raise DownloadCancelled()

        if data.get('status') == 'downloading':
            self.progress.emit(
                {
                    'downloaded': data.get('downloaded_bytes'),
                    'total': data.get('total_bytes') or data.get('total_bytes_estimate'),
                    'speed': data.get('speed'),
                    'eta': data.get('eta'),
                }
            )
        elif data.get('status') == 'finished':
            self.status.emit('Обрабатываем файл…')

    def _resolve_final_path(self, ydl: YoutubeDL, info: dict[str, Any]) -> str:
        requested = info.get('requested_downloads') or []
        for item in requested:
            filepath = item.get('filepath')
            if filepath:
                path = Path(filepath)
                if self.mode in {'mp3', 'wav'}:
                    return str(path.with_suffix(f'.{self.mode}'))
                return str(path)

        prepared = Path(ydl.prepare_filename(info))
        if self.mode in {'mp3', 'wav'}:
            return str(prepared.with_suffix(f'.{self.mode}'))
        candidate = prepared.with_suffix('.mp4')
        return str(candidate if candidate.exists() else prepared)
