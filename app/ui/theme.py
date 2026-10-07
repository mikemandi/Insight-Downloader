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
    overlay: str
    divider: str


DARK = Theme(
    name="dark",
    bg="#090D12",
    surface="#0E141D",
    surface_alt="#121A25",
    field="#0B1119",
    border="rgba(255,255,255,0.075)",
    border_hover="rgba(255,255,255,0.16)",
    text="#F4F7FB",
    text_soft="#B9C3D1",
    muted="#778397",
    accent="#8C7CFF",
    accent_hover="#9C8FFF",
    accent_2="#A85CF7",
    accent_text="#FFFFFF",
    success="#48D7A0",
    warning="#F3BF62",
    danger="#FF6B7A",
    progress="#1A222D",
    selection="#1A2330",
    overlay="#0D131C",
    divider="rgba(255,255,255,0.055)",
)

LIGHT = Theme(
    name="light",
    bg="#F6F7F9",
    surface="#FFFFFF",
    surface_alt="#F3F5F8",
    field="#F8F9FB",
    border="rgba(20,30,45,0.10)",
    border_hover="rgba(20,30,45,0.22)",
    text="#111722",
    text_soft="#465266",
    muted="#7B879A",
    accent="#746BFF",
    accent_hover="#655BFA",
    accent_2="#A655F2",
    accent_text="#FFFFFF",
    success="#168A5A",
    warning="#9B6C19",
    danger="#CF5162",
    progress="#E8EBF0",
    selection="#EEF0F6",
    overlay="#FFFFFF",
    divider="rgba(20,30,45,0.075)",
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
    font-family: 'Segoe UI Variable', 'Segoe UI';
    font-size: 13px;
    background: transparent;
}}

QMainWindow, QWidget#Root {{ background: {t.bg}; }}

QLabel#Brand {{ font-size: 17px; font-weight: 650; color: {t.text}; }}
QLabel#PageTitle, QLabel#ShellTitle, QLabel#DialogTitle {{ font-size: 22px; font-weight: 650; color: {t.text}; }}
QLabel#SectionTitle {{ font-size: 15px; font-weight: 600; color: {t.text}; }}
QLabel#MediaTitle {{ font-size: 16px; font-weight: 600; color: {t.text}; }}
QLabel#Strong {{ font-size: 13px; font-weight: 600; color: {t.text}; }}
QLabel#Muted {{ color: {t.muted}; }}
QLabel#Soft {{ color: {t.text_soft}; }}
QLabel#Tiny {{ font-size: 11px; color: {t.muted}; }}
QLabel#FieldLabel {{ font-size: 12px; font-weight: 550; color: {t.text_soft}; }}
QLabel#SuccessText {{ color: {t.success}; font-weight: 600; }}
QLabel#WarningText {{ color: {t.warning}; font-weight: 600; }}
QLabel#DangerText {{ color: {t.danger}; font-weight: 600; }}
QLabel#AboutTitle {{ font-size: 15px; font-weight: 650; color: {t.text}; }}
QLabel#AboutMeta {{ font-size: 12px; color: {t.muted}; }}
QLabel#SheetTitle {{ font-size: 15px; font-weight: 650; color: {t.text}; }}
QLabel#SheetMessage {{ color: {t.text_soft}; line-height: 1.35; }}

QFrame#HeaderDivider,
QFrame#PaneDivider,
QFrame#SettingsDivider {{
    background: {t.divider};
    border: none;
}}

QFrame#PreviewSurface {{
    background: {t.surface};
    border: none;
    border-radius: 12px;
}}

QFrame#InfoStrip {{
    background: {t.surface_alt};
    border: none;
    border-radius: 10px;
}}

QFrame#DownloadState {{
    background: transparent;
    border: none;
}}

QFrame#SuccessState {{
    background: {t.surface_alt};
    border: none;
    border-radius: 10px;
}}

QFrame#SettingsPanel {{
    background: {t.surface};
    border: 1px solid {t.border};
    border-radius: 14px;
}}

QFrame#DiagnosticsPanel {{
    background: {t.surface_alt};
    border: none;
    border-radius: 10px;
}}
QLabel#StatusDotReady, QLabel#StatusReady {{ color: {t.success}; }}
QLabel#StatusDotMissing, QLabel#StatusMissing {{ color: {t.warning}; }}
QLabel#StatusReady, QLabel#StatusMissing {{ font-size: 12px; font-weight: 600; }}

QLineEdit {{
    min-height: 42px;
    background: {t.field};
    color: {t.text};
    border: 1px solid {t.border};
    border-radius: 10px;
    padding: 0 13px;
    selection-background-color: {t.selection};
}}
QLineEdit:hover {{ border-color: {t.border_hover}; }}
QLineEdit:focus {{ border-color: {t.accent}; }}
QLineEdit:disabled {{ color: {t.muted}; background: {t.surface_alt}; }}

QComboBox {{
    min-height: 40px;
    background: {t.field};
    color: {t.text};
    border: 1px solid {t.border};
    border-radius: 10px;
    padding: 0 34px 0 12px;
}}
QComboBox:hover {{ border-color: {t.border_hover}; }}
QComboBox:focus {{ border-color: {t.accent}; }}
QComboBox:disabled {{ color: {t.muted}; background: {t.surface_alt}; }}
QComboBox::drop-down {{ border: none; width: 30px; }}
QComboBox::down-arrow {{ image: none; }}
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
    min-height: 38px;
    padding: 0 13px;
    border-radius: 10px;
    background: {t.surface_alt};
    color: {t.text};
    border: 1px solid {t.border};
    font-weight: 600;
}}
QPushButton:hover {{ background: {t.selection}; border-color: {t.border_hover}; }}
QPushButton:pressed {{ background: {t.surface_alt}; border-color: {t.accent}; }}
QPushButton:disabled {{ color: {t.muted}; border-color: {t.border}; background: {t.surface_alt}; }}

QPushButton#Primary {{
    min-height: 42px;
    color: {t.accent_text};
    border: none;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {t.accent}, stop:1 {t.accent_2});
}}
QPushButton#Primary:hover {{
    border: none;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {t.accent_hover}, stop:1 {t.accent_2});
}}
QPushButton#Primary:pressed {{ border: none; background: {t.accent}; }}
QPushButton#Primary:disabled {{
    border: 1px solid {t.border};
    color: {t.muted};
    background: {t.field};
}}

QPushButton#Secondary {{
    min-height: 40px;
    background: transparent;
    border: 1px solid {t.border};
    color: {t.text_soft};
}}
QPushButton#Secondary:hover {{
    background: {t.selection};
    border-color: {t.border_hover};
    color: {t.text};
}}
QPushButton#Secondary:disabled {{
    background: {t.field};
    border: 1px solid {t.border};
    color: {t.muted};
}}
QPushButton#GhostButton {{
    min-height: 34px;
    background: transparent;
    border: none;
    color: {t.text_soft};
    padding: 0 8px;
}}
QPushButton#GhostButton:hover {{ background: {t.selection}; color: {t.text}; border: none; }}
QPushButton#TextButton {{
    min-height: 28px;
    background: transparent;
    border: none;
    color: {t.text_soft};
    padding: 0 4px;
}}
QPushButton#TextButton:hover {{ color: {t.text}; background: transparent; border: none; }}
QPushButton#LinkButton {{
    min-height: 28px;
    background: transparent;
    border: none;
    color: {t.text_soft};
    padding: 0 2px;
    font-weight: 500;
}}
QPushButton#LinkButton:hover {{ color: {t.accent_2}; background: transparent; border: none; }}
QPushButton#LinkButton:pressed {{ color: {t.accent}; background: transparent; border: none; }}
QPushButton#DisclosureButton {{
    min-height: 30px;
    background: transparent;
    border: none;
    color: {t.text_soft};
    padding: 0 2px;
    font-weight: 600;
}}
QPushButton#DisclosureButton:hover {{ color: {t.text}; background: transparent; border: none; }}
QPushButton#Danger {{ color: {t.danger}; background: transparent; border: none; }}

QPushButton#IconButton {{
    min-height: 36px; max-height: 36px;
    min-width: 36px; max-width: 36px;
    padding: 0;
    border-radius: 10px;
    background: transparent;
    border: none;
    color: {t.muted};
}}
QPushButton#IconButton:hover {{ background: {t.selection}; color: {t.text}; border: none; }}
QPushButton#IconButton:pressed {{ background: {t.surface_alt}; border: none; }}

QPushButton#UpdateButton {{
    min-height: 32px;
    padding: 0 11px;
    border-radius: 9px;
    background: {t.selection};
    border-color: {t.border_hover};
    color: {t.text};
}}

QPushButton#SegmentButton {{
    min-height: 36px;
    border-radius: 9px;
    background: transparent;
    color: {t.muted};
    border: none;
}}
QPushButton#SegmentButton:checked {{
    color: {t.text};
    background: {t.selection};
    border: 1px solid {t.border_hover};
}}
QPushButton#SegmentButton:hover {{ color: {t.text}; background: {t.selection}; border: none; }}
QPushButton#SegmentButton:checked:hover {{ border: 1px solid {t.border_hover}; }}

QLabel#Preview {{
    color: {t.muted};
    background: {t.surface};
    border: none;
    border-radius: 12px;
}}


QCheckBox::indicator {{
    width: 36px;
    height: 20px;
    border-radius: 10px;
    background: {t.progress};
    border: 1px solid {t.border};
}}
QCheckBox::indicator:checked {{
    background: {t.accent};
    border-color: {t.accent};
}}

QProgressBar {{
    min-height: 6px; max-height: 6px;
    border: none;
    border-radius: 3px;
    background: {t.progress};
}}
QProgressBar::chunk {{
    border-radius: 3px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {t.accent}, stop:1 {t.accent_2});
}}

QLabel#Percent {{
    color: {t.text_soft};
    background: transparent;
    border: none;
    font-size: 12px;
    font-weight: 600;
}}

QLabel#Toast {{
    background: {t.overlay};
    color: {t.text};
    border: 1px solid {t.border_hover};
    border-radius: 11px;
    padding: 0 14px;
    font-weight: 600;
}}

QWidget#BottomSheetOverlay {{ background: rgba(0,0,0,0.42); }}
QFrame#BottomSheet {{
    background: {t.overlay};
    border: 1px solid {t.border_hover};
    border-radius: 14px;
}}

QDialog {{ background: {t.bg}; }}
QTextBrowser#ReleaseNotes {{
    background: {t.surface};
    border: 1px solid {t.border};
    border-radius: 10px;
    padding: 8px;
}}
QToolTip {{
    color: {t.text};
    background: {t.overlay};
    border: 1px solid {t.border_hover};
    padding: 6px;
}}
"""
