from __future__ import annotations


def format_duration(seconds: int | None) -> str:
    if not seconds:
        return '—'
    seconds = int(seconds)
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f'{hours}:{minutes:02d}:{seconds:02d}'
    return f'{minutes}:{seconds:02d}'


def human_bytes(value: int | float | None) -> str:
    if value is None:
        return '—'
    size = float(value)
    units = ('B', 'KB', 'MB', 'GB', 'TB')
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f'{int(size)} {unit}' if unit == 'B' else f'{size:.1f} {unit}'
        size /= 1024
    return '—'


def human_speed(value: int | float | None) -> str:
    return '—' if not value else f'{human_bytes(value)}/s'


def format_eta(seconds: int | float | None) -> str:
    if seconds is None:
        return '—'
    seconds = max(0, int(seconds))
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f'{hours}ч {minutes:02d}м'
    if minutes:
        return f'{minutes}м {seconds:02d}с'
    return f'{seconds}с'
