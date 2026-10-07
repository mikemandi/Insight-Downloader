# Changelog

## 0.7.2

- Финальная UI-polish итерация без изменения общей концепции.
- Уплотнена правая колонка: CTA располагается сразу после состояния, без искусственного stretch.
- Empty state поднят выше и получил более компактную иконку.
- Preview ограничен высотой 320 px.
- Вертикальный разделитель стал ещё мягче.
- Disabled-состояние кнопки «Скачать» теперь читается именно как недоступная кнопка.
- Выбранный режим Видео / MP3 / WAV стал чуть контрастнее.
- Settings получил больше вертикального воздуха и компактную кнопку «Готово».
- Усилено применение новой иконки в Windows и ярлыки установщика используют отдельный Insight.ico.

## 0.7.1

- Polished the download workflow: only one primary action is emphasized at a time.
- Moved Download closer to the selection/status block and removed the large dead area in the right pane.
- Compact media metadata now uses a single source/duration/author line.
- Portrait thumbnails are contained over a subtle backdrop instead of being aggressively cropped.
- Settings spacing and About hierarchy were refined.
- Diagnostics now expands to a proper content-sized panel with separate status indicators.
- Update check is styled as a link-style action.
- Windows application identity and native window icon handling were refreshed so the new download icon is used by titlebar/taskbar after rebuilding.

## 0.7.0

### Design system

- Rebuilt the main screen around a neutral, low-border Windows product UI.
- Removed the large framed header and giant outer application card.
- Reduced visual noise: fewer outlines, smaller radii, calmer purple accent, subtler hover states.
- Added a fixed 1000×720 window and disabled maximize/fullscreen resizing for a predictable layout.
- Replaced the emoji settings button with a painted vector-style settings glyph.
- Added explicit chevrons to all select controls.
- Reworked typography around Segoe UI Variable with clearer hierarchy and less all-caps text.
- Replaced inline error banners with an animated modal bottom sheet.
- Updated the application icon from the new Insight download mark.

### Download UX

- Download stays disabled until a link is successfully analyzed.
- Progress UI only appears while a download is active.
- Completed downloads switch to a compact success state instead of leaving a 100% progress bar on screen.
- Added MP3 quality choices: 320 / 256 / 192 / 128 kbps.
- Added WAV output choices: source rate 16-bit, 48 kHz 24-bit, 48 kHz 16-bit, and 44.1 kHz 16-bit.
- Audio conversion is now performed explicitly with FFmpeg so the selected audio preset is real, not cosmetic.

### Settings

- Rebuilt Settings as clean sections instead of stacked cards.
- Moved version information into the About area.
- Added default download folder control.
- Added automatic update toggle.
- Moved FFmpeg / QuickJS / Chromium status behind a collapsed Diagnostics section.

## 0.6.0

- Replaced full PySide6 with PySide6-Essentials.
- Replaced Deno with QuickJS-NG.
- Moved FFmpeg/ffprobe into a separate optional media runtime package.
- Added first-use media runtime installation and compact release packaging.

## 0.5.0

- Added Windows installer.
- Added app icon and Windows version metadata.
- Added GitHub Release update checks and self-update helper.
