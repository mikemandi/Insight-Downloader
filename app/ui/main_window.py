from __future__ import annotations

from pathlib import Path
import time

from PySide6.QtCore import QSettings, Qt, QTimer
from PySide6.QtGui import QGuiApplication, QIcon, QKeySequence, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from app import __version__
from app.core.downloader import DownloadWorker
from app.core.extractor import ExtractWorker, ThumbnailWorker
from app.core.formatting import format_duration, format_eta, human_bytes, human_speed
from app.core.media import MediaInfo
from app.core.runtime import find_chrome, find_deno, find_ffmpeg_dir, is_youtube_url, open_path, resource_path
from app.core.update_apply import can_self_update, launch_self_update
from app.core.update_service import (
    UpdateCheckWorker,
    UpdateDownloadWorker,
    UpdateInfo,
    updates_configured,
)
from app.ui.theme import resolve_theme, stylesheet
from app.ui.update_dialog import UpdateDialog
from app.ui.widgets import ElideLabel, GlowButton, ModeSelector, PreviewLabel


class MainWindow(QMainWindow):
    """Single-window production UI designed to fit without scrolling."""

    def __init__(self) -> None:
        super().__init__()

        self.settings = QSettings("Insight Development", "Insight Downloader")
        self.media: MediaInfo | None = None
        self.extract_worker: ExtractWorker | None = None
        self.thumbnail_worker: ThumbnailWorker | None = None
        self.download_worker: DownloadWorker | None = None
        self.update_check_worker: UpdateCheckWorker | None = None
        self.update_download_worker: UpdateDownloadWorker | None = None
        self.update_info: UpdateInfo | None = None
        self.update_dialog: UpdateDialog | None = None
        self._update_tray: QSystemTrayIcon | None = None
        self.last_download_path: Path | None = None
        self.output_dir = Path(self.settings.value("output_dir", str(Path.home() / "Downloads")))
        self.theme_mode = str(self.settings.value("theme", "system"))

        self.setWindowTitle("Insight Downloader")
        self.setMinimumSize(920, 680)
        self.resize(1000, 700)
        self.setAcceptDrops(True)

        icon_path = resource_path("app", "assets", "insight.ico")
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        self._build_ui()
        self._restore_settings()
        self._apply_theme()
        self._refresh_runtime_status()
        self._connect_system_theme_listener()
        self._install_shortcuts()
        self._schedule_update_check()

        geometry = self.settings.value("window_geometry")
        if geometry:
            self.restoreGeometry(geometry)

    # ------------------------------------------------------------------ UI

    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("Root")
        self.setCentralWidget(root)

        outer = QVBoxLayout(root)
        outer.setContentsMargins(18, 16, 18, 16)
        outer.setSpacing(12)

        outer.addWidget(self._build_top_nav())
        outer.addWidget(self._build_app_shell(), 1)

    def _build_top_nav(self) -> QFrame:
        nav = QFrame()
        nav.setObjectName("TopNav")
        nav.setFixedHeight(62)
        layout = QHBoxLayout(nav)
        layout.setContentsMargins(16, 10, 14, 10)
        layout.setSpacing(11)

        self.logo = QLabel()
        self.logo.setFixedSize(32, 32)
        self._load_logo()
        layout.addWidget(self.logo)

        brand = QVBoxLayout()
        brand.setSpacing(0)
        brand.setContentsMargins(0, 0, 0, 0)
        brand_name = QLabel("Insight Downloader")
        brand_name.setObjectName("Brand")
        brand_meta = QLabel(f"INSIGHT DEVELOPMENT  ·  v{__version__}")
        brand_meta.setObjectName("Eyebrow")
        brand.addWidget(brand_name)
        brand.addWidget(brand_meta)
        layout.addLayout(brand)
        layout.addStretch()

        self.update_button = GlowButton("Обновление")
        self.update_button.setObjectName("UpdateButton")
        self.update_button.setVisible(False)
        self.update_button.setToolTip("Доступна новая версия Insight Downloader")
        self.update_button.clicked.connect(self._show_update_dialog)
        layout.addWidget(self.update_button)

        self.ffmpeg_status = QLabel()
        self.ffmpeg_status.setToolTip("FFmpeg используется для объединения видео и аудио и конвертации MP3/WAV.")
        layout.addWidget(self.ffmpeg_status)

        self.deno_status = QLabel()
        self.deno_status.setToolTip("Deno используется yt-dlp для актуальной поддержки YouTube.")
        layout.addWidget(self.deno_status)

        self.theme_combo = QComboBox()
        self.theme_combo.setFixedWidth(118)
        self.theme_combo.addItem("Система", "system")
        self.theme_combo.addItem("Тёмная", "dark")
        self.theme_combo.addItem("Светлая", "light")
        self.theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        self.theme_combo.setToolTip("Тема интерфейса")
        layout.addWidget(self.theme_combo)
        return nav

    def _build_app_shell(self) -> QFrame:
        shell = QFrame()
        shell.setObjectName("AppShell")
        shell_layout = QVBoxLayout(shell)
        shell_layout.setContentsMargins(18, 16, 18, 16)
        shell_layout.setSpacing(12)

        heading_row = QHBoxLayout()
        heading = QVBoxLayout()
        heading.setSpacing(1)
        title = QLabel("Скачать видео или аудио")
        title.setObjectName("ShellTitle")
        subtitle = QLabel("Вставьте ссылку — Insight сам определит источник и доступные форматы.")
        subtitle.setObjectName("Muted")
        heading.addWidget(title)
        heading.addWidget(subtitle)
        heading_row.addLayout(heading)
        heading_row.addStretch()
        shell_layout.addLayout(heading_row)

        url_row = QHBoxLayout()
        url_row.setSpacing(8)
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://youtube.com/watch?v=…")
        self.url_input.returnPressed.connect(self.analyze_url)
        self.url_input.setClearButtonEnabled(True)
        url_row.addWidget(self.url_input, 1)

        paste = GlowButton("Вставить")
        paste.setObjectName("SmallButton")
        paste.setFixedWidth(88)
        paste.clicked.connect(self.paste_clipboard)
        paste.setToolTip("Вставить ссылку из буфера обмена")
        url_row.addWidget(paste)

        self.analyze_button = GlowButton("Анализировать", glow=True)
        self.analyze_button.setObjectName("Primary")
        self.analyze_button.setFixedWidth(142)
        self.analyze_button.clicked.connect(self.analyze_url)
        url_row.addWidget(self.analyze_button)
        shell_layout.addLayout(url_row)

        body = QHBoxLayout()
        body.setSpacing(12)
        body.addWidget(self._build_media_pane(), 3)
        body.addWidget(self._build_control_pane(), 2)
        shell_layout.addLayout(body, 1)

        return shell

    def _build_media_pane(self) -> QFrame:
        pane = QFrame()
        pane.setObjectName("MediaPane")
        layout = QVBoxLayout(pane)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        self.media_stack = QStackedWidget()
        self.media_stack.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.media_stack.addWidget(self._build_empty_media_page())
        self.media_stack.addWidget(self._build_result_media_page())
        layout.addWidget(self.media_stack, 1)
        return pane

    def _build_empty_media_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(8)
        layout.addStretch()

        mark = QLabel()
        mark.setAlignment(Qt.AlignCenter)
        mark_path = resource_path("app", "assets", "insight_mark.png")
        if mark_path.exists():
            pix = QPixmap(str(mark_path))
            mark.setPixmap(pix.scaled(72, 72, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        layout.addWidget(mark)

        empty_title = QLabel("Здесь появится превью")
        empty_title.setObjectName("MediaTitle")
        empty_title.setAlignment(Qt.AlignCenter)
        layout.addWidget(empty_title)

        empty_text = QLabel("Можно перетащить ссылку прямо в окно или вставить её сверху.")
        empty_text.setObjectName("Muted")
        empty_text.setAlignment(Qt.AlignCenter)
        empty_text.setWordWrap(True)
        layout.addWidget(empty_text)
        layout.addStretch()
        return page

    def _build_result_media_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(9)

        self.preview = PreviewLabel()
        self.preview.setObjectName("Preview")
        self.preview.setText("Превью")
        self.preview.setMinimumHeight(205)
        self.preview.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.preview, 1)

        self.video_title = QLabel()
        self.video_title.setObjectName("MediaTitle")
        self.video_title.setWordWrap(True)
        self.video_title.setMaximumHeight(46)
        layout.addWidget(self.video_title)

        self.video_meta = QLabel()
        self.video_meta.setObjectName("Muted")
        self.video_meta.setWordWrap(False)
        layout.addWidget(self.video_meta)
        return page

    def _build_control_pane(self) -> QFrame:
        pane = QFrame()
        pane.setObjectName("ControlPane")
        layout = QVBoxLayout(pane)
        layout.setContentsMargins(15, 14, 15, 14)
        layout.setSpacing(6)

        mode_label = QLabel("ФОРМАТ")
        mode_label.setObjectName("SectionLabel")
        layout.addWidget(mode_label)

        self.mode_selector = ModeSelector()
        self.mode_selector.modeChanged.connect(self._on_mode_changed)
        layout.addWidget(self.mode_selector)

        quality_label = QLabel("КАЧЕСТВО")
        quality_label.setObjectName("SectionLabel")
        layout.addWidget(quality_label)

        self.quality_combo = QComboBox()
        self.quality_combo.addItem("Сначала проанализируйте ссылку", None)
        self.quality_combo.setEnabled(False)
        layout.addWidget(self.quality_combo)

        folder = QFrame()
        folder.setObjectName("CompactField")
        folder_layout = QHBoxLayout(folder)
        folder_layout.setContentsMargins(11, 7, 7, 7)
        folder_layout.setSpacing(8)
        self.folder_value = ElideLabel(str(self.output_dir))
        self.folder_value.setObjectName("Strong")
        folder_layout.addWidget(self.folder_value, 1)
        folder_button = GlowButton("Изменить")
        folder_button.setObjectName("SmallButton")
        folder_button.clicked.connect(self.choose_output_dir)
        folder_layout.addWidget(folder_button)
        layout.addWidget(folder)

        self.status_panel = QFrame()
        self.status_panel.setObjectName("StatusPanel")
        status_layout = QVBoxLayout(self.status_panel)
        status_layout.setContentsMargins(11, 8, 11, 8)
        status_layout.setSpacing(5)

        status_header = QHBoxLayout()
        self.status_label = QLabel("Готово к работе")
        self.status_label.setObjectName("Strong")
        status_header.addWidget(self.status_label, 1)
        self.percent_label = QLabel("0%")
        self.percent_label.setObjectName("Percent")
        self.percent_label.setAlignment(Qt.AlignCenter)
        self.percent_label.setFixedWidth(56)
        status_header.addWidget(self.percent_label)
        status_layout.addLayout(status_header)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        status_layout.addWidget(self.progress)

        self.stats_label = ElideLabel("Вставьте ссылку и запустите анализ.")
        self.stats_label.setObjectName("Muted")
        status_layout.addWidget(self.stats_label)
        layout.addWidget(self.status_panel)

        layout.addStretch()

        self.download_button = GlowButton("Скачать", glow=True)
        self.download_button.setObjectName("Primary")
        self.download_button.setEnabled(False)
        self.download_button.clicked.connect(self.start_download)
        layout.addWidget(self.download_button)

        actions = QHBoxLayout()
        actions.setSpacing(7)
        self.open_file_button = GlowButton("Открыть файл")
        self.open_file_button.setObjectName("SmallButton")
        self.open_file_button.setEnabled(False)
        self.open_file_button.clicked.connect(self.open_downloaded_file)
        actions.addWidget(self.open_file_button, 1)

        self.open_folder_button = GlowButton("Папка")
        self.open_folder_button.setObjectName("SmallButton")
        self.open_folder_button.clicked.connect(self.open_download_folder)
        actions.addWidget(self.open_folder_button)

        self.cancel_button = GlowButton("Отмена")
        self.cancel_button.setObjectName("Danger")
        self.cancel_button.setVisible(False)
        self.cancel_button.clicked.connect(self.cancel_download)
        actions.addWidget(self.cancel_button)
        layout.addLayout(actions)

        return pane

    # ------------------------------------------------------------- settings

    def _restore_settings(self) -> None:
        self._select_data(self.theme_combo, self.theme_mode)
        self.mode_selector.set_mode(str(self.settings.value("mode", "video")))
        self._on_mode_changed(self.mode_selector.mode())

    def _connect_system_theme_listener(self) -> None:
        try:
            QGuiApplication.styleHints().colorSchemeChanged.connect(self._system_theme_changed)
        except Exception:
            pass

    def _install_shortcuts(self) -> None:
        focus_url = QShortcut(QKeySequence("Ctrl+L"), self)
        focus_url.activated.connect(self._focus_url)
        paste_analyze = QShortcut(QKeySequence("Ctrl+Shift+V"), self)
        paste_analyze.activated.connect(self._paste_and_analyze)

    def _focus_url(self) -> None:
        self.url_input.setFocus()
        self.url_input.selectAll()

    def _paste_and_analyze(self) -> None:
        self.paste_clipboard()
        self.analyze_url()

    def _system_theme_changed(self, _scheme) -> None:
        if self.theme_mode == "system":
            self._apply_theme()

    @staticmethod
    def _select_data(combo: QComboBox, value: str) -> None:
        for index in range(combo.count()):
            if combo.itemData(index) == value:
                combo.setCurrentIndex(index)
                return

    def _on_theme_changed(self) -> None:
        self.theme_mode = str(self.theme_combo.currentData())
        self.settings.setValue("theme", self.theme_mode)
        self._apply_theme()

    def _apply_theme(self) -> None:
        self.setStyleSheet(stylesheet(resolve_theme(self.theme_mode)))
        self._refresh_runtime_status()

    def _load_logo(self) -> None:
        path = resource_path("app", "assets", "insight_mark.png")
        if path.exists():
            pix = QPixmap(str(path))
            if not pix.isNull():
                self.logo.setPixmap(pix.scaled(30, 30, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def _refresh_runtime_status(self) -> None:
        if not hasattr(self, "ffmpeg_status"):
            return

        self._set_runtime_label(self.ffmpeg_status, "FFmpeg", find_ffmpeg_dir() is not None)
        self._set_runtime_label(self.deno_status, "Deno", find_deno() is not None)

    @staticmethod
    def _set_runtime_label(label: QLabel, name: str, ok: bool) -> None:
        label.setText(f"● {name}")
        label.setObjectName("RuntimeOk" if ok else "RuntimeWarn")
        label.style().unpolish(label)
        label.style().polish(label)

    # -------------------------------------------------------------- updates

    def _schedule_update_check(self) -> None:
        if not updates_configured():
            return
        try:
            last_check = float(self.settings.value("last_update_check", 0) or 0)
        except (TypeError, ValueError):
            last_check = 0
        if time.time() - last_check < 6 * 60 * 60:
            return
        QTimer.singleShot(1800, self._check_for_updates)

    def _check_for_updates(self) -> None:
        if self.update_check_worker and self.update_check_worker.isRunning():
            return

        worker = UpdateCheckWorker(self)
        worker.found.connect(self._update_found)
        worker.up_to_date.connect(self._update_up_to_date)
        worker.failed.connect(self._update_check_failed)
        self.update_check_worker = worker
        worker.start()

    def _update_found(self, info: UpdateInfo) -> None:
        self.settings.setValue("last_update_check", time.time())
        self.update_info = info
        self.update_button.setText(f"Обновить · {info.version}")
        self.update_button.setVisible(True)
        self.update_button.setToolTip(f"Доступна версия {info.version}. Нажмите, чтобы посмотреть изменения.")
        self._notify_update(info)

    def _update_up_to_date(self) -> None:
        self.settings.setValue("last_update_check", time.time())

    def _update_check_failed(self, message: str) -> None:
        # Проверка обновлений не должна мешать основной функции приложения.
        self.update_button.setToolTip(f"Не удалось проверить обновления: {message}")

    def _notify_update(self, info: UpdateInfo) -> None:
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        tray = QSystemTrayIcon(self.windowIcon(), self)
        tray.setToolTip("Insight Downloader")
        tray.show()
        tray.showMessage(
            "Доступно обновление",
            f"Insight Downloader {info.version} готов к установке.",
            QSystemTrayIcon.MessageIcon.Information,
            6500,
        )
        self._update_tray = tray
        QTimer.singleShot(8000, self._hide_update_tray)

    def _hide_update_tray(self) -> None:
        if self._update_tray is not None:
            self._update_tray.hide()
            self._update_tray.deleteLater()
            self._update_tray = None

    def _show_update_dialog(self) -> None:
        if self.update_info is None:
            return

        dialog = UpdateDialog(self.update_info, self)
        dialog.installRequested.connect(self._start_update_download)
        self.update_dialog = dialog
        dialog.exec()
        if self.update_dialog is dialog:
            self.update_dialog = None

    def _start_update_download(self) -> None:
        if self.update_info is None or self.update_dialog is None:
            return
        if not can_self_update():
            QMessageBox.information(
                self,
                "Самообновление",
                "Автоматическое обновление работает в собранной Windows-версии приложения. "
                "При запуске из исходников обновитесь через GitHub Release вручную.",
            )
            return
        if self.update_download_worker and self.update_download_worker.isRunning():
            return

        self.update_dialog.set_downloading(True)
        worker = UpdateDownloadWorker(self.update_info, self)
        worker.progress.connect(self._update_download_progress)
        worker.status.connect(self._update_download_status)
        worker.failed.connect(self._update_download_failed)
        worker.succeeded.connect(self._update_download_ready)
        self.update_download_worker = worker
        worker.start()

    def _update_download_progress(self, downloaded: int, total: int) -> None:
        if self.update_dialog is not None:
            self.update_dialog.set_progress(downloaded, total)

    def _update_download_status(self, text: str) -> None:
        if self.update_dialog is not None:
            self.update_dialog.set_status(text)

    def _update_download_failed(self, message: str) -> None:
        if self.update_dialog is not None:
            self.update_dialog.set_error(message)

    def _update_download_ready(self, archive: str) -> None:
        if self.update_dialog is not None:
            self.update_dialog.set_status("Перезапускаем приложение…")
        try:
            launch_self_update(archive, self.update_info.version if self.update_info else __version__)
        except Exception as exc:
            if self.update_dialog is not None:
                self.update_dialog.set_error(str(exc))
            return
        QApplication.quit()

    # --------------------------------------------------------------- input UX

    def paste_clipboard(self) -> None:
        text = QApplication.clipboard().text().strip()
        if text:
            self.url_input.setText(text)
            self.url_input.setFocus()
            self.url_input.setCursorPosition(len(text))

    def dragEnterEvent(self, event) -> None:
        mime = event.mimeData()
        if mime.hasUrls() or mime.hasText():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dropEvent(self, event) -> None:
        mime = event.mimeData()
        text = ""
        if mime.hasUrls() and mime.urls():
            text = mime.urls()[0].toString()
        elif mime.hasText():
            text = mime.text().strip()

        if text:
            self.url_input.setText(text)
            event.acceptProposedAction()
            self.analyze_url()
        else:
            super().dropEvent(event)

    # --------------------------------------------------------------- controls

    def _on_mode_changed(self, mode: str) -> None:
        self.settings.setValue("mode", mode)
        if mode in {"mp3", "wav"}:
            self.quality_combo.setEnabled(False)
            self.quality_combo.setToolTip("Для аудио используется лучшая доступная аудиодорожка.")
        else:
            self.quality_combo.setEnabled(self.media is not None)
            self.quality_combo.setToolTip("")

    def choose_output_dir(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "Выберите папку", str(self.output_dir))
        if selected:
            self.output_dir = Path(selected)
            self.folder_value.setText(str(self.output_dir))
            self.settings.setValue("output_dir", str(self.output_dir))

    def _youtube_preflight(self, url: str) -> bool:
        if not is_youtube_url(url):
            return True

        if find_chrome() is None:
            QMessageBox.warning(
                self,
                "Chrome / Chromium не найден",
                "Для YouTube PO Token provider нужен установленный Chrome или Chromium.",
            )
            return False

        if find_deno() is None:
            answer = QMessageBox.question(
                self,
                "Для YouTube нужен Deno",
                "Deno не найден. Современная поддержка YouTube в yt-dlp может работать неполно.\n\n"
                "Установка:\nwinget install --id=DenoLand.Deno -e\n\n"
                "Продолжить без Deno?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            return answer == QMessageBox.Yes

        return True

    # --------------------------------------------------------------- analysis

    def analyze_url(self) -> None:
        url = self.url_input.text().strip()
        if not url:
            self.url_input.setFocus()
            return
        if not self._youtube_preflight(url):
            return
        if self.extract_worker and self.extract_worker.isRunning():
            return

        self.media = None
        self.media_stack.setCurrentIndex(0)
        self.download_button.setEnabled(False)
        self.open_file_button.setEnabled(False)
        self.analyze_button.setEnabled(False)
        self.url_input.setEnabled(False)
        self.progress.setRange(0, 0)
        self.percent_label.setText("…")
        self.status_label.setText("Анализируем ссылку")
        self.stats_label.setText("Получаем метаданные и форматы…")

        worker = ExtractWorker(url, self)
        worker.succeeded.connect(self._extract_success)
        worker.failed.connect(self._extract_failed)
        worker.finished.connect(self._extract_finished)
        self.extract_worker = worker
        worker.start()

    def _extract_success(self, media: MediaInfo) -> None:
        self.media = media
        self.video_title.setText(media.title)
        self.video_title.setToolTip(media.title)
        self.video_meta.setText(
            f"{media.uploader}  •  {media.extractor}  •  {format_duration(media.duration)}"
        )
        self.video_meta.setToolTip(self.video_meta.text())
        self._populate_quality()
        self.media_stack.setCurrentIndex(1)
        self.download_button.setEnabled(True)
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.percent_label.setText("0%")
        self.status_label.setText("Готово к скачиванию")
        self.stats_label.setText("Выберите формат и качество.")

        self.preview.clear_source()
        self.preview.setText("Загрузка превью…")
        if media.thumbnail:
            worker = ThumbnailWorker(media.thumbnail, self)
            worker.succeeded.connect(self._thumbnail_ready)
            worker.failed.connect(lambda: self.preview.setText("Превью недоступно"))
            self.thumbnail_worker = worker
            worker.start()
        else:
            self.preview.setText("Нет превью")

    def _extract_failed(self, message: str) -> None:
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.percent_label.setText("0%")
        self.status_label.setText("Не удалось проанализировать")
        self.stats_label.setText("Проверьте ссылку или подробности ошибки.")
        QMessageBox.critical(self, "Ошибка анализа", message)

    def _extract_finished(self) -> None:
        self.analyze_button.setEnabled(True)
        self.url_input.setEnabled(True)

    def _thumbnail_ready(self, data: bytes) -> None:
        pix = QPixmap()
        if not pix.loadFromData(data):
            self.preview.setText("Превью недоступно")
            return
        self.preview.setText("")
        self.preview.set_source_pixmap(pix)

    def _populate_quality(self) -> None:
        self.quality_combo.clear()
        self.quality_combo.addItem("Лучшее доступное", None)
        if not self.media:
            return

        seen: set[int] = set()
        for fmt in self.media.formats:
            if not fmt.height or fmt.height in seen:
                continue
            seen.add(fmt.height)
            fps = f" · до {int(fmt.fps)} FPS" if fmt.fps else ""
            self.quality_combo.addItem(f"{fmt.height}p{fps}", fmt.height)

        self._on_mode_changed(self.mode_selector.mode())

    # --------------------------------------------------------------- download

    def start_download(self) -> None:
        if not self.media:
            return
        if find_ffmpeg_dir() is None:
            QMessageBox.warning(
                self,
                "FFmpeg не найден",
                "Положите ffmpeg.exe и ffprobe.exe в папку bin приложения.",
            )
            return
        if self.download_worker and self.download_worker.isRunning():
            return

        mode = self.mode_selector.mode()
        height = self.quality_combo.currentData() if mode == "video" else None

        self.download_button.setEnabled(False)
        self.analyze_button.setEnabled(False)
        self.url_input.setEnabled(False)
        self.cancel_button.setVisible(True)
        self.cancel_button.setEnabled(True)
        self.open_file_button.setEnabled(False)
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.percent_label.setText("0%")
        self.status_label.setText("Запускаем загрузку")
        self.stats_label.setText("Подготавливаем файл…")

        worker = DownloadWorker(
            url=self.media.url,
            output_dir=self.output_dir,
            mode=mode,
            height=height,
            parent=self,
        )
        worker.progress.connect(self._download_progress)
        worker.status.connect(self.status_label.setText)
        worker.succeeded.connect(self._download_success)
        worker.failed.connect(self._download_failed)
        worker.cancelled.connect(self._download_cancelled)
        worker.finished.connect(self._download_finished)
        self.download_worker = worker
        worker.start()

    def _download_progress(self, data: dict) -> None:
        downloaded = data.get("downloaded")
        total = data.get("total")

        if total:
            percent = int(max(0, min(100, (downloaded or 0) * 100 / total)))
            self.progress.setRange(0, 100)
            self.progress.setValue(percent)
            self.percent_label.setText(f"{percent}%")
        else:
            self.progress.setRange(0, 0)
            self.percent_label.setText("…")

        self.status_label.setText(f"{human_bytes(downloaded)} / {human_bytes(total)}")
        self.stats_label.setText(
            f"{human_speed(data.get('speed'))}  •  осталось {format_eta(data.get('eta'))}"
        )

    def _download_success(self, path: str) -> None:
        self.last_download_path = Path(path)
        self.progress.setRange(0, 100)
        self.progress.setValue(100)
        self.percent_label.setText("100%")
        self.status_label.setText("Скачивание завершено")
        self.stats_label.setText(str(path))
        self.open_file_button.setEnabled(True)

    def _download_failed(self, message: str) -> None:
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.percent_label.setText("0%")
        self.status_label.setText("Ошибка скачивания")
        self.stats_label.setText("Файл не сохранён.")
        QMessageBox.critical(self, "Ошибка скачивания", message)

    def _download_cancelled(self) -> None:
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.percent_label.setText("0%")
        self.status_label.setText("Скачивание отменено")
        self.stats_label.setText("Можно запустить загрузку снова.")

    def _download_finished(self) -> None:
        self.download_button.setEnabled(self.media is not None)
        self.analyze_button.setEnabled(True)
        self.url_input.setEnabled(True)
        self.cancel_button.setVisible(False)
        self.cancel_button.setEnabled(True)

    def cancel_download(self) -> None:
        if self.download_worker and self.download_worker.isRunning():
            self.cancel_button.setEnabled(False)
            self.status_label.setText("Отменяем загрузку…")
            self.download_worker.cancel()

    def open_downloaded_file(self) -> None:
        if not self.last_download_path or not self.last_download_path.exists():
            QMessageBox.information(self, "Insight Downloader", "Файл уже перемещён или удалён.")
            self.open_file_button.setEnabled(False)
            return
        open_path(self.last_download_path)

    def open_download_folder(self) -> None:
        open_path(self.output_dir)

    # --------------------------------------------------------------- lifetime

    def closeEvent(self, event) -> None:
        self.settings.setValue("window_geometry", self.saveGeometry())
        self.settings.setValue("output_dir", str(self.output_dir))
        super().closeEvent(event)
