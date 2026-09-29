# Insight Downloader

Insight Downloader — Windows-приложение для скачивания публично доступного видео и аудио через `yt-dlp`.

Текущая версия: **0.5.0**.

## Возможности

- Видео в доступных качествах
- MP3 и WAV
- YouTube с актуальным PO Token pipeline
- VK Video и другие источники, поддерживаемые `yt-dlp`
- Тёмная / светлая / системная тема
- Drag & Drop ссылок
- FFmpeg / Deno runtime status
- Автоматическая проверка обновлений через GitHub Releases
- Обновление приложения без повторного запуска установщика
- Windows installer через Inno Setup
- Настоящая Windows-иконка для EXE, ярлыков и установщика

## Разработка

```powershell
setup_windows.cmd
run.cmd
```

Для FFmpeg положите `ffmpeg.exe` и `ffprobe.exe` в `bin/` или установите их в PATH.
Deno может лежать в `bin/` или быть установлен в PATH.

## Иконка приложения

Главная иконка:

```text
app/assets/insight.ico
```

ICO содержит размеры 16, 20, 24, 32, 40, 48, 64, 128 и 256 px.
PyInstaller использует её для `Insight Downloader.exe`, а Inno Setup — для установщика и ярлыков.

## Система обновлений

Обновления работают через **GitHub Releases**.

Приложение при запуске делает фоновый запрос к:

```text
https://api.github.com/repos/OWNER/REPOSITORY/releases/latest
```

Если версия релиза новее текущей и в релизе есть:

```text
InsightDownloader-update.zip
```

в шапке появляется кнопка `Обновить · X.Y.Z`, а Windows получает уведомление.

После подтверждения приложение:

1. скачивает update ZIP;
2. проверяет SHA-256, если digest доступен через GitHub API или опубликован `.sha256`;
3. запускает `InsightUpdater.exe` из временной папки;
4. закрывает основной процесс;
5. заменяет файлы приложения;
6. запускает новую версию.

Установщик повторно запускать не требуется.

### Как указать GitHub-репозиторий

При `build_release.cmd` репозиторий автоматически берётся из Git remote `origin`.

Например:

```powershell
git remote add origin https://github.com/USERNAME/InsightDownloader.git
```

Либо перед сборкой можно явно задать:

```powershell
$env:INSIGHT_GITHUB_REPOSITORY="USERNAME/InsightDownloader"
.\build_release.cmd
```

В готовую сборку попадёт файл:

```text
update_config.json
```

Если репозиторий не определён, приложение просто не проверяет обновления.

## Выпуск новой версии

Версия хранится централизованно. Перед новым релизом:

```powershell
set_version.cmd 0.5.1
```

Команда обновит runtime version и `pyproject.toml`. Windows version resource генерируется автоматически при сборке.

## Production build

Сначала установите Inno Setup:

```powershell
winget install --id JRSoftware.InnoSetup -e
```

После этого:

```powershell
build_release.cmd
```

Скрипт создаёт:

```text
release/
├── InsightDownloaderSetup-v0.5.0.exe
├── InsightDownloader-update.zip
└── InsightDownloader-update.zip.sha256
```

`InsightDownloaderSetup-v0.5.0.exe` — файл для новых пользователей.

`InsightDownloader-update.zip` — payload для встроенного обновления.

## Публикация GitHub Release

После `build_release.cmd` и `gh auth login`:

```powershell
publish_release.cmd
```

Он создаст тег `v0.5.0` и прикрепит installer + update ZIP + checksum.

## Куда устанавливается приложение

Установщик использует per-user установку:

```text
%LOCALAPPDATA%\Programs\Insight Downloader
```

Поэтому:

- UAC обычно не нужен;
- обновлятор может заменять файлы без прав администратора;
- установка не требует Python.

## Структура обновления

```text
app/core/update_service.py   # GitHub Releases API, download, SHA-256
app/core/update_apply.py     # запуск updater helper
app/updater_main.py          # замена файлов после выхода приложения
app/ui/update_dialog.py      # окно обновления
installer/InsightDownloader.iss
build_release.ps1
publish_release.ps1
```

## Важное перед публичным релизом

Если вы распространяете FFmpeg вместе с приложением, проверьте лицензию конкретной FFmpeg-сборки и положите необходимые third-party notices/licenses в дистрибутив.

Windows SmartScreen может показывать предупреждение для неподписанного `.exe`. Для публичного коммерческого релиза следующий production-шаг — Authenticode code signing установщика и EXE.
