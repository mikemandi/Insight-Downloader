from __future__ import annotations

from typing import Any

from app.core.runtime import find_chrome, find_qjs, is_youtube_url


def common_options(url: str) -> dict[str, Any]:
    options: dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
    }

    if is_youtube_url(url):
        # Do not force mweb as the only YouTube client. When the PO-token provider
        # is unavailable or fails to start, mweb can expose only a very small
        # subset of formats (often the legacy low-resolution progressive stream).
        #
        # We ask yt-dlp for its current defaults first, keep web_embedded as an
        # additional compatibility fallback, and still include mweb so the WPC
        # provider can mint GVS PO tokens and unlock adaptive high-resolution
        # streams when available.
        youtube_args: dict[str, list[str]] = {
            "player_client": ["default", "web_embedded", "mweb"],
            "fetch_pot": ["always"],
        }

        extractor_args: dict[str, dict[str, list[str]]] = {
            "youtube": youtube_args,
        }

        # WPC can auto-discover Chrome, but an explicit path is substantially more
        # reliable in a frozen Windows build and avoids falling back to mweb
        # without a usable PO token provider.
        chrome = find_chrome()
        if chrome:
            extractor_args["youtubepot-wpc"] = {
                "browser_path": [str(chrome)],
            }

        options["extractor_args"] = extractor_args

        # yt-dlp-ejs needs an external JS runtime for current YouTube player
        # challenges. QuickJS-NG is bundled with the desktop build.
        qjs = find_qjs()
        if qjs:
            options["js_runtimes"] = {"quickjs": {"path": str(qjs)}}

    return options


def friendly_error(message: str) -> str:
    msg = message or "Неизвестная ошибка."
    low = msg.lower()

    if "sign in to confirm" in low and "not a bot" in low:
        return (
            "YouTube отклонил запрос как автоматический. Insight использует PO Token provider, "
            "но YouTube иногда дополнительно ограничивает конкретные IP. Попробуйте ещё раз немного позже "
            "или смените сеть.\n\n"
            f"Техническая ошибка:\n{msg}"
        )

    if "po token" in low or "pot provider" in low:
        return (
            "Не удалось получить YouTube PO Token. Убедитесь, что установлен Chrome или Chromium, "
            "и повторите анализ ссылки.\n\n"
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
            "Медиадвижок FFmpeg ещё не установлен. Insight устанавливает его автоматически при первом запуске "
            "и повторно использует в следующих версиях.\n\n"
            f"Техническая ошибка:\n{msg}"
        )

    return msg
