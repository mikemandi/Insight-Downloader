from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
)

from app.core.formatting import human_bytes
from app.core.update_service import UpdateInfo


class UpdateDialog(QDialog):
    installRequested = Signal()

    def __init__(self, info: UpdateInfo, parent=None) -> None:
        super().__init__(parent)
        self.info = info
        self._downloading = False
        self.setWindowTitle(f"Обновление {info.version}")
        self.setModal(True)
        self.setMinimumWidth(520)
        self.resize(560, 430)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(14)

        title = QLabel(f"Доступен Insight Downloader {info.version}")
        title.setObjectName("DialogTitle")
        layout.addWidget(title)

        subtitle = QLabel(
            f"Текущая версия будет обновлена автоматически без повторной установки. "
            f"Размер: {human_bytes(info.size)}"
        )
        subtitle.setObjectName("Muted")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        self.notes = QTextBrowser()
        self.notes.setObjectName("ReleaseNotes")
        self.notes.setOpenExternalLinks(True)
        self.notes.setMarkdown(info.notes or "В релизе нет описания изменений.")
        layout.addWidget(self.notes, 1)

        self.status = QLabel("Готово к загрузке")
        self.status.setObjectName("Muted")
        layout.addWidget(self.status)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.hide()
        layout.addWidget(self.progress)

        buttons = QHBoxLayout()
        buttons.addStretch()
        self.later_button = QPushButton("Позже")
        self.later_button.clicked.connect(self.reject)
        buttons.addWidget(self.later_button)
        self.install_button = QPushButton("Скачать и обновить")
        self.install_button.setObjectName("Primary")
        self.install_button.clicked.connect(self.installRequested.emit)
        buttons.addWidget(self.install_button)
        layout.addLayout(buttons)

    def set_downloading(self, active: bool) -> None:
        self._downloading = active
        self.install_button.setEnabled(not active)
        self.later_button.setEnabled(not active)
        self.progress.setVisible(active)

    def set_progress(self, downloaded: int, total: int) -> None:
        if total > 0:
            percent = int(downloaded * 100 / total)
            self.progress.setRange(0, 100)
            self.progress.setValue(max(0, min(100, percent)))
            self.status.setText(f"{human_bytes(downloaded)} / {human_bytes(total)}")
        else:
            self.progress.setRange(0, 0)
            self.status.setText(human_bytes(downloaded))

    def set_status(self, text: str) -> None:
        self.status.setText(text)

    def set_error(self, text: str) -> None:
        self.set_downloading(False)
        self.progress.setRange(0, 100)
        self.status.setText(text)

    def reject(self) -> None:
        if self._downloading:
            return
        super().reject()

    def closeEvent(self, event) -> None:
        if self._downloading:
            event.ignore()
            return
        super().closeEvent(event)
