from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class VideoFormat:
    height: int | None
    fps: float | None
    ext: str | None
    vcodec: str | None
    filesize: int | None
    tbr: float | None


@dataclass(slots=True)
class MediaInfo:
    url: str
    title: str
    uploader: str
    extractor: str
    duration: int | None
    thumbnail: str | None
    formats: list[VideoFormat] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)
