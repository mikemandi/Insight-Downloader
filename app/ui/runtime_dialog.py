from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)

from app.core.formatting import human_bytes
from app.core.runtime_manager import MediaRuntimeInstallWorker


class RuntimeInstallDialog(QDialog):
    installed = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.worker: MediaRuntimeInstallWorker | None = None
        self.setWindowTitle("Медиадвижок Insight")
        self.setModal(True)
        self.setFixedWidth(440)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 22, 22, 20)
        layout.setSpacing(12)

        title = QLabel("Нужен медиадвижок")
        title.setObjectName("ShellTitle")
        layout.addWidget(title)

        text = QLabel(
            "Для объединения видео и аудио, а также MP3/WAV Insight использует FFmpeg. "
            "Мы скачиваем его один раз и храним отдельно от приложения, поэтому сам установщик остаётся компактным."
        )
        text.setWordWrap(True)
        text.setObjectName("Muted")
        layout.addWidget(text)

        self.status = QLabel("Готово к установке")
        self.status.setObjectName("Strong")
        layout.addWidget(self.status)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        layout.addWidget(self.progress)

        self.detail = QLabel("Потребуется подключение к интернету.")
        self.detail.setObjectName("Tiny")
        layout.addWidget(self.detail)

        buttons = QHBoxLayout()
        buttons.addStretch()
        self.cancel_button = QPushButton("Не сейчас")
        self.cancel_button.clicked.connect(self.reject)
        buttons.addWidget(self.cancel_button)

        self.install_button = QPushButton("Установить")
        self.install_button.setObjectName("Primary")
        self.install_button.clicked.connect(self.start_install)
        buttons.addWidget(self.install_button)
        layout.addLayout(buttons)

    def start_install(self) -> None:
        if self.worker and self.worker.isRunning():
            return

        self.install_button.setEnabled(False)
        self.cancel_button.setEnabled(False)
        self.progress.setRange(0, 0)
        self.status.setText("Подготавливаем загрузку…")

        worker = MediaRuntimeInstallWorker(self)
        worker.status.connect(self.status.setText)
        worker.progress.connect(self._on_progress)
        worker.succeeded.connect(self._on_success)
        worker.failed.connect(self._on_failed)
        self.worker = worker
        worker.start()

    def _on_progress(self, downloaded: int, total: int) -> None:
        if total > 0:
            percent = max(0, min(100, int(downloaded * 100 / total)))
            self.progress.setRange(0, 100)
            self.progress.setValue(percent)
            self.detail.setText(f"{human_bytes(downloaded)} / {human_bytes(total)}")
        else:
            self.progress.setRange(0, 0)
            self.detail.setText(human_bytes(downloaded))

    def _on_success(self, _path: str) -> None:
        self.progress.setRange(0, 100)
        self.progress.setValue(100)
        self.status.setText("Медиадвижок установлен")
        self.detail.setText("Можно продолжать загрузку.")
        self.installed.emit()
        self.accept()

    def _on_failed(self, message: str) -> None:
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.status.setText("Не удалось установить медиадвижок")
        self.detail.setText(message)
        self.detail.setWordWrap(True)
        self.install_button.setEnabled(True)
        self.cancel_button.setEnabled(True)
