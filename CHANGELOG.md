# Changelog

## 0.5.0

- Добавлена полноценная Windows-иконка с multi-resolution ICO
- Добавлен Windows AppUserModelID для корректной иконки taskbar / shortcut grouping
- Добавлен version resource в EXE
- Добавлена автоматическая проверка GitHub Releases
- Добавлена кнопка уведомления о новой версии в шапке приложения
- Добавлено Windows-уведомление о доступном обновлении
- Добавлено окно с release notes
- Добавлена загрузка update ZIP с прогрессом
- Добавлена SHA-256 проверка update package
- Добавлен отдельный InsightUpdater.exe
- Реализовано обновление файлов без повторной установки
- Добавлен per-user installer на Inno Setup
- Установщик создаёт Start Menu shortcut и опциональный Desktop shortcut
- Добавлена release-сборка installer + update payload
- Добавлен publish_release.cmd для GitHub Releases
- Runtime binaries автоматически копируются из `bin/` или PATH при production build

## 0.4.0

- Полностью переработан компактный UI без вертикальной прокрутки
- Добавлен hover glow для основных действий
- Улучшены light/dark/system темы
- Добавлены drag & drop и clipboard UX
- Добавлена Windows-иконка базового уровня
