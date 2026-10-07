from __future__ import annotations

import time
from pathlib import Path

from PySide6.QtCore import QSettings, Qt, QTimer
from PySide6.QtGui import QGuiApplication, QIcon, QKeySequence, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
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
from app.core.runtime import find_ffmpeg_dir, open_path, resource_path
from app.core.runtime_manager import MediaRuntimeInstallWorker
from app.core.update_apply import can_self_update, launch_self_update
from app.core.update_service import (
    UpdateCheckWorker,
    UpdateDownloadWorker,
    UpdateInfo,
    updates_configured,
)
from app.ui.runtime_dialog import RuntimeInstallDialog
from app.ui.settings_dialog import SettingsDialog
from app.ui.theme import resolve_theme, stylesheet
from app.ui.update_dialog import UpdateDialog
from app.ui.widgets import (
    BottomSheet,
    ChevronComboBox,
    ElideLabel,
    GlowButton,
    ModeSelector,
    PreviewLabel,
    SettingsButton,
    Spinner,
    Toast,
)


class MainWindow(QMainWindow):
    """Fixed, compact production UI built around one primary workflow."""

    WINDOW_WIDTH = 1000
    WINDOW_HEIGHT = 720

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
        self.runtime_dialog: RuntimeInstallDialog | None = None
        self.runtime_bootstrap_worker: MediaRuntimeInstallWorker | None = None
        self.runtime_bootstrap_error: str | None = None
        self._update_tray: QSystemTrayIcon | None = None
        self.last_download_path: Path | None = None
        self.output_dir = Path(self.settings.value("output_dir", str(Path.home() / "Downloads")))
        self.theme_mode = str(self.settings.value("theme", "system"))
        self.auto_updates = self._setting_bool("auto_updates", True)
        self._pending_download_after_runtime = False

        self.setWindowTitle("Insight Downloader")
        self.setFixedSize(self.WINDOW_WIDTH, self.WINDOW_HEIGHT)
        self.setWindowFlag(Qt.WindowMaximizeButtonHint, False)
        self.setAcceptDrops(True)

        icon_path = resource_path("app", "assets", "insight.ico")
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        self._build_ui()
        self._set_primary_step("analyze")
        self._restore_settings()
        self._apply_theme()
        self._connect_system_theme_listener()
        self._install_shortcuts()
        self._schedule_update_check()
        self._schedule_media_runtime_bootstrap()

    # ------------------------------------------------------------------ UI

    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("Root")
        self.setCentralWidget(root)

        outer = QVBoxLayout(root)
        outer.setContentsMargins(24, 18, 24, 20)
        outer.setSpacing(0)

        outer.addWidget(self._build_header())
        outer.addSpacing(12)

        divider = QFrame()
        divider.setObjectName("HeaderDivider")
        divider.setFixedHeight(1)
        outer.addWidget(divider)
        outer.addSpacing(18)

        intro = QVBoxLayout()
        intro.setSpacing(2)
        title = QLabel("Скачать видео или аудио")
        title.setObjectName("PageTitle")
        subtitle = QLabel("Вставьте ссылку — Insight определит источник и доступные форматы.")
        subtitle.setObjectName("Muted")
        intro.addWidget(title)
        intro.addWidget(subtitle)
        outer.addLayout(intro)
        outer.addSpacing(14)

        outer.addLayout(self._build_url_row())
        outer.addSpacing(16)

        body = QHBoxLayout()
        body.setSpacing(18)
        body.addWidget(self._build_media_pane(), 1)

        pane_divider = QFrame()
        pane_divider.setObjectName("PaneDivider")
        pane_divider.setFixedWidth(1)
        body.addWidget(pane_divider)

        body.addWidget(self._build_control_pane())
        outer.addLayout(body, 1)

        self.toast = Toast(root)
        self.bottom_sheet = BottomSheet(root)

    def _build_header(self) -> QWidget:
        header = QWidget()
        header.setFixedHeight(44)
        layout = QHBoxLayout(header)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.logo = QLabel()
        self.logo.setFixedSize(32, 32)
        self._load_logo()
        layout.addWidget(self.logo)

        brand = QLabel("Insight Downloader")
        brand.setObjectName("Brand")
        layout.addWidget(brand)
        layout.addStretch()

        self.update_button = GlowButton("Обновить")
        self.update_button.setObjectName("UpdateButton")
        self.update_button.setVisible(False)
        self.update_button.clicked.connect(self._show_update_dialog)
        layout.addWidget(self.update_button)

        self.settings_button = SettingsButton()
        self.settings_button.clicked.connect(self._show_settings)
        layout.addWidget(self.settings_button)
        return header

    def _build_url_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(8)

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Вставьте ссылку на YouTube, VK Video, Rutube и другие сайты")
        self.url_input.setClearButtonEnabled(True)
        self.url_input.returnPressed.connect(self.analyze_url)
        row.addWidget(self.url_input, 1)

        paste = QPushButton("Вставить")
        paste.setObjectName("GhostButton")
        paste.setFixedWidth(82)
        paste.clicked.connect(self.paste_clipboard)
        row.addWidget(paste)

        self.analyze_button = GlowButton("Анализировать", glow=True)
        self.analyze_button.setObjectName("Primary")
        self.analyze_button.setFixedWidth(138)
        self.analyze_button.clicked.connect(self.analyze_url)
        row.addWidget(self.analyze_button)
        return row

    def _build_media_pane(self) -> QWidget:
        pane = QWidget()
        pane.setFixedWidth(620)
        layout = QVBoxLayout(pane)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.media_stack = QStackedWidget()
        self.media_stack.addWidget(self._build_empty_media_page())
        self.media_stack.addWidget(self._build_result_media_page())
        self.media_stack.setCurrentIndex(0)
        layout.addWidget(self.media_stack, 1)
        return pane

    def _build_empty_media_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 26, 24, 34)
        layout.setSpacing(8)
        layout.addStretch(2)

        mark = QLabel()
        mark.setAlignment(Qt.AlignCenter)
        mark_path = resource_path("app", "assets", "insight_app_icon.png")
        if mark_path.exists():
            pix = QPixmap(str(mark_path))
            if not pix.isNull():
                mark.setPixmap(pix.scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        layout.addWidget(mark)
        layout.addSpacing(6)

        title = QLabel("Готов к новой загрузке")
        title.setObjectName("MediaTitle")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        text = QLabel("Вставьте ссылку сверху или перетащите её в окно.")
        text.setObjectName("Muted")
        text.setAlignment(Qt.AlignCenter)
        layout.addWidget(text)
        layout.addStretch(3)
        return page

    def _build_result_media_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(7)

        self.preview = PreviewLabel()
        self.preview.setObjectName("Preview")
        self.preview.setText("Загрузка превью…")
        self.preview.setFixedHeight(320)
        self.preview.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout.addWidget(self.preview)
        layout.addSpacing(3)

        self.video_title = QLabel()
        self.video_title.setObjectName("MediaTitle")
        self.video_title.setWordWrap(True)
        self.video_title.setMaximumHeight(42)
        layout.addWidget(self.video_title)

        # Production-style metadata: one compact line, no API-looking repetition.
        self.video_meta = ElideLabel()
        self.video_meta.setObjectName("Muted")
        layout.addWidget(self.video_meta)
        layout.addStretch()
        return page

    def _build_control_pane(self) -> QWidget:
        pane = QWidget()
        pane.setFixedWidth(280)
        layout = QVBoxLayout(pane)
        layout.setContentsMargins(2, 0, 0, 0)
        layout.setSpacing(0)

        label = QLabel("Формат")
        label.setObjectName("FieldLabel")
        layout.addWidget(label)
        layout.addSpacing(7)

        self.mode_selector = ModeSelector()
        self.mode_selector.modeChanged.connect(self._on_mode_changed)
        layout.addWidget(self.mode_selector)
        layout.addSpacing(16)

        self.quality_label = QLabel("Качество видео")
        self.quality_label.setObjectName("FieldLabel")
        layout.addWidget(self.quality_label)
        layout.addSpacing(7)

        self.quality_combo = ChevronComboBox()
        self.quality_combo.addItem("Сначала проанализируйте ссылку", None)
        self.quality_combo.setEnabled(False)
        self.quality_combo.currentIndexChanged.connect(self._quality_changed)
        layout.addWidget(self.quality_combo)
        layout.addSpacing(16)

        save_label = QLabel("Сохранение")
        save_label.setObjectName("FieldLabel")
        layout.addWidget(save_label)
        layout.addSpacing(6)

        save_row = QHBoxLayout()
        save_row.setSpacing(6)
        self.folder_value = ElideLabel(str(self.output_dir))
        self.folder_value.setObjectName("Soft")
        save_row.addWidget(self.folder_value, 1)
        folder_button = QPushButton("Изменить")
        folder_button.setObjectName("TextButton")
        folder_button.clicked.connect(self.choose_output_dir)
        save_row.addWidget(folder_button)
        layout.addLayout(save_row)

        layout.addSpacing(16)
        divider = QFrame()
        divider.setObjectName("SettingsDivider")
        divider.setFixedHeight(1)
        layout.addWidget(divider)
        layout.addSpacing(14)

        self.state_stack = QStackedWidget()
        self.state_stack.addWidget(self._build_ready_state())
        self.state_stack.addWidget(self._build_progress_state())
        self.state_stack.addWidget(self._build_success_state())
        self._set_state_page(0)
        self.state_stack.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.state_stack.setFixedHeight(66)
        layout.addWidget(self.state_stack)
        layout.addSpacing(10)

        self.download_button = GlowButton("Скачать", glow=True)
        self.download_button.setObjectName("Primary")
        self.download_button.setEnabled(False)
        self.download_button.clicked.connect(self.start_download)
        layout.addWidget(self.download_button)
        layout.addStretch()
        return pane

    def _build_ready_state(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        self.ready_title = QLabel("Сначала проанализируйте ссылку")
        self.ready_title.setObjectName("Strong")
        self.ready_title.setWordWrap(True)
        self.ready_hint = QLabel("После анализа появятся доступные параметры скачивания.")
        self.ready_hint.setObjectName("Muted")
        self.ready_hint.setWordWrap(True)
        layout.addWidget(self.ready_title)
        layout.addWidget(self.ready_hint)
        return page

    def _build_progress_state(self) -> QWidget:
        page = QWidget()
        page.setObjectName("DownloadState")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(7)

        header = QHBoxLayout()
        self.status_label = QLabel("Подготавливаем загрузку")
        self.status_label.setObjectName("Strong")
        header.addWidget(self.status_label, 1)
        self.percent_label = QLabel("0%")
        self.percent_label.setObjectName("Percent")
        header.addWidget(self.percent_label)
        layout.addLayout(header)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        layout.addWidget(self.progress)

        detail_row = QHBoxLayout()
        detail_row.setSpacing(6)
        self.spinner = Spinner()
        detail_row.addWidget(self.spinner)
        self.stats_label = ElideLabel("Соединяемся с источником…")
        self.stats_label.setObjectName("Muted")
        detail_row.addWidget(self.stats_label, 1)
        layout.addLayout(detail_row)

        self.cancel_button = QPushButton("Отменить загрузку")
        self.cancel_button.setObjectName("TextButton")
        self.cancel_button.clicked.connect(self.cancel_download)
        layout.addWidget(self.cancel_button, 0, Qt.AlignLeft)
        layout.addStretch()
        return page

    def _build_success_state(self) -> QWidget:
        page = QFrame()
        page.setObjectName("SuccessState")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(5)

        title = QLabel("✓  Загружено")
        title.setObjectName("SuccessText")
        layout.addWidget(title)

        self.success_filename = ElideLabel("")
        self.success_filename.setObjectName("Strong")
        layout.addWidget(self.success_filename)

        self.success_meta = QLabel("")
        self.success_meta.setObjectName("Muted")
        layout.addWidget(self.success_meta)

        actions = QHBoxLayout()
        actions.setSpacing(4)
        self.open_file_button = QPushButton("Открыть файл")
        self.open_file_button.setObjectName("GhostButton")
        self.open_file_button.clicked.connect(self.open_downloaded_file)
        actions.addWidget(self.open_file_button)
        self.open_folder_button = QPushButton("Показать в папке")
        self.open_folder_button.setObjectName("GhostButton")
        self.open_folder_button.clicked.connect(self.open_download_folder)
        actions.addWidget(self.open_folder_button)
        actions.addStretch()
        layout.addLayout(actions)
        return page

    def _set_state_page(self, index: int) -> None:
        """Keep the action column dense instead of reserving empty height."""
        heights = {0: 66, 1: 112, 2: 118}
        self.state_stack.setCurrentIndex(index)
        self.state_stack.setFixedHeight(heights.get(index, 66))

    # ------------------------------------------------------------- settings

    def _restore_settings(self) -> None:
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

    def _set_theme_mode(self, mode: str) -> None:
        self.theme_mode = mode
        self.settings.setValue("theme", mode)
        self._apply_theme()

    def _apply_theme(self) -> None:
        self.setStyleSheet(stylesheet(resolve_theme(self.theme_mode)))

    def _load_logo(self) -> None:
        path = resource_path("app", "assets", "insight_app_icon.png")
        if path.exists():
            pix = QPixmap(str(path))
            if not pix.isNull():
                self.logo.setPixmap(pix.scaled(30, 30, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def _show_settings(self) -> None:
        dialog = SettingsDialog(self.theme_mode, self.output_dir, self.auto_updates, self)
        dialog.themeChanged.connect(self._set_theme_mode)
        dialog.outputDirectoryChanged.connect(self._set_output_dir)
        dialog.autoUpdatesChanged.connect(self._set_auto_updates)
        dialog.checkUpdatesRequested.connect(self._manual_update_check)
        dialog.setStyleSheet(self.styleSheet())
        dialog.exec()

    def _set_output_dir(self, path: str) -> None:
        self.output_dir = Path(path)
        self.folder_value.setText(str(self.output_dir))
        self.settings.setValue("output_dir", str(self.output_dir))

    def _set_auto_updates(self, enabled: bool) -> None:
        self.auto_updates = bool(enabled)
        self.settings.setValue("auto_updates", self.auto_updates)

    # ------------------------------------------------------- media runtime

    def _schedule_media_runtime_bootstrap(self) -> None:
        """Prepare FFmpeg automatically in production without bloating the installer."""
        if find_ffmpeg_dir() is not None or not updates_configured():
            return
        # Give the main window time to appear before doing network work.
        QTimer.singleShot(2200, self._bootstrap_media_runtime)

    def _bootstrap_media_runtime(self) -> None:
        if find_ffmpeg_dir() is not None:
            return
        if self.runtime_bootstrap_worker and self.runtime_bootstrap_worker.isRunning():
            return

        self.runtime_bootstrap_error = None
        worker = MediaRuntimeInstallWorker(self)
        worker.succeeded.connect(self._background_runtime_installed)
        worker.failed.connect(self._background_runtime_failed)
        self.runtime_bootstrap_worker = worker
        self.toast.show_message("Подготавливаем медиадвижок в фоне…")
        worker.start()

    def _background_runtime_installed(self, _path: str) -> None:
        self.runtime_bootstrap_error = None
        self.toast.show_message("Медиадвижок готов")
        if self._pending_download_after_runtime:
            self._pending_download_after_runtime = False
            QTimer.singleShot(120, self._begin_download)

    def _background_runtime_failed(self, message: str) -> None:
        # Do not interrupt startup. If the user starts a download, the normal
        # runtime dialog will explain the problem and allow an explicit retry.
        self.runtime_bootstrap_error = message

    # -------------------------------------------------------------- updates

    def _schedule_update_check(self) -> None:
        if not self.auto_updates or not updates_configured():
            return
        try:
            last_check = float(self.settings.value("last_update_check", 0) or 0)
        except (TypeError, ValueError):
            last_check = 0
        if time.time() - last_check < 6 * 60 * 60:
            return
        QTimer.singleShot(1600, self._check_for_updates)

    def _manual_update_check(self) -> None:
        self.settings.setValue("last_update_check", 0)
        self._check_for_updates(show_up_to_date=True)

    def _check_for_updates(self, show_up_to_date: bool = False) -> None:
        if self.update_check_worker and self.update_check_worker.isRunning():
            return
        worker = UpdateCheckWorker(self)
        worker.found.connect(self._update_found)
        worker.up_to_date.connect(lambda: self._update_up_to_date(show_up_to_date))
        worker.failed.connect(self._update_check_failed)
        self.update_check_worker = worker
        worker.start()

    def _update_found(self, info: UpdateInfo) -> None:
        self.settings.setValue("last_update_check", time.time())
        self.update_info = info
        self.update_button.setText(f"Обновить · {info.version}")
        self.update_button.setVisible(True)
        self._notify_update(info)

    def _update_up_to_date(self, show_message: bool = False) -> None:
        self.settings.setValue("last_update_check", time.time())
        if show_message:
            self.toast.show_message("У вас последняя версия Insight Downloader")

    def _update_check_failed(self, message: str) -> None:
        self.toast.show_message("Не удалось проверить обновления")
        self.update_button.setToolTip(message)

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
        dialog.setStyleSheet(self.styleSheet())
        dialog.installRequested.connect(self._start_update_download)
        self.update_dialog = dialog
        dialog.exec()
        if self.update_dialog is dialog:
            self.update_dialog = None

    def _start_update_download(self) -> None:
        if self.update_info is None or self.update_dialog is None:
            return
        if not can_self_update():
            self.toast.show_message("Самообновление доступно в установленной Windows-версии")
            return
        if self.update_download_worker and self.update_download_worker.isRunning():
            return

        self.update_dialog.set_downloading(True)
        worker = UpdateDownloadWorker(self.update_info, self)
        worker.progress.connect(self.update_dialog.set_progress)
        worker.status.connect(self.update_dialog.set_status)
        worker.succeeded.connect(self._apply_update)
        worker.failed.connect(self._update_download_failed)
        self.update_download_worker = worker
        worker.start()

    def _apply_update(self, zip_path: str) -> None:
        try:
            if self.update_info is None:
                return
            launch_self_update(zip_path, self.update_info.version)
            QApplication.quit()
        except Exception as exc:
            self._update_download_failed(str(exc))

    def _update_download_failed(self, message: str) -> None:
        if self.update_dialog:
            self.update_dialog.set_error(message)

    # -------------------------------------------------------------- input

    def paste_clipboard(self) -> None:
        text = QApplication.clipboard().text().strip()
        if text:
            self.url_input.setText(text)
            self.url_input.setFocus()

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        text = event.mimeData().text().strip()
        if text:
            self.url_input.setText(text)
            event.acceptProposedAction()
            self.analyze_url()

    # -------------------------------------------------------------- analyze

    def analyze_url(self) -> None:
        url = self.url_input.text().strip()
        if not url:
            self._show_error("Нужна ссылка", "Вставьте ссылку на видео и повторите попытку.")
            return
        if self.extract_worker and self.extract_worker.isRunning():
            return

        self.media = None
        self._set_primary_step("analyze")
        self.media_stack.setCurrentIndex(0)
        self.download_button.setEnabled(False)
        self._set_state_page(0)
        self.ready_title.setText("Анализируем ссылку…")
        self.ready_hint.setText("Получаем метаданные и доступные форматы.")
        self.quality_combo.clear()
        self.quality_combo.addItem("Анализируем…", None)
        self.quality_combo.setEnabled(False)

        self.analyze_button.setEnabled(False)
        self.analyze_button.setText("Анализируем…")
        self.url_input.setEnabled(False)

        worker = ExtractWorker(url, parent=self)
        worker.succeeded.connect(self._on_extract_success)
        worker.failed.connect(self._on_extract_failed)
        worker.finished.connect(self._on_extract_finished)
        self.extract_worker = worker
        worker.start()

    def _on_extract_success(self, media: MediaInfo) -> None:
        self.media = media
        self.media_stack.setCurrentIndex(1)
        self.video_title.setText(media.title)
        compact_meta = [media.extractor, format_duration(media.duration)]
        if media.uploader and media.uploader.strip() and media.uploader.strip().lower() != media.title.strip().lower():
            compact_meta.append(media.uploader.strip())
        self.video_meta.setText("  ·  ".join(part for part in compact_meta if part and part != "—"))
        self._refresh_quality_for_mode()

        self.ready_title.setText("Готово к скачиванию")
        self.ready_hint.setText(self._selection_summary())
        self._set_state_page(0)
        self.download_button.setEnabled(True)
        self._set_primary_step("download")

        self.preview.clear_source()
        self.preview.setText("Загрузка превью…")
        if media.thumbnail:
            thumb = ThumbnailWorker(media.thumbnail, self)
            thumb.succeeded.connect(self._set_thumbnail)
            thumb.failed.connect(lambda: self.preview.setText("Превью недоступно"))
            self.thumbnail_worker = thumb
            thumb.start()
        else:
            self.preview.setText("Превью недоступно")

    def _on_extract_failed(self, message: str) -> None:
        self.ready_title.setText("Не удалось проанализировать ссылку")
        self.ready_hint.setText("Проверьте адрес и попробуйте ещё раз.")
        self._show_error("Не удалось обработать ссылку", self._short_error(message))

    def _on_extract_finished(self) -> None:
        self.analyze_button.setEnabled(True)
        self.analyze_button.setText("Обновить" if self.media else "Анализировать")
        self.url_input.setEnabled(True)
        if self.media:
            self._set_primary_step("download")
        else:
            self._set_primary_step("analyze")

    def _set_thumbnail(self, data: bytes) -> None:
        pixmap = QPixmap()
        if not pixmap.loadFromData(data):
            self.preview.setText("Превью недоступно")
            return
        self.preview.setText("")
        self.preview.set_source_pixmap(pixmap)

    def _refresh_quality_for_mode(self) -> None:
        mode = self.mode_selector.mode()
        self.quality_combo.clear()

        if not self.media:
            self.quality_label.setText("Качество видео" if mode == "video" else "Качество аудио")
            self.quality_combo.addItem("Сначала проанализируйте ссылку", None)
            self.quality_combo.setEnabled(False)
            return

        self.quality_combo.setEnabled(True)
        if mode == "video":
            self.quality_label.setText("Качество видео")
            self.quality_combo.addItem("Лучшее доступное", None)
            seen: set[int] = set()
            for fmt in self.media.formats:
                if not fmt.height or fmt.height in seen:
                    continue
                seen.add(fmt.height)
                fps = f" · до {int(fmt.fps)} FPS" if fmt.fps else ""
                self.quality_combo.addItem(f"{fmt.height}p{fps}", fmt.height)
        elif mode == "mp3":
            self.quality_label.setText("Качество аудио")
            self.quality_combo.addItem("320 кбит/с · максимальное", "320")
            self.quality_combo.addItem("256 кбит/с", "256")
            self.quality_combo.addItem("192 кбит/с", "192")
            self.quality_combo.addItem("128 кбит/с", "128")
        else:
            self.quality_label.setText("Качество аудио")
            self.quality_combo.addItem("Исходная частота · 16 бит", "source")
            self.quality_combo.addItem("48 кГц · 24 бит", "48k24")
            self.quality_combo.addItem("48 кГц · 16 бит", "48k16")
            self.quality_combo.addItem("44,1 кГц · 16 бит", "44k16")

    # ------------------------------------------------------------- download

    def _on_mode_changed(self, mode: str) -> None:
        self.settings.setValue("mode", mode)
        self._refresh_quality_for_mode()
        if self.media:
            self.ready_hint.setText(self._selection_summary())

    def _quality_changed(self, _index: int) -> None:
        if self.media:
            self.ready_hint.setText(self._selection_summary())

    def _selection_summary(self) -> str:
        mode = self.mode_selector.mode()
        mode_title = {"video": "Видео", "mp3": "MP3", "wav": "WAV"}.get(mode, "Файл")
        quality = self.quality_combo.currentText().strip()
        if not quality or quality.startswith("Сначала"):
            return f"{mode_title}"
        return f"{mode_title}  ·  {quality}"

    def _set_primary_step(self, step: str) -> None:
        """Only one action should look primary at a time."""
        analyze_is_primary = step == "analyze"
        self.analyze_button.setObjectName("Primary" if analyze_is_primary else "Secondary")
        self.download_button.setObjectName("Secondary" if analyze_is_primary else "Primary")
        self.analyze_button.set_glow_enabled(analyze_is_primary)
        self.download_button.set_glow_enabled(not analyze_is_primary)
        for button in (self.analyze_button, self.download_button):
            button.style().unpolish(button)
            button.style().polish(button)
            button.update()

    def choose_output_dir(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "Куда сохранять файлы", str(self.output_dir))
        if directory:
            self._set_output_dir(directory)

    def start_download(self) -> None:
        if not self.media:
            self._show_error("Сначала проанализируйте ссылку", "Нажмите «Анализировать», чтобы Insight получил доступные форматы и качество.")
            return
        if self.download_worker and self.download_worker.isRunning():
            return

        if find_ffmpeg_dir() is None:
            self._pending_download_after_runtime = True
            if self.runtime_bootstrap_worker and self.runtime_bootstrap_worker.isRunning():
                self.toast.show_message("Медиадвижок ещё устанавливается…")
                return
            self._install_media_runtime()
            return

        self._begin_download()

    def _install_media_runtime(self) -> None:
        dialog = RuntimeInstallDialog(self)
        dialog.setStyleSheet(self.styleSheet())
        dialog.installed.connect(self._runtime_installed)
        self.runtime_dialog = dialog
        dialog.exec()
        if dialog.result() != QDialog.Accepted:
            self._pending_download_after_runtime = False
        self.runtime_dialog = None

    def _runtime_installed(self) -> None:
        self.toast.show_message("Медиадвижок установлен")
        if self._pending_download_after_runtime:
            self._pending_download_after_runtime = False
            QTimer.singleShot(120, self._begin_download)

    def _begin_download(self) -> None:
        if not self.media:
            return

        mode = self.mode_selector.mode()
        selected_quality = self.quality_combo.currentData()
        height = selected_quality if mode == "video" else None
        audio_quality = str(selected_quality) if mode in {"mp3", "wav"} and selected_quality is not None else None

        self.last_download_path = None
        self.download_button.setEnabled(False)
        self.analyze_button.setEnabled(False)
        self.url_input.setEnabled(False)
        self.cancel_button.setEnabled(True)

        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.percent_label.setText("0%")
        self.status_label.setText("Подготавливаем загрузку")
        self.stats_label.setText("Соединяемся с источником…")
        self.spinner.start()
        self._set_state_page(1)

        worker = DownloadWorker(
            url=self.media.url,
            output_dir=self.output_dir,
            mode=mode,
            height=height,
            audio_quality=audio_quality,
            parent=self,
        )
        worker.progress.connect(self._on_download_progress)
        worker.status.connect(self._on_download_status)
        worker.succeeded.connect(self._on_download_success)
        worker.failed.connect(self._on_download_failed)
        worker.cancelled.connect(self._on_download_cancelled)
        worker.finished.connect(self._on_download_finished)
        self.download_worker = worker
        worker.start()

    def _on_download_status(self, text: str) -> None:
        self.status_label.setText(text)
        self.stats_label.setText(text)

    def _on_download_progress(self, data: dict) -> None:
        downloaded = data.get("downloaded")
        total = data.get("total")
        speed = data.get("speed")
        eta = data.get("eta")

        if total:
            percent = max(0, min(100, int((downloaded or 0) * 100 / total)))
            self.progress.setRange(0, 100)
            self.progress.setValue(percent)
            self.percent_label.setText(f"{percent}%")
        else:
            self.progress.setRange(0, 0)
            self.percent_label.setText("…")

        left = f"{human_bytes(downloaded)} / {human_bytes(total)}"
        right = f"{human_speed(speed)} · {format_eta(eta)}"
        self.status_label.setText("Скачивание")
        self.stats_label.setText(f"{left} · {right}")

    def _on_download_success(self, path: str) -> None:
        self.last_download_path = Path(path)
        self.spinner.stop()

        size = human_bytes(self.last_download_path.stat().st_size) if self.last_download_path.exists() else ""
        ext = self.last_download_path.suffix.lstrip(".").upper()
        meta = " · ".join(part for part in (size, ext) if part)
        self.success_filename.setText(self.last_download_path.name)
        self.success_meta.setText(meta)
        self._set_state_page(2)
        self._set_primary_step("download")
        self.toast.show_message("Файл успешно сохранён")

    def _on_download_failed(self, message: str) -> None:
        self.spinner.stop()
        self._set_state_page(0)
        self.ready_title.setText("Загрузка не завершена")
        self.ready_hint.setText("Исправьте причину ошибки и попробуйте снова.")
        self._show_error("Не удалось скачать файл", self._short_error(message))

    def _on_download_cancelled(self) -> None:
        self.spinner.stop()
        self._set_state_page(0)
        self.ready_title.setText("Загрузка отменена")
        self.ready_hint.setText("Можно изменить параметры и начать снова.")

    def _on_download_finished(self) -> None:
        self.spinner.stop()
        self.download_button.setEnabled(self.media is not None)
        self.analyze_button.setEnabled(True)
        self.url_input.setEnabled(True)
        self.cancel_button.setEnabled(True)

    def cancel_download(self) -> None:
        if self.download_worker and self.download_worker.isRunning():
            self.status_label.setText("Отменяем…")
            self.stats_label.setText("Завершаем текущую операцию.")
            self.cancel_button.setEnabled(False)
            self.download_worker.cancel()

    def open_downloaded_file(self) -> None:
        if not self.last_download_path:
            return
        if not self.last_download_path.exists():
            self.toast.show_message("Файл был перемещён или удалён")
            return
        open_path(self.last_download_path)

    def open_download_folder(self) -> None:
        open_path(self.last_download_path.parent if self.last_download_path else self.output_dir)

    # -------------------------------------------------------------- helpers

    def _show_error(self, title: str, message: str) -> None:
        self.bottom_sheet.show_error(title, message)

    @staticmethod
    def _short_error(message: str) -> str:
        first = message.strip().split("\n\n", 1)[0].strip()
        return first if len(first) <= 360 else first[:357] + "…"

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if hasattr(self, "toast") and self.toast.isVisible():
            self.toast.show_message(self.toast.text())
        if hasattr(self, "bottom_sheet") and self.bottom_sheet.isVisible():
            self.bottom_sheet.setGeometry(self.centralWidget().rect())

    @staticmethod
    def _setting_bool(key: str, default: bool) -> bool:
        settings = QSettings("Insight Development", "Insight Downloader")
        value = settings.value(key, default)
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in {"1", "true", "yes", "on"}
