from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QEvent, QPoint, QPropertyAnimation, QRect, Qt, Signal, QTimer
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QPixmap, QPolygonF
from PySide6.QtWidgets import (
    QAbstractButton,
    QButtonGroup,
    QComboBox,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class GlowButton(QPushButton):
    """Restrained primary/secondary button with a soft hover glow."""

    def __init__(self, text: str = "", parent=None, *, glow: bool = False) -> None:
        super().__init__(text, parent)
        self.setCursor(Qt.PointingHandCursor)
        self._glow_enabled = glow
        self._shadow: QGraphicsDropShadowEffect | None = None
        self._animation: QPropertyAnimation | None = None

        if glow:
            self._shadow = QGraphicsDropShadowEffect(self)
            self._shadow.setBlurRadius(0)
            self._shadow.setOffset(0, 2)
            self._shadow.setColor(QColor(142, 92, 255, 72))
            self.setGraphicsEffect(self._shadow)

            self._animation = QPropertyAnimation(self._shadow, b"blurRadius", self)
            self._animation.setDuration(150)
            self._animation.setEasingCurve(QEasingCurve.OutCubic)

    def enterEvent(self, event: QEvent) -> None:
        if self.isEnabled():
            self._animate_glow(18)
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent) -> None:
        self._animate_glow(0)
        super().leaveEvent(event)

    def set_glow_enabled(self, enabled: bool) -> None:
        self._glow_enabled = bool(enabled)
        if not self._glow_enabled and self._shadow is not None:
            self._shadow.setBlurRadius(0)

    def _animate_glow(self, target: float) -> None:
        if not self._glow_enabled or self._animation is None or self._shadow is None:
            return
        self._animation.stop()
        self._animation.setStartValue(self._shadow.blurRadius())
        self._animation.setEndValue(target)
        self._animation.start()


class SettingsButton(QPushButton):
    """Painted line icon button; avoids platform emoji rendering."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("IconButton")
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(36, 36)
        self.setToolTip("Настройки")

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        color = QColor("#8B95A7")
        if self.underMouse():
            color = QColor("#C9D1DD")
        if not self.isEnabled():
            color.setAlpha(90)
        pen = QPen(color, 1.7, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)

        cx, cy = self.width() / 2, self.height() / 2
        # Minimal settings glyph: center ring + eight short radial teeth.
        painter.drawEllipse(QPoint(int(cx), int(cy)), 4, 4)
        for dx, dy in ((0, -9), (6, -6), (9, 0), (6, 6), (0, 9), (-6, 6), (-9, 0), (-6, -6)):
            sx = cx + dx * 0.64
            sy = cy + dy * 0.64
            ex = cx + dx
            ey = cy + dy
            painter.drawLine(QPoint(int(sx), int(sy)), QPoint(int(ex), int(ey)))


class ChevronComboBox(QComboBox):
    """QComboBox with an explicit painted chevron so it always looks clickable."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setCursor(Qt.PointingHandCursor)

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        color = self.palette().text().color()
        if not self.isEnabled():
            color.setAlpha(90)
        pen = QPen(color, 1.6, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        painter.setPen(pen)
        x = self.width() - 18
        y = self.height() // 2 - 2
        painter.drawLine(x - 4, y, x, y + 4)
        painter.drawLine(x, y + 4, x + 4, y)


class ElideLabel(QLabel):
    """Single-line label that safely elides long text in the middle."""

    def __init__(self, text: str = "", parent=None) -> None:
        super().__init__(parent)
        self._full_text = text
        self.setToolTip(text)
        self._update_elided()

    def setText(self, text: str) -> None:  # noqa: N802
        self._full_text = text
        self.setToolTip(text)
        self._update_elided()

    def fullText(self) -> str:  # noqa: N802
        return self._full_text

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._update_elided()

    def _update_elided(self) -> None:
        fm = self.fontMetrics()
        available = max(24, self.width() - 6)
        super().setText(fm.elidedText(self._full_text, Qt.ElideMiddle, available))


class PreviewLabel(QLabel):
    """Thumbnail view with a restrained backdrop and aspect-ratio-safe content.

    Wide thumbnails fill the surface naturally. Portrait/square media is contained
    instead of being aggressively cropped; a dimmed copy of the same thumbnail is
    used as the backdrop so the preview still feels intentional.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._source = QPixmap()
        self._placeholder = ""
        self.setAlignment(Qt.AlignCenter)

    def setText(self, text: str) -> None:  # noqa: N802
        self._placeholder = text
        if self._source.isNull():
            super().setText(text)

    def set_source_pixmap(self, pixmap: QPixmap) -> None:
        self._source = pixmap
        super().setText("")
        self.update()

    def clear_source(self) -> None:
        self._source = QPixmap()
        self.setPixmap(QPixmap())
        super().setText(self._placeholder)
        self.update()

    def paintEvent(self, event) -> None:
        if self._source.isNull():
            super().paintEvent(event)
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        clip = QPainterPath()
        clip.addRoundedRect(self.rect(), 10, 10)
        painter.setClipPath(clip)

        # Soft full-bleed backdrop. It gives portrait thumbnails a deliberate
        # presentation without stretching or cutting away most of the image.
        backdrop = self._source.scaled(
            self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation
        )
        bx = (self.width() - backdrop.width()) // 2
        by = (self.height() - backdrop.height()) // 2
        painter.setOpacity(0.20)
        painter.drawPixmap(bx, by, backdrop)
        painter.setOpacity(1.0)
        painter.fillRect(self.rect(), QColor(5, 8, 13, 118))

        # Main image is always kept intact.
        foreground = self._source.scaled(
            self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        fx = (self.width() - foreground.width()) // 2
        fy = (self.height() - foreground.height()) // 2
        painter.drawPixmap(fx, fy, foreground)


class ModeSelector(QWidget):
    modeChanged = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

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
        return str(checked.property("mode")) if checked else "video"

    def set_mode(self, mode: str) -> None:
        self._buttons.get(mode, self._buttons["video"]).setChecked(True)

    def _emit_mode(self, button: QPushButton) -> None:
        self.modeChanged.emit(str(button.property("mode")))


class ToggleSwitch(QAbstractButton):
    """Small native-looking toggle without platform checkbox chrome."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(38, 22)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        rect = self.rect().adjusted(1, 1, -1, -1)
        if self.isChecked():
            track = QColor(140, 124, 255)
            knob = QColor(255, 255, 255)
            knob_x = rect.right() - 18
        else:
            track = QColor(125, 135, 150, 72)
            knob = QColor(220, 225, 232)
            knob_x = rect.left() + 2
        painter.setPen(Qt.NoPen)
        painter.setBrush(track)
        painter.drawRoundedRect(rect, 10, 10)
        painter.setBrush(knob)
        painter.drawEllipse(int(knob_x), rect.top() + 2, 16, 16)


class Spinner(QWidget):
    """Tiny paint-based spinner for analysis/runtime setup states."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFixedSize(16, 16)
        self._angle = 0
        self._timer = QTimer(self)
        self._timer.setInterval(55)
        self._timer.timeout.connect(self._tick)
        self.hide()

    def start(self) -> None:
        self.show()
        self._timer.start()

    def stop(self) -> None:
        self._timer.stop()
        self.hide()

    def _tick(self) -> None:
        self._angle = (self._angle + 30) % 360
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        pen = QPen(self.palette().highlight().color())
        pen.setWidth(2)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        rect = self.rect().adjusted(3, 3, -3, -3)
        painter.drawArc(rect, (90 - self._angle) * 16, -250 * 16)


class Toast(QLabel):
    """Non-blocking feedback bubble shown over the main window."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setObjectName("Toast")
        self.setAlignment(Qt.AlignCenter)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.hide()
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide)

    def show_message(self, text: str, duration_ms: int = 2400) -> None:
        self.setText(text)
        self.adjustSize()
        width = max(220, min(440, self.width() + 32))
        self.resize(width, 40)
        parent = self.parentWidget()
        if parent:
            x = (parent.width() - width) // 2
            y = max(18, parent.height() - 60)
            self.move(x, y)
        self.raise_()
        self.show()
        self._timer.start(duration_ms)


class BottomSheet(QWidget):
    """Modal, animated bottom sheet for errors and important feedback."""

    closed = Signal()

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setObjectName("BottomSheetOverlay")
        self.hide()
        self.setAttribute(Qt.WA_StyledBackground, True)

        self.sheet = QFrame(self)
        self.sheet.setObjectName("BottomSheet")
        layout = QVBoxLayout(self.sheet)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(9)

        header = QHBoxLayout()
        self.title = QLabel("Ошибка")
        self.title.setObjectName("SheetTitle")
        header.addWidget(self.title, 1)
        self.close_button = QPushButton("Закрыть")
        self.close_button.setObjectName("TextButton")
        self.close_button.clicked.connect(self.close_sheet)
        header.addWidget(self.close_button)
        layout.addLayout(header)

        self.message = QLabel()
        self.message.setObjectName("SheetMessage")
        self.message.setWordWrap(True)
        layout.addWidget(self.message)

        self._anim = QPropertyAnimation(self.sheet, b"pos", self)
        self._anim.setDuration(180)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)

    def show_error(self, title: str, message: str) -> None:
        parent = self.parentWidget()
        if not parent:
            return
        self.setGeometry(parent.rect())
        self.title.setText(title)
        self.message.setText(message)
        width = min(620, max(520, parent.width() - 96))
        self.sheet.setFixedWidth(width)
        self.sheet.adjustSize()
        height = max(118, self.sheet.sizeHint().height())
        self.sheet.setFixedHeight(height)
        x = (parent.width() - width) // 2
        target_y = parent.height() - height - 22
        self.sheet.move(x, parent.height() + 8)
        self.raise_()
        self.show()
        self.sheet.show()
        self._anim.stop()
        self._anim.setStartValue(QPoint(x, parent.height() + 8))
        self._anim.setEndValue(QPoint(x, target_y))
        self._anim.start()

    def close_sheet(self) -> None:
        if not self.isVisible():
            return
        parent = self.parentWidget()
        if not parent:
            self.hide()
            return
        x = self.sheet.x()
        self._anim.stop()
        self._anim.setStartValue(self.sheet.pos())
        self._anim.setEndValue(QPoint(x, parent.height() + 8))
        try:
            self._anim.finished.disconnect()
        except Exception:
            pass
        self._anim.finished.connect(self._finish_close)
        self._anim.start()

    def _finish_close(self) -> None:
        self.hide()
        try:
            self._anim.finished.disconnect(self._finish_close)
        except Exception:
            pass
        self.closed.emit()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if not self.sheet.isVisible():
            return
        width = self.sheet.width()
        x = (self.width() - width) // 2
        y = self.height() - self.sheet.height() - 22
        self.sheet.move(x, y)
