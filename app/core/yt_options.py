from __future__ import annotations

from typing import Any

from app.core.runtime import find_qjs, is_youtube_url


def common_options(url: str) -> dict[str, Any]:
    options: dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
    }

    if is_youtube_url(url):
        # mweb + WPC PO Token provider remains the most reliable path we use
        # for public YouTube downloads. The provider launches its own browser
        # and never reads the user's Chrome cookie database.
        options["extractor_args"] = {
            "youtube": {
                "player_client": ["mweb"],
            }
        }

        # QuickJS-NG is ~2 MB on Windows, dramatically smaller than bundling
        # a full Deno runtime while still being supported by yt-dlp-ejs.
        qjs = find_qjs()
        if qjs:
            options["js_runtimes"] = {"quickjs": {"path": str(qjs)}}

    return options


def friendly_error(message: str) -> str:
    msg = message or "Неизвестная ошибка."
    low = msg.lower()

    if "sign in to confirm" in low and "not a bot" in low:
        return (
            "YouTube отклонил запрос как автоматический. Insight уже использует PO Token provider, "
            "но YouTube иногда дополнительно ограничивает конкретные IP. Попробуйте ещё раз немного позже "
            "или смените сеть.\n\n"
            f"Техническая ошибка:\n{msg}"
        )

    if "javascript runtime" in low or "ejs" in low or "quickjs" in low or "qjs" in low:
        return (
            "Не найден JavaScript-движок QuickJS. В production-сборке он поставляется вместе с приложением. "
            "Если вы запускаете проект из исходников, выполните tools\\fetch_qjs.ps1.\n\n"
            f"Техническая ошибка:\n{msg}"
        )

    if "ffmpeg" in low or "ffprobe" in low:
        return (
            "Медиадвижок FFmpeg ещё не установлен. Insight может установить его автоматически перед первой загрузкой.\n\n"
            f"Техническая ошибка:\n{msg}"
        )

    return msg
