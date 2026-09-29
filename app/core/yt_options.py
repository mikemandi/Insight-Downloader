from __future__ import annotations

from typing import Any

from app.core.runtime import find_deno, is_youtube_url


def common_options(url: str) -> dict[str, Any]:
    options: dict[str, Any] = {
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
    }

    if is_youtube_url(url):
        # Current yt-dlp recommendation: use mweb with a PO Token provider.
        # yt-dlp-getpot-wpc is installed with the project and launches its own
        # controlled Chrome/Chromium instance to mint tokens, so it does not
        # read or lock the user's normal Chrome cookie database.
        options['extractor_args'] = {
            'youtube': {
                'player_client': ['mweb'],
            }
        }

        # Deno is enabled by default in yt-dlp. Explicitly pass the bundled
        # path when the app ships with deno.exe in bin/.
        deno = find_deno()
        if deno:
            options['js_runtimes'] = {'deno': {'path': str(deno)}}

    return options


def friendly_error(message: str) -> str:
    msg = message or 'Неизвестная ошибка.'
    low = msg.lower()

    if 'sign in to confirm' in low and 'not a bot' in low:
        return (
            'YouTube отклонил запрос как автоматический. Insight Downloader уже использует '
            'актуальный PO Token provider, но YouTube может дополнительно ограничивать отдельные IP.\n\n'
            'Проверьте, что установлен Deno, и повторите попытку. Если блокировка остаётся только '
            'на конкретной сети/IP, попробуйте позже или с другой сетью.\n\n'
            f'Техническая ошибка:\n{msg}'
        )

    if 'javascript runtime' in low or 'ejs' in low or 'deno' in low:
        return (
            'Для полной поддержки YouTube нужен JavaScript runtime Deno.\n\n'
            'Windows PowerShell:\nwinget install --id=DenoLand.Deno -e\n\n'
            'После установки полностью перезапустите VS Code/PowerShell.\n\n'
            f'Техническая ошибка:\n{msg}'
        )

    if 'could not copy chrome cookie database' in low or 'failed to decrypt with dpapi' in low:
        return (
            'Эта ошибка относится к старому способу чтения cookies Chrome. В новой версии '
            'Insight Downloader этот способ не используется. Убедитесь, что вы запускаете '
            'именно проект v3 и обновили зависимости.\n\n'
            f'Техническая ошибка:\n{msg}'
        )

    return msg
