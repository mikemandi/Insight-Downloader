from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app import __version__
from app.core.runtime import find_chrome, find_ffmpeg_dir, find_qjs, resource_path
from app.ui.widgets import ChevronComboBox, ElideLabel, ToggleSwitch


class SettingsDialog(QDialog):
    themeChanged = Signal(str)
    outputDirectoryChanged = Signal(str)
    autoUpdatesChanged = Signal(bool)
    checkUpdatesRequested = Signal()

    BASE_WIDTH = 560
    BASE_HEIGHT = 646
    EXPANDED_HEIGHT = 742

    def __init__(
        self,
        theme_mode: str,
        output_dir: Path,
        auto_updates: bool = True,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.output_dir = Path(output_dir)
        self.setWindowTitle("Настройки Insight Downloader")
        self.setModal(True)
        self.setFixedSize(self.BASE_WIDTH, self.BASE_HEIGHT)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)

        root = QVBoxLayout(self)
        root.setContentsMargins(26, 24, 26, 22)
        root.setSpacing(0)

        heading = QLabel("Настройки")
        heading.setObjectName("PageTitle")
        root.addWidget(heading)
        root.addSpacing(22)

        # Appearance
        root.addWidget(self._section_label("Внешний вид"))
        root.addSpacing(10)
        appearance_row = QHBoxLayout()
        appearance_row.setSpacing(12)
        theme_text = QLabel("Тема")
        theme_text.setObjectName("Soft")
        appearance_row.addWidget(theme_text)
        appearance_row.addStretch()
        self.theme_combo = ChevronComboBox()
        self.theme_combo.setFixedWidth(170)
        self.theme_combo.addItem("Системная", "system")
        self.theme_combo.addItem("Тёмная", "dark")
        self.theme_combo.addItem("Светлая", "light")
        self._select(self.theme_combo, theme_mode)
        self.theme_combo.currentIndexChanged.connect(
            lambda: self.themeChanged.emit(str(self.theme_combo.currentData()))
        )
        appearance_row.addWidget(self.theme_combo)
        root.addLayout(appearance_row)

        root.addSpacing(20)
        root.addWidget(self._divider())
        root.addSpacing(20)

        # Downloads
        root.addWidget(self._section_label("Загрузки"))
        root.addSpacing(10)
        folder_row = QHBoxLayout()
        folder_row.setSpacing(10)
        folder_caption = QLabel("Папка по умолчанию")
        folder_caption.setObjectName("Soft")
        folder_row.addWidget(folder_caption)
        folder_row.addStretch()
        self.folder_value = ElideLabel(str(self.output_dir))
        self.folder_value.setObjectName("Muted")
        self.folder_value.setFixedWidth(205)
        folder_row.addWidget(self.folder_value)
        change_folder = QPushButton("Изменить")
        change_folder.setObjectName("TextButton")
        change_folder.clicked.connect(self._choose_folder)
        folder_row.addWidget(change_folder)
        root.addLayout(folder_row)

        root.addSpacing(20)
        root.addWidget(self._divider())
        root.addSpacing(20)

        # Updates
        root.addWidget(self._section_label("Обновления"))
        root.addSpacing(10)
        update_row = QHBoxLayout()
        update_row.setSpacing(12)
        update_label = QLabel("Автоматически проверять обновления")
        update_label.setObjectName("Soft")
        update_row.addWidget(update_label)
        update_row.addStretch()
        self.auto_update = ToggleSwitch()
        self.auto_update.setChecked(bool(auto_updates))
        self.auto_update.toggled.connect(self.autoUpdatesChanged.emit)
        update_row.addWidget(self.auto_update)
        root.addLayout(update_row)

        root.addSpacing(6)
        check_row = QHBoxLayout()
        check_row.addStretch()
        check_button = QPushButton("Проверить обновления")
        check_button.setObjectName("LinkButton")
        check_button.setCursor(Qt.PointingHandCursor)
        check_button.clicked.connect(self.checkUpdatesRequested.emit)
        check_row.addWidget(check_button)
        root.addLayout(check_row)

        root.addSpacing(24)
        root.addWidget(self._divider())
        root.addSpacing(24)

        # About — no duplicated publisher line.
        about_row = QHBoxLayout()
        about_row.setSpacing(13)
        icon = QLabel()
        icon.setFixedSize(44, 44)
        icon_path = resource_path("app", "assets", "insight_app_icon.png")
        if icon_path.exists():
            pix = QPixmap(str(icon_path))
            if not pix.isNull():
                icon.setPixmap(pix.scaled(44, 44, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        about_row.addWidget(icon)

        about_text = QVBoxLayout()
        about_text.setSpacing(2)
        name = QLabel("Insight Downloader")
        name.setObjectName("AboutTitle")
        version = QLabel(f"Версия {__version__}")
        version.setObjectName("AboutMeta")
        copyright_text = QLabel("© 2026 Insight Development")
        copyright_text.setObjectName("AboutMeta")
        about_text.addWidget(name)
        about_text.addWidget(version)
        about_text.addWidget(copyright_text)
        about_row.addLayout(about_text)
        about_row.addStretch()
        root.addLayout(about_row)

        root.addSpacing(16)
        self.diagnostics_toggle = QPushButton("Диагностика")
        self.diagnostics_toggle.setObjectName("DisclosureButton")
        self.diagnostics_toggle.setCheckable(True)
        self.diagnostics_toggle.setChecked(False)
        self.diagnostics_toggle.clicked.connect(self._toggle_diagnostics)
        root.addWidget(self.diagnostics_toggle, 0, Qt.AlignLeft)

        self.diagnostics = QFrame()
        self.diagnostics.setObjectName("DiagnosticsPanel")
        self.diagnostics.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        diag_layout = QVBoxLayout(self.diagnostics)
        diag_layout.setContentsMargins(14, 10, 14, 10)
        diag_layout.setSpacing(0)
        diag_layout.addWidget(self._component_row("Медиадвижок", find_ffmpeg_dir() is not None))
        diag_layout.addWidget(self._component_row("QuickJS", find_qjs() is not None))
        diag_layout.addWidget(self._component_row("Chromium", find_chrome() is not None))
        self.diagnostics.setVisible(False)
        root.addWidget(self.diagnostics)

        root.addStretch()

        buttons = QHBoxLayout()
        buttons.addStretch()
        done = QPushButton("Готово")
        done.setObjectName("Secondary")
        done.setFixedWidth(88)
        done.clicked.connect(self.accept)
        buttons.addWidget(done)
        root.addLayout(buttons)

    @staticmethod
    def _section_label(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("SectionTitle")
        return label

    @staticmethod
    def _divider() -> QFrame:
        line = QFrame()
        line.setObjectName("SettingsDivider")
        line.setFixedHeight(1)
        return line

    @staticmethod
    def _component_row(title: str, available: bool) -> QWidget:
        row = QWidget()
        row.setFixedHeight(30)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        marker = QLabel("●")
        marker.setObjectName("StatusDotReady" if available else "StatusDotMissing")
        marker.setFixedWidth(10)
        layout.addWidget(marker)

        name = QLabel(title)
        name.setObjectName("Soft")
        layout.addWidget(name)
        layout.addStretch()

        state = QLabel("Готов" if available else "Не найден")
        state.setObjectName("StatusReady" if available else "StatusMissing")
        layout.addWidget(state)
        return row

    def _choose_folder(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "Папка загрузок", str(self.output_dir))
        if not directory:
            return
        self.output_dir = Path(directory)
        self.folder_value.setText(str(self.output_dir))
        self.outputDirectoryChanged.emit(str(self.output_dir))

    def _toggle_diagnostics(self, checked: bool) -> None:
        self.diagnostics.setVisible(checked)
        self.diagnostics_toggle.setText("Диагностика  ⌃" if checked else "Диагностика  ⌄")
        self.setFixedHeight(self.EXPANDED_HEIGHT if checked else self.BASE_HEIGHT)

    @staticmethod
    def _select(combo: ChevronComboBox, value: str) -> None:
        for index in range(combo.count()):
            if combo.itemData(index) == value:
                combo.setCurrentIndex(index)
                return
