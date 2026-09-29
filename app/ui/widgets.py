from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QEvent, QPropertyAnimation, Qt, Signal
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import (
    QButtonGroup,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
)


class GlowButton(QPushButton):
    """Push button with a subtle animated glow on hover.

    Qt stylesheets do not support CSS-style transitions, so the glow is
    implemented with QGraphicsDropShadowEffect and QPropertyAnimation.
    """

    def __init__(self, text: str = "", parent=None, *, glow: bool = False) -> None:
        super().__init__(text, parent)
        self._glow_enabled = glow
        self._shadow: QGraphicsDropShadowEffect | None = None
        self._animation: QPropertyAnimation | None = None

        if glow:
            self._shadow = QGraphicsDropShadowEffect(self)
            self._shadow.setBlurRadius(0)
            self._shadow.setOffset(0, 3)
            self._shadow.setColor(QColor(118, 139, 255, 105))
            self.setGraphicsEffect(self._shadow)

            self._animation = QPropertyAnimation(self._shadow, b"blurRadius", self)
            self._animation.setDuration(150)
            self._animation.setEasingCurve(QEasingCurve.OutCubic)

    def enterEvent(self, event: QEvent) -> None:
        if self.isEnabled():
            self._animate_glow(22)
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent) -> None:
        self._animate_glow(0)
        super().leaveEvent(event)

    def _animate_glow(self, target: float) -> None:
        if not self._glow_enabled or self._animation is None or self._shadow is None:
            return
        self._animation.stop()
        self._animation.setStartValue(self._shadow.blurRadius())
        self._animation.setEndValue(target)
        self._animation.start()


class ElideLabel(QLabel):
    """Single-line label that elides long text in the middle."""

    def __init__(self, text: str = "", parent=None) -> None:
        super().__init__(parent)
        self._full_text = text
        self.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.setToolTip(text)
        self._update_elided()

    def setText(self, text: str) -> None:  # noqa: N802 (Qt naming)
        self._full_text = text
        self.setToolTip(text)
        self._update_elided()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._update_elided()

    def _update_elided(self) -> None:
        fm = self.fontMetrics()
        available = max(20, self.width() - 4)
        super().setText(fm.elidedText(self._full_text, Qt.ElideMiddle, available))


class PreviewLabel(QLabel):
    """Preview label that keeps a source pixmap and center-crops responsively."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._source = QPixmap()
        self.setAlignment(Qt.AlignCenter)

    def set_source_pixmap(self, pixmap: QPixmap) -> None:
        self._source = pixmap
        self._render_pixmap()

    def clear_source(self) -> None:
        self._source = QPixmap()
        self.setPixmap(QPixmap())

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._render_pixmap()

    def _render_pixmap(self) -> None:
        if self._source.isNull() or self.width() <= 0 or self.height() <= 0:
            return

        scaled = self._source.scaled(
            self.size(),
            Qt.KeepAspectRatioByExpanding,
            Qt.SmoothTransformation,
        )
        x = max(0, (scaled.width() - self.width()) // 2)
        y = max(0, (scaled.height() - self.height()) // 2)
        cropped = scaled.copy(x, y, self.width(), self.height())
        self.setPixmap(cropped)


class ModeSelector(QWidget):
    modeChanged = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._buttons: dict[str, QPushButton] = {}

        for mode, title in (("video", "Видео"), ("mp3", "MP3"), ("wav", "WAV")):
            button = QPushButton(title)
            button.setObjectName("SegmentButton")
            button.setCheckable(True)
            button.setProperty("mode", mode)
            button.setCursor(Qt.PointingHandCursor)
            self._group.addButton(button)
            self._buttons[mode] = button
            layout.addWidget(button, 1)

        self._buttons["video"].setChecked(True)
        self._group.buttonClicked.connect(self._emit_mode)

    def mode(self) -> str:
        checked = self._group.checkedButton()
        if checked is None:
            return "video"
        return str(checked.property("mode"))

    def set_mode(self, mode: str) -> None:
        button = self._buttons.get(mode, self._buttons["video"])
        button.setChecked(True)

    def _emit_mode(self, button: QPushButton) -> None:
        self.modeChanged.emit(str(button.property("mode")))
