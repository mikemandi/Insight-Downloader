from __future__ import annotations

import urllib.request
from typing import Any

from PySide6.QtCore import QThread, Signal
from yt_dlp import YoutubeDL

from app.core.formatting import human_bytes
from app.core.media import MediaInfo, VideoFormat
from app.core.yt_options import common_options, friendly_error


class ExtractWorker(QThread):
    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(self, url: str, parent=None) -> None:
        super().__init__(parent)
        self.url = url.strip()

    def run(self) -> None:
        try:
            options: dict[str, Any] = common_options(self.url)
            options.update({'skip_download': True})

            with YoutubeDL(options) as ydl:
                info = ydl.extract_info(self.url, download=False)

            if info.get('_type') == 'playlist':
                entries = info.get('entries') or []
                info = next((entry for entry in entries if entry), None)
                if not info:
                    raise RuntimeError('Не удалось получить элемент из плейлиста.')

            self.succeeded.emit(self._build_media_info(info))
        except Exception as exc:
            self.failed.emit(friendly_error(str(exc)))

    def _build_media_info(self, info: dict[str, Any]) -> MediaInfo:
        formats: list[VideoFormat] = []
        seen: set[tuple[int | None, float | None, str | None]] = set()

        for fmt in info.get('formats') or []:
            vcodec = fmt.get('vcodec')
            if not vcodec or vcodec == 'none':
                continue

            height = fmt.get('height')
            fps = fmt.get('fps')
            ext = fmt.get('ext')
            key = (height, fps, ext)
            if key in seen:
                continue
            seen.add(key)

            size = fmt.get('filesize') or fmt.get('filesize_approx')
            formats.append(
                VideoFormat(
                    height=int(height) if height else None,
                    fps=float(fps) if fps else None,
                    ext=ext,
                    vcodec=vcodec,
                    filesize=int(size) if size else None,
                    tbr=float(fmt['tbr']) if fmt.get('tbr') else None,
                )
            )

        formats.sort(key=lambda item: (item.height or 0, item.fps or 0, item.tbr or 0), reverse=True)

        return MediaInfo(
            url=str(info.get('webpage_url') or self.url),
            title=str(info.get('title') or 'Без названия'),
            uploader=str(info.get('uploader') or info.get('channel') or info.get('creator') or 'Неизвестный автор'),
            extractor=str(info.get('extractor_key') or info.get('extractor') or 'Источник'),
            duration=int(info['duration']) if info.get('duration') else None,
            thumbnail=info.get('thumbnail'),
            formats=formats,
            raw=info,
        )


class ThumbnailWorker(QThread):
    succeeded = Signal(bytes)
    failed = Signal()

    def __init__(self, url: str, parent=None) -> None:
        super().__init__(parent)
        self.url = url

    def run(self) -> None:
        try:
            request = urllib.request.Request(
                self.url,
                headers={'User-Agent': 'Mozilla/5.0 InsightDownloader/4.0'},
            )
            with urllib.request.urlopen(request, timeout=15) as response:
                data = response.read(8 * 1024 * 1024)
            self.succeeded.emit(data)
        except Exception:
            self.failed.emit()
