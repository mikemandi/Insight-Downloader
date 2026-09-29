from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication, QPalette
from PySide6.QtWidgets import QApplication


@dataclass(frozen=True, slots=True)
class Theme:
    name: str
    bg: str
    surface: str
    surface_alt: str
    field: str
    border: str
    border_hover: str
    text: str
    text_soft: str
    muted: str
    accent: str
    accent_hover: str
    accent_2: str
    accent_text: str
    success: str
    warning: str
    danger: str
    progress: str
    selection: str


DARK = Theme(
    name="dark",
    bg="#070B12",
    surface="#0E151F",
    surface_alt="#111A27",
    field="#0A111B",
    border="#1C293B",
    border_hover="#334766",
    text="#F4F7FB",
    text_soft="#C6D0DF",
    muted="#8290A5",
    accent="#90ABFF",
    accent_hover="#A7BCFF",
    accent_2="#A66DFF",
    accent_text="#08111F",
    success="#65D6A1",
    warning="#F4C66D",
    danger="#FF899B",
    progress="#172336",
    selection="#243756",
)

LIGHT = Theme(
    name="light",
    bg="#F3F6FB",
    surface="#FFFFFF",
    surface_alt="#F8FAFD",
    field="#F7F9FD",
    border="#DEE5F0",
    border_hover="#B7C5DA",
    text="#0D1421",
    text_soft="#34425A",
    muted="#718097",
    accent="#6E88FF",
    accent_hover="#5F7CFA",
    accent_2="#9B62F5",
    accent_text="#FFFFFF",
    success="#178B5B",
    warning="#A97922",
    danger="#C75269",
    progress="#E7ECF5",
    selection="#E6ECFF",
)


def system_theme_name() -> str:
    app = QApplication.instance()
    if app is None:
        return "dark"

    try:
        scheme = QGuiApplication.styleHints().colorScheme()
        if scheme == Qt.ColorScheme.Dark:
            return "dark"
        if scheme == Qt.ColorScheme.Light:
            return "light"
    except Exception:
        pass

    color = app.palette().color(QPalette.Window)
    return "dark" if color.lightness() < 128 else "light"


def resolve_theme(mode: str) -> Theme:
    selected = system_theme_name() if mode == "system" else mode
    return DARK if selected == "dark" else LIGHT


def stylesheet(t: Theme) -> str:
    return f"""
QWidget {{
    color: {t.text};
    font-family: 'Segoe UI';
    font-size: 13px;
    background: transparent;
}}

QMainWindow, QWidget#Root {{
    background: {t.bg};
}}

QFrame#TopNav,
QFrame#AppShell,
QFrame#MediaPane,
QFrame#ControlPane,
QFrame#StatusPanel,
QFrame#CompactField {{
    background: {t.surface};
    border: 1px solid {t.border};
}}

QFrame#TopNav {{ border-radius: 18px; }}
QFrame#AppShell {{ border-radius: 22px; }}
QFrame#MediaPane,
QFrame#ControlPane {{ border-radius: 18px; }}
QFrame#StatusPanel,
QFrame#CompactField {{
    background: {t.field};
    border-radius: 14px;
}}

QLabel#Brand {{
    color: {t.text};
    font-size: 18px;
    font-weight: 800;
}}
QLabel#Eyebrow {{
    color: {t.muted};
    font-size: 10px;
    font-weight: 700;
}}
QLabel#ShellTitle {{
    color: {t.text};
    font-size: 20px;
    font-weight: 800;
}}
QLabel#SectionLabel {{
    color: {t.muted};
    font-size: 11px;
    font-weight: 700;
}}
QLabel#MediaTitle {{
    color: {t.text};
    font-size: 17px;
    font-weight: 800;
}}
QLabel#Strong {{
    color: {t.text};
    font-size: 14px;
    font-weight: 700;
}}
QLabel#Muted {{ color: {t.muted}; }}
QLabel#Soft {{ color: {t.text_soft}; }}
QLabel#Footer {{ color: {t.muted}; font-size: 11px; }}
QLabel#Percent {{
    color: {t.text};
    background: {t.surface_alt};
    border: 1px solid {t.border};
    border-radius: 12px;
    padding: 5px 9px;
    font-weight: 800;
}}
QLabel#RuntimeOk {{ color: {t.success}; font-weight: 700; }}
QLabel#RuntimeWarn {{ color: {t.warning}; font-weight: 700; }}
QLabel#Preview {{
    color: {t.muted};
    background: {t.field};
    border: 1px solid {t.border};
    border-radius: 16px;
}}

QLineEdit {{
    min-height: 44px;
    background: {t.field};
    color: {t.text};
    border: 1px solid {t.border};
    border-radius: 14px;
    padding: 0 14px;
    selection-background-color: {t.selection};
}}
QLineEdit:hover {{ border-color: {t.border_hover}; }}
QLineEdit:focus {{ border-color: {t.accent}; }}

QComboBox {{
    min-height: 40px;
    background: {t.field};
    color: {t.text};
    border: 1px solid {t.border};
    border-radius: 12px;
    padding: 0 12px;
}}
QComboBox:hover {{ border-color: {t.border_hover}; }}
QComboBox:focus {{ border-color: {t.accent}; }}
QComboBox::drop-down {{ border: none; width: 28px; }}
QComboBox QAbstractItemView {{
    background: {t.surface};
    color: {t.text};
    border: 1px solid {t.border_hover};
    selection-background-color: {t.selection};
    selection-color: {t.text};
    outline: 0;
    padding: 5px;
}}

QPushButton {{
    min-height: 40px;
    padding: 0 14px;
    border-radius: 12px;
    background: {t.surface_alt};
    color: {t.text};
    border: 1px solid {t.border};
    font-weight: 700;
}}
QPushButton:hover {{
    background: {t.field};
    border-color: {t.border_hover};
}}
QPushButton:pressed {{
    background: {t.selection};
    border-color: {t.accent};
}}
QPushButton:disabled {{
    color: {t.muted};
    border-color: {t.border};
    background: {t.surface_alt};
}}
QPushButton#Primary {{
    min-height: 46px;
    color: {t.accent_text};
    border: none;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {t.accent}, stop:1 {t.accent_2});
}}
QPushButton#Primary:hover {{
    border: none;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {t.accent_hover}, stop:1 {t.accent_2});
}}
QPushButton#Primary:pressed {{
    border: none;
    background: {t.accent};
}}
QPushButton#Danger {{ color: {t.danger}; }}
QPushButton#UpdateButton {{
    min-height: 32px;
    padding: 0 11px;
    border-radius: 10px;
    color: {t.text};
    background: {t.selection};
    border: 1px solid {t.accent};
}}
QPushButton#UpdateButton:hover {{
    background: {t.surface_alt};
    border-color: {t.accent_hover};
}}
QLabel#DialogTitle {{
    color: {t.text};
    font-size: 20px;
    font-weight: 800;
}}
QTextBrowser#ReleaseNotes {{
    background: {t.field};
    color: {t.text_soft};
    border: 1px solid {t.border};
    border-radius: 12px;
    padding: 10px;
}}
QDialog {{
    background: {t.surface};
}}
QPushButton#SmallButton {{
    min-height: 34px;
    padding: 0 11px;
    border-radius: 10px;
}}

QPushButton#SegmentButton {{
    min-height: 38px;
    border-radius: 10px;
    background: {t.field};
    border: 1px solid {t.border};
    color: {t.muted};
}}
QPushButton#SegmentButton:first {{ border-top-left-radius: 12px; border-bottom-left-radius: 12px; }}
QPushButton#SegmentButton:last {{ border-top-right-radius: 12px; border-bottom-right-radius: 12px; }}
QPushButton#SegmentButton:hover {{ color: {t.text}; background: {t.surface_alt}; }}
QPushButton#SegmentButton:checked {{
    color: {t.text};
    background: {t.selection};
    border-color: {t.accent};
}}

QProgressBar {{
    min-height: 10px;
    max-height: 10px;
    border: none;
    border-radius: 5px;
    background: {t.progress};
}}
QProgressBar::chunk {{
    border-radius: 5px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {t.accent}, stop:1 {t.accent_2});
}}

QToolTip {{
    color: {t.text};
    background: {t.surface};
    border: 1px solid {t.border_hover};
    padding: 5px 7px;
}}
QMessageBox {{ background: {t.surface}; }}
QMessageBox QLabel {{ color: {t.text}; }}
"""
