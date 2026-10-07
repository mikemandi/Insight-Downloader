from __future__ import annotations

import ctypes
import os
import sys

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from app.config import APP_ID, APP_NAME, PUBLISHER
from app.core.runtime import resource_path
from app.ui.main_window import MainWindow


def _set_windows_app_id() -> None:
    if os.name != "nt":
        return
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
    except Exception:
        pass


def _apply_native_windows_icon(window: MainWindow, icon_path: str) -> None:
    """Force both small/titlebar and large/taskbar icons on Windows.

    Qt normally does this itself, but Python development launches and old taskbar
    cache entries can otherwise keep showing the previous Insight glyph.
    """
    if os.name != "nt":
        return
    try:
        user32 = ctypes.windll.user32
        IMAGE_ICON = 1
        LR_LOADFROMFILE = 0x0010
        WM_SETICON = 0x0080
        ICON_SMALL = 0
        ICON_BIG = 1
        hwnd = int(window.winId())

        small = user32.LoadImageW(None, icon_path, IMAGE_ICON, 16, 16, LR_LOADFROMFILE)
        big = user32.LoadImageW(None, icon_path, IMAGE_ICON, 32, 32, LR_LOADFROMFILE)
        if small:
            user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, small)
        if big:
            user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, big)
    except Exception:
        pass


def main() -> int:
    _set_windows_app_id()
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    app.setOrganizationName(PUBLISHER)

    icon_path = resource_path("app", "assets", "insight.ico")
    if icon_path.exists():
        icon = QIcon(str(icon_path))
        app.setWindowIcon(icon)
    else:
        icon = QIcon()

    window = MainWindow()
    if not icon.isNull():
        window.setWindowIcon(icon)
    window.show()

    if icon_path.exists():
        # Qt/Windows can refresh the native frame after the first show. Apply the
        # icon more than once so development launches do not fall back to an old
        # cached/Python taskbar glyph. Installed builds also embed the same ICO.
        QTimer.singleShot(0, lambda: _apply_native_windows_icon(window, str(icon_path)))
        QTimer.singleShot(250, lambda: _apply_native_windows_icon(window, str(icon_path)))
        QTimer.singleShot(900, lambda: _apply_native_windows_icon(window, str(icon_path)))

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
