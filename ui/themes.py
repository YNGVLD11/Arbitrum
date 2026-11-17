import os
import sys
import math
import random
from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import (
    QColor, QLinearGradient, QRadialGradient, QPainter,
    QPainterPath, QBrush, QPixmap, QPen, QIcon
)

THEME_LIGHT = "light"
THEME_FEMININE = "feminine"
THEME_CAPPUCCINO = "cappuccino"
THEME_LAVENDER = "lavender"

def get_app_icon() -> QIcon:
    """
    Returns the application icon, supporting both source and frozen PyInstaller bundles.
    """
    if getattr(sys, "frozen", False):
        base_dir = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    else:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    ico_path = os.path.join(base_dir, "assets", "app_icon.ico")
    png_path = os.path.join(base_dir, "assets", "app_icon.png")

    icon = QIcon()
    if os.path.exists(ico_path):
        icon.addFile(ico_path)
    if os.path.exists(png_path):
        icon.addFile(png_path)
    return icon

# Directory for indicator icons (radio and checkbox)
ICONS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "icons"
).replace("\\", "/")
os.makedirs(ICONS_DIR, exist_ok=True)


def ensure_indicator_icons():
    """
    Guarantees that clean, modern high-DPI indicator icons exist on disk
    for radio buttons and checkboxes in both themes.
    """
    needed_files = [
        "radio_unchecked.png", "radio_checked_blue.png", "radio_checked_pink.png",
        "radio_checked_cappuccino.png", "radio_checked_lavender.png",
        "checkbox_unchecked.png", "checkbox_checked_blue.png", "checkbox_checked_pink.png",
        "checkbox_checked_cappuccino.png", "checkbox_checked_lavender.png",
        "arrow_down_dark.png"
    ]
    if all(os.path.exists(os.path.join(ICONS_DIR, f)) for f in needed_files):
        return

    def make_radio(filename: str, color_hex: str):
        pm = QPixmap(20, 20)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setPen(QPen(QColor(color_hex), 2))
        p.setBrush(QBrush(QColor("#FFFFFF")))
        p.drawEllipse(2, 2, 16, 16)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(color_hex)))
        p.drawEllipse(5, 5, 10, 10)
        p.end()
        pm.save(os.path.join(ICONS_DIR, filename))

    def make_checkbox(filename: str, color_hex: str):
        pm = QPixmap(20, 20)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setPen(QPen(QColor(color_hex), 1))
        p.setBrush(QBrush(QColor(color_hex)))
        p.drawRoundedRect(2, 2, 16, 16, 4, 4)
        pen = QPen(QColor("#FFFFFF"), 2)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        p.setPen(pen)
        path = QPainterPath()
        path.moveTo(5.5, 10)
        path.lineTo(8.5, 13.5)
        path.lineTo(14.5, 6.5)
        p.drawPath(path)
        p.end()
        pm.save(os.path.join(ICONS_DIR, filename))

    make_radio("radio_checked_blue.png", "#2563EB")
    make_radio("radio_checked_pink.png", "#FF4D6D")
    make_radio("radio_checked_cappuccino.png", "#8C5E3C")
    make_radio("radio_checked_lavender.png", "#7C3AED")

    make_checkbox("checkbox_checked_blue.png", "#2563EB")
    make_checkbox("checkbox_checked_pink.png", "#FF4D6D")
    make_checkbox("checkbox_checked_cappuccino.png", "#8C5E3C")
    make_checkbox("checkbox_checked_lavender.png", "#7C3AED")

    # Arrow Down Dark
    pm = QPixmap(16, 16)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)
    pen = QPen(QColor("#475569"), 2)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    p.setPen(pen)
    path = QPainterPath()
    path.moveTo(4, 6)
    path.lineTo(8, 10)
    path.lineTo(12, 6)
    p.drawPath(path)
    p.end()
    pm.save(os.path.join(ICONS_DIR, "arrow_down_dark.png"))

    # 1. Radio Unchecked (Circle outline)
    pm = QPixmap(20, 20)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)
    p.setPen(QPen(QColor("#94A3B8"), 2))
    p.setBrush(QBrush(QColor("#FFFFFF")))
    p.drawEllipse(2, 2, 16, 16)
    p.end()
    pm.save(os.path.join(ICONS_DIR, "radio_unchecked.png"))

    # 2. Radio Checked Light (Blue)
    pm = QPixmap(20, 20)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)
    p.setPen(QPen(QColor("#2563EB"), 2))
    p.setBrush(QBrush(QColor("#FFFFFF")))
    p.drawEllipse(2, 2, 16, 16)
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(QColor("#2563EB")))
    p.drawEllipse(5, 5, 10, 10)
    p.end()
    pm.save(os.path.join(ICONS_DIR, "radio_checked_blue.png"))

    # 3. Radio Checked Feminine (Pink)
    pm = QPixmap(20, 20)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)
    p.setPen(QPen(QColor("#FF4D6D"), 2))
    p.setBrush(QBrush(QColor("#FFFFFF")))
    p.drawEllipse(2, 2, 16, 16)
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(QColor("#FF4D6D")))
    p.drawEllipse(5, 5, 10, 10)
    p.end()
    pm.save(os.path.join(ICONS_DIR, "radio_checked_pink.png"))

    # 4. Checkbox Unchecked (Rounded square)
    pm = QPixmap(20, 20)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)
    p.setPen(QPen(QColor("#94A3B8"), 2))
    p.setBrush(QBrush(QColor("#FFFFFF")))
    p.drawRoundedRect(2, 2, 16, 16, 4, 4)
    p.end()
    pm.save(os.path.join(ICONS_DIR, "checkbox_unchecked.png"))

    # 5. Checkbox Checked Light (Blue)
    pm = QPixmap(20, 20)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)
    p.setPen(QPen(QColor("#2563EB"), 1))
    p.setBrush(QBrush(QColor("#2563EB")))
    p.drawRoundedRect(2, 2, 16, 16, 4, 4)
    pen = QPen(QColor("#FFFFFF"), 2)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    p.setPen(pen)
    path = QPainterPath()
    path.moveTo(5.5, 10)
    path.lineTo(8.5, 13.5)
    path.lineTo(14.5, 6.5)
    p.drawPath(path)
    p.end()
    pm.save(os.path.join(ICONS_DIR, "checkbox_checked_blue.png"))

    # 6. Checkbox Checked Feminine (Pink)
    pm = QPixmap(20, 20)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)
    p.setPen(QPen(QColor("#FF4D6D"), 1))
    p.setBrush(QBrush(QColor("#FF4D6D")))
    p.drawRoundedRect(2, 2, 16, 16, 4, 4)
    pen = QPen(QColor("#FFFFFF"), 2)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    p.setPen(pen)
    path = QPainterPath()
    path.moveTo(5.5, 10)
    path.lineTo(8.5, 13.5)
    path.lineTo(14.5, 6.5)
    p.drawPath(path)
    p.end()
    pm.save(os.path.join(ICONS_DIR, "checkbox_checked_pink.png"))


# Ensure icons exist immediately
try:
    ensure_indicator_icons()
except Exception:
    pass


# ==============================================================================
# QSS Stylesheets
# ==============================================================================

LIGHT_QSS = f"""
QMainWindow {{
    background: transparent;
    color: #0F172A;
    font-family: "Inter", "Segoe UI", Arial, sans-serif;
    font-size: 13px;
}}

QDialog {{
    background-color: #F0F9FF;
    color: #0F172A;
    font-family: "Inter", "Segoe UI", Arial, sans-serif;
    font-size: 13px;
}}

QWidget {{
    font-family: "Inter", "Segoe UI", Arial, sans-serif;
    font-size: 13px;
    color: #0F172A;
}}

/* Card Containers */
QFrame#cardFrame {{
    background-color: #FFFFFF;
    border: 1px solid #BAE6FD;
    border-radius: 12px;
}}

/* Group Boxes in Settings Dialog */
QGroupBox {{
    background-color: #FFFFFF;
    border: 1px solid #BAE6FD;
    border-radius: 10px;
    margin-top: 16px;
    padding-top: 0px;
    padding-bottom: 0px;
    padding-left: 0px;
    padding-right: 0px;
    font-weight: 600;
    color: #0369A1;
    font-size: 13px;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 14px;
    padding: 0 6px;
    background-color: #F0F9FF;
    color: #0369A1;
}}

/* Splitter - comfortable gap with centered thin divider line */
QSplitter::handle:horizontal {{
    background-color: #94A3B8;
    margin: 6px 7px;
    border-radius: 1px;
}}

QSplitter::handle:horizontal:hover {{
    background-color: #0284C7;
}}

/* Tooltips */
QToolTip {{
    background-color: #1E293B;
    color: #F8FAFC;
    border: 1px solid #475569;
    border-radius: 6px;
    padding: 5px 9px;
    font-size: 12px;
    font-weight: 500;
}}

/* Gear Settings Button (Big & Prominent) */
QPushButton#settingsButton {{
    background-color: rgba(255, 255, 255, 0.95);
    border: 1px solid #BAE6FD;
    border-radius: 12px;
    padding: 0px;
    font-size: 24px;
    text-align: center;
}}

QPushButton#settingsButton:hover {{
    background-color: #F0F9FF;
    border-color: #0284C7;
}}

/* Standard Buttons */
QPushButton {{
    background-color: #FFFFFF;
    color: #0F172A;
    border: 1px solid #CBD5E1;
    border-radius: 8px;
    padding: 6px 16px;
    font-weight: 600;
    min-height: 24px;
    font-size: 13px;
}}

QPushButton:hover {{
    background-color: #F1F5F9;
    border-color: #64748B;
}}

QPushButton:pressed {{
    background-color: #E2E8F0;
}}

QPushButton:disabled {{
    background-color: #F8FAFC;
    color: #94A3B8;
    border-color: #E2E8F0;
}}

/* Primary Action Button (Dialogs & Build) */
QPushButton#primaryButton {{
    background-color: #2563EB;
    color: #FFFFFF;
    border: 1px solid #1D4ED8;
    border-radius: 8px;
    padding: 6px 20px;
    font-size: 13px;
    font-weight: 600;
    min-height: 24px;
}}

QPushButton#primaryButton:hover {{
    background-color: #1D4ED8;
}}

QPushButton#primaryButton:pressed {{
    background-color: #1E40AF;
}}

/* Big Main Screen Build Button */
QPushButton#mainBuildButton {{
    background-color: #2563EB;
    color: #FFFFFF;
    border: 1px solid #1D4ED8;
    border-radius: 10px;
    padding: 10px 42px;
    font-size: 15px;
    font-weight: 700;
    min-height: 28px;
}}

QPushButton#mainBuildButton:hover {{
    background-color: #1D4ED8;
}}

QPushButton#mainBuildButton:pressed {{
    background-color: #1E40AF;
}}

QPushButton#mainBuildButton:disabled {{
    background-color: #94A3B8;
    border-color: #94A3B8;
    color: #F1F5F9;
}}

/* Danger / Clear Button */
QPushButton#dangerButton {{
    background-color: #FFF1F2;
    color: #E11D48;
    border: 1px solid #FECDD3;
    padding: 6px 14px;
}}

QPushButton#dangerButton:hover {{
    background-color: #FFE4E6;
    border-color: #FDA4AF;
}}

/* Compact Tool Icon Buttons (Up, Down, Gear) - Explicit 0 padding */
QPushButton#toolIconBtn, QPushButton#iconButton {{
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 8px;
    padding: 0px;
    font-size: 13px;
    font-weight: bold;
    text-align: center;
}}

QPushButton#toolIconBtn:hover, QPushButton#iconButton:hover {{
    background-color: #F1F5F9;
    border-color: #64748B;
}}

/* Preview Navigation Buttons (◀, ▶, −, +) */
QPushButton#previewNavBtn {{
    background-color: #FFFFFF;
    color: #0F172A;
    border: 1px solid #CBD5E1;
    border-radius: 8px;
    padding: 0px;
    font-size: 14px;
    font-weight: bold;
    text-align: center;
    min-width: 36px;
    min-height: 34px;
}}

QPushButton#previewNavBtn:hover {{
    background-color: #F1F5F9;
    border-color: #64748B;
}}

/* Radio Buttons */
QRadioButton {{
    color: #0F172A;
    font-size: 13px;
    font-weight: 500;
    spacing: 10px;
    background: transparent;
    padding: 3px 0px;
}}

QRadioButton::indicator {{
    width: 20px;
    height: 20px;
    background: transparent;
}}

QRadioButton::indicator:unchecked {{
    image: url("{ICONS_DIR}/radio_unchecked.png");
}}

QRadioButton::indicator:checked {{
    image: url("{ICONS_DIR}/radio_checked_blue.png");
}}

/* Checkboxes */
QCheckBox {{
    color: #0F172A;
    font-size: 13px;
    font-weight: 500;
    spacing: 10px;
    background: transparent;
    padding: 3px 0px;
}}

QCheckBox::indicator {{
    width: 20px;
    height: 20px;
    background: transparent;
}}

QCheckBox::indicator:unchecked {{
    image: url("{ICONS_DIR}/checkbox_unchecked.png");
}}

QCheckBox::indicator:checked {{
    image: url("{ICONS_DIR}/checkbox_checked_blue.png");
}}

/* Lists */
QListWidget {{
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 10px;
    outline: none;
    padding: 4px;
}}

QListWidget::item {{
    background: transparent;
    border: none;
    padding: 0px;
    margin: 2px 0px;
}}

QListWidget::item:selected {{
    background: transparent;
    border: none;
}}

/* Scroll Area & Preview Viewport - ALWAYS WHITE */
QScrollArea {{
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 8px;
}}

QScrollArea > QWidget > QWidget {{
    background-color: #FFFFFF;
}}

/* Scrollbars */
QScrollBar:vertical {{
    border: none;
    background: #F1F5F9;
    width: 8px;
    border-radius: 4px;
    margin: 2px;
}}

QScrollBar::handle:vertical {{
    background: #94A3B8;
    min-height: 24px;
    border-radius: 4px;
}}

QScrollBar::handle:vertical:hover {{
    background: #64748B;
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QScrollBar:horizontal {{
    border: none;
    background: #F1F5F9;
    height: 8px;
    border-radius: 4px;
    margin: 2px;
}}

QScrollBar::handle:horizontal {{
    background: #94A3B8;
    min-width: 24px;
    border-radius: 4px;
}}

QScrollBar::handle:horizontal:hover {{
    background: #64748B;
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}

/* Line Edit / Input */
QLineEdit,
QTextEdit,
QPlainTextEdit {{
    background-color: #FFFFFF !important;
    background: #FFFFFF !important;
    border: 1px solid #CBD5E1;
    border-radius: 8px;
    padding: 6px 10px;
    color: #0F172A !important;
    font-size: 13px;
    min-height: 24px;
}}

QLineEdit:focus,
QTextEdit:focus,
QPlainTextEdit:focus {{
    border: 1px solid #2563EB;
}}

/* Typography */
QLabel#headerTitle {{
    font-size: 15px;
    font-weight: 700;
    color: #0F172A;
}}

QLabel#subTitle {{
    font-size: 12px;
    color: #64748B;
}}

QLabel#successHighlight {{
    color: #0369A1;
    font-weight: 600;
    font-size: 12px;
}}

/* Sidebar Styles (Light) */
QFrame#sidebarFrame {{
    background-color: rgba(255, 255, 255, 0.92);
    border: 1px solid #BAE6FD;
    border-radius: 12px;
}}

QLabel#sidebarTitle {{
    font-size: 16px;
    font-weight: 700;
    color: #0369A1;
}}

QLabel#sidebarSubtitle {{
    font-size: 10px;
    font-weight: 500;
    color: #64748B;
}}

QFrame#sidebarDivider {{
    color: #BAE6FD;
    background-color: #BAE6FD;
    max-height: 1px;
}}

QPushButton#sidebarNavButton {{
    background-color: transparent;
    color: #334155;
    border: 1px solid transparent;
    border-radius: 8px;
    padding: 8px 10px;
    font-size: 12px;
    font-weight: 600;
    text-align: left;
}}

QPushButton#sidebarNavButton:hover {{
    background-color: #F0F9FF;
    color: #0369A1;
    border-color: #BAE6FD;
}}

QPushButton#sidebarNavButton[active="true"] {{
    background-color: #2563EB;
    color: #FFFFFF;
    border: 1px solid #1D4ED8;
    font-weight: 700;
}}

QPushButton#sidebarSettingsButton {{
    background-color: #FFFFFF;
    color: #334155;
    border: 1px solid #BAE6FD;
    border-radius: 8px;
    padding: 6px 14px;
    font-size: 12px;
    font-weight: 600;
    text-align: left;
}}

QPushButton#sidebarSettingsButton:hover {{
    background-color: #F0F9FF;
    color: #0369A1;
    border-color: #0284C7;
}}

QLabel#sidebarVersion {{
    font-size: 10px;
    color: #94A3B8;
}}

/* Drop Area for Court Decisions */
QFrame#courtDropArea,
QFrame#kartotekaDropArea {{
    background-color: #F8FAFC;
    border: 1.5px dashed #38BDF8;
    border-radius: 8px;
}}

QFrame#courtDropArea:hover, QFrame#courtDropArea[dragOver="true"],
QFrame#kartotekaDropArea:hover, QFrame#kartotekaDropArea[dragOver="true"] {{
    background-color: #F0F9FF;
    border: 2px dashed #0284C7;
}}

QLabel#dropAreaText,
QLabel#kartotekaDropAreaText {{
    color: #0369A1;
    font-size: 12px;
    font-weight: 600;
}}

QLabel#formSectionHeader {{
    font-size: 12px;
    font-weight: 700;
    color: #0369A1;
    padding-top: 4px;
    padding-bottom: 2px;
}}

QLineEdit#formLineEdit {{
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    padding: 5px 8px;
    font-size: 12px;
    min-height: 20px;
}}

QLineEdit#formLineEdit:focus {{
    border: 1px solid #2563EB;
    background-color: #F8FAFC;
}}

QProgressBar#parsingProgressBar {{
    background-color: #E2E8F0;
    border-radius: 4px;
    border: none;
}}

QProgressBar#parsingProgressBar::chunk {{
    background-color: #2563EB;
    border-radius: 4px;
}}

QLabel#parsingStatusLabel {{
    font-size: 11px;
    color: #0369A1;
    font-weight: 600;
}}

/* Tables & Tree Views (Light Theme) */
QTableWidget,
QTableView {{
    background-color: #FFFFFF !important;
    background: #FFFFFF !important;
    color: #0F172A !important;
    gridline-color: #E2E8F0;
    border: 1px solid #CBD5E1;
    border-radius: 8px;
    selection-background-color: #EFF6FF !important;
    selection-color: #1D4ED8 !important;
    outline: none;
    font-size: 13px;
}}

QTableWidget::item,
QTableView::item {{
    padding: 6px 8px;
    border: none;
    color: #0F172A !important;
    background-color: #FFFFFF !important;
}}

QTableWidget::item:selected,
QTableView::item:selected {{
    background-color: #EFF6FF !important;
    color: #1D4ED8 !important;
    border: none !important;
    outline: none !important;
}}

QTableWidget::item:hover,
QTableView::item:hover {{
    background-color: #E0F2FE !important;
    color: #0369A1 !important;
}}

QHeaderView::section {{
    background-color: #F8FAFC !important;
    color: #475569 !important;
    font-weight: 600;
    font-size: 12px;
    padding: 6px 8px;
    border: none;
    border-bottom: 1px solid #CBD5E1;
    border-right: 1px solid #E2E8F0;
}}

QTableCornerButton::section {{
    background-color: #F8FAFC !important;
    border: none;
    border-bottom: 1px solid #CBD5E1;
    border-right: 1px solid #E2E8F0;
}}

/* Combo Boxes (Light Theme) */
QComboBox {{
    background-color: #FFFFFF !important;
    border: 1px solid #CBD5E1;
    border-radius: 8px;
    padding: 6px 12px;
    color: #0F172A !important;
    font-size: 13px;
    min-height: 28px;
}}

QComboBox:hover {{
    border: 1px solid #94A3B8;
}}

QComboBox:focus {{
    border: 1px solid #2563EB;
}}

QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 28px;
    border-left: none;
    border-top-right-radius: 8px;
    border-bottom-right-radius: 8px;
}}

QComboBox::down-arrow {{
    image: url("{ICONS_DIR}/arrow_down_dark.png");
    width: 12px;
    height: 12px;
}}

QComboBox QAbstractItemView {{
    background-color: #FFFFFF !important;
    background: #FFFFFF !important;
    color: #0F172A !important;
    border: 1px solid #CBD5E1;
    border-radius: 8px;
    padding: 4px;
    selection-background-color: #EFF6FF !important;
    selection-color: #1D4ED8 !important;
    outline: none;
    font-size: 13px;
}}

QComboBox QAbstractItemView::item {{
    padding: 6px 10px;
    border-radius: 4px;
    color: #0F172A !important;
    background: transparent;
    min-height: 24px;
}}

QComboBox QAbstractItemView::item:hover {{
    background-color: #E0F2FE !important;
    color: #0369A1 !important;
}}

QComboBox QAbstractItemView::item:selected {{
    background-color: #EFF6FF !important;
    color: #1D4ED8 !important;
    font-weight: 600;
}}

/* Auto-complete Popup (Light Theme) */
QCompleter QAbstractItemView,
QListView#completerPopup,
QListView#debtorCompleterPopup {{
    background-color: #FFFFFF !important;
    background: #FFFFFF !important;
    color: #0F172A !important;
    border: 1px solid #CBD5E1;
    border-radius: 8px;
    padding: 4px;
    selection-background-color: #EFF6FF !important;
    selection-color: #1D4ED8 !important;
    outline: none;
    font-size: 12px;
}}

QCompleter QAbstractItemView::item,
QListView#completerPopup::item,
QListView#debtorCompleterPopup::item {{
    padding: 6px 10px;
    border-radius: 4px;
    color: #1E293B !important;
    background: transparent;
}}

QCompleter QAbstractItemView::item:hover,
QListView#completerPopup::item:hover,
QListView#debtorCompleterPopup::item:hover {{
    background-color: #E0F2FE !important;
    color: #0369A1 !important;
}}

QCompleter QAbstractItemView::item:selected,
QListView#completerPopup::item:selected,
QListView#debtorCompleterPopup::item:selected {{
    background-color: #EFF6FF !important;
    color: #1D4ED8 !important;
    font-weight: 600;
}}

/* Settings Dialog Sidebar (Light Theme) */
QFrame#settingsSidebar {{
    background-color: #F8FAFC !important;
    border-right: 1px solid #CBD5E1;
}}

QPushButton#settingsNavButton {{
    background: transparent;
    color: #475569;
    border: none;
    border-radius: 8px;
    padding: 10px 14px;
    text-align: left;
    font-size: 13px;
    font-weight: 500;
}}

QPushButton#settingsNavButton:hover {{
    background-color: #E2E8F0;
    color: #0F172A;
}}

QPushButton#settingsNavButton[active="true"] {{
    background-color: #EFF6FF;
    color: #1D4ED8;
    font-weight: 700;
}}

/* Regions List Widget in Settings */
QListWidget#regionsListWidget {{
    background-color: #FFFFFF !important;
    border: 1px solid #CBD5E1;
    border-radius: 8px;
    padding: 4px;
    outline: none;
}}

QListWidget#regionsListWidget::item {{
    padding: 8px 10px;
    border-radius: 6px;
    color: #1E293B !important;
    background: transparent;
    margin: 1px 0px;
}}

QListWidget#regionsListWidget::item:hover {{
    background-color: #F1F5F9 !important;
    color: #0F172A !important;
}}

QListWidget#regionsListWidget::item:selected {{
    background-color: #EFF6FF !important;
    color: #1D4ED8 !important;
    font-weight: 600;
}}

/* Dialog Bottom Bar */
QFrame#dialogBottomBar {{
    background-color: #FFFFFF !important;
    border-top: 1px solid #CBD5E1;
    border-radius: 0px;
}}
"""



FEMININE_QSS = f"""
QMainWindow {{
    background: transparent;
    color: #38272F;
    font-family: "Inter", "Segoe UI", Arial, sans-serif;
    font-size: 13px;
}}

QDialog {{
    background-color: #FFF0F5;
    color: #38272F;
    font-family: "Inter", "Segoe UI", Arial, sans-serif;
    font-size: 13px;
}}

QWidget {{
    font-family: "Inter", "Segoe UI", Arial, sans-serif;
    font-size: 13px;
    color: #38272F;
}}

/* Glassmorphism Card Containers */
QFrame#cardFrame {{
    background-color: rgba(255, 255, 255, 0.95);
    border: 1px solid rgba(255, 175, 195, 0.85);
    border-radius: 12px;
}}

/* Group Boxes in Settings Dialog */
QGroupBox {{
    background-color: #FFFFFF;
    border: 1px solid #FFCCD5;
    border-radius: 10px;
    margin-top: 16px;
    padding-top: 0px;
    padding-bottom: 0px;
    padding-left: 0px;
    padding-right: 0px;
    font-weight: 600;
    color: #800F2F;
    font-size: 13px;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 14px;
    padding: 0 6px;
    background-color: #FFF0F5;
    color: #800F2F;
}}

/* Splitter - comfortable gap with soft rose divider line */
QSplitter::handle:horizontal {{
    background-color: #FB7185;
    margin: 6px 7px;
    border-radius: 1px;
}}

QSplitter::handle:horizontal:hover {{
    background-color: #FF4D6D;
}}

/* Tooltips */
QToolTip {{
    background-color: #590D22;
    color: #FFF0F3;
    border: 1px solid #800F2F;
    border-radius: 6px;
    padding: 5px 9px;
    font-size: 12px;
    font-weight: 500;
}}

/* Gear Settings Button (Big & Prominent) */
QPushButton#settingsButton {{
    background-color: rgba(255, 255, 255, 0.95);
    border: 1px solid #FFCCD5;
    border-radius: 12px;
    padding: 0px;
    font-size: 24px;
    text-align: center;
}}

QPushButton#settingsButton:hover {{
    background-color: #FFF0F3;
    border-color: #FF758F;
}}

/* Buttons */
QPushButton {{
    background-color: rgba(255, 255, 255, 0.95);
    color: #6A1B4D;
    border: 1px solid #FFCCD5;
    border-radius: 8px;
    padding: 6px 16px;
    font-weight: 600;
    min-height: 24px;
    font-size: 13px;
}}

QPushButton:hover {{
    background-color: #FFF0F3;
    border-color: #FF758F;
    color: #A4133C;
}}

QPushButton:pressed {{
    background-color: #FFE5EC;
}}

QPushButton:disabled {{
    background-color: rgba(255, 255, 255, 0.6);
    color: #C9A2B5;
    border-color: #FCE7F0;
}}

/* Primary Action Button */
QPushButton#primaryButton {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #FF758F, stop:1 #FF4D6D);
    color: #FFFFFF;
    border: 1px solid #E03557;
    border-radius: 8px;
    padding: 6px 20px;
    font-size: 13px;
    font-weight: 600;
    min-height: 24px;
}}

QPushButton#primaryButton:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #FF4D6D, stop:1 #C9184A);
}}

QPushButton#primaryButton:pressed {{
    background: #A4133C;
}}

/* Big Main Screen Build Button */
QPushButton#mainBuildButton {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #FF758F, stop:1 #FF4D6D);
    color: #FFFFFF;
    border: 1px solid #E03557;
    border-radius: 10px;
    padding: 10px 42px;
    font-size: 15px;
    font-weight: 700;
    min-height: 28px;
}}

QPushButton#mainBuildButton:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #FF4D6D, stop:1 #C9184A);
}}

QPushButton#mainBuildButton:pressed {{
    background: #A4133C;
}}

QPushButton#mainBuildButton:disabled {{
    background: #D8B4BE;
    border-color: #D8B4BE;
    color: #FFF0F3;
}}

/* Danger / Clear Button */
QPushButton#dangerButton {{
    background-color: rgba(255, 240, 243, 0.95);
    color: #C9184A;
    border: 1px solid #FFCCD5;
    padding: 6px 14px;
}}

QPushButton#dangerButton:hover {{
    background-color: #FFCCD5;
    border-color: #FF758F;
}}

/* Compact Tool Icon Buttons (Up, Down, Gear) - Explicit 0 padding */
QPushButton#toolIconBtn, QPushButton#iconButton {{
    background-color: rgba(255, 255, 255, 0.95);
    border: 1px solid #FFCCD5;
    border-radius: 8px;
    padding: 0px;
    font-size: 13px;
    font-weight: bold;
    text-align: center;
}}

QPushButton#toolIconBtn:hover, QPushButton#iconButton:hover {{
    background-color: #FFF0F3;
    border-color: #FF758F;
}}

/* Preview Navigation Buttons (◀, ▶, −, +) */
QPushButton#previewNavBtn {{
    background-color: rgba(255, 255, 255, 0.95);
    color: #590D22;
    border: 1px solid #FFCCD5;
    border-radius: 8px;
    padding: 0px;
    font-size: 14px;
    font-weight: bold;
    text-align: center;
    min-width: 36px;
    min-height: 34px;
}}

QPushButton#previewNavBtn:hover {{
    background-color: #FFF0F3;
    border-color: #FF758F;
}}

/* Radio Buttons */
QRadioButton {{
    color: #38272F;
    font-size: 13px;
    font-weight: 500;
    spacing: 10px;
    background: transparent;
    padding: 3px 0px;
}}

QRadioButton::indicator {{
    width: 20px;
    height: 20px;
    background: transparent;
}}

QRadioButton::indicator:unchecked {{
    image: url("{ICONS_DIR}/radio_unchecked.png");
}}

QRadioButton::indicator:checked {{
    image: url("{ICONS_DIR}/radio_checked_pink.png");
}}

/* Checkboxes */
QCheckBox {{
    color: #38272F;
    font-size: 13px;
    font-weight: 500;
    spacing: 10px;
    background: transparent;
    padding: 3px 0px;
}}

QCheckBox::indicator {{
    width: 20px;
    height: 20px;
    background: transparent;
}}

QCheckBox::indicator:unchecked {{
    image: url("{ICONS_DIR}/checkbox_unchecked.png");
}}

QCheckBox::indicator:checked {{
    image: url("{ICONS_DIR}/checkbox_checked_pink.png");
}}

/* Lists */
QListWidget {{
    background-color: rgba(255, 255, 255, 0.95);
    border: 1px solid rgba(255, 175, 195, 0.85);
    border-radius: 10px;
    outline: none;
    padding: 4px;
}}

QListWidget::item {{
    background: transparent;
    border: none;
    padding: 0px;
    margin: 2px 0px;
}}

QListWidget::item:selected {{
    background: transparent;
    border: none;
}}

/* Scroll Area & Preview Viewport - ALWAYS WHITE */
QScrollArea {{
    background-color: #FFFFFF;
    border: 1px solid rgba(255, 175, 195, 0.85);
    border-radius: 8px;
}}

QScrollArea > QWidget > QWidget {{
    background-color: #FFFFFF;
}}

/* Scrollbars */
QScrollBar:vertical {{
    border: none;
    background: #FFF0F3;
    width: 8px;
    border-radius: 4px;
    margin: 2px;
}}

QScrollBar::handle:vertical {{
    background: #FFB3C1;
    min-height: 24px;
    border-radius: 4px;
}}

QScrollBar::handle:vertical:hover {{
    background: #FF758F;
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QScrollBar:horizontal {{
    border: none;
    background: #FFF0F3;
    height: 8px;
    border-radius: 4px;
    margin: 2px;
}}

QScrollBar::handle:horizontal {{
    background: #FFB3C1;
    min-width: 24px;
    border-radius: 4px;
}}

QScrollBar::handle:horizontal:hover {{
    background: #FF758F;
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}

/* Line Edit / Input */
QLineEdit,
QTextEdit,
QPlainTextEdit {{
    background-color: #FFFFFF !important;
    background: #FFFFFF !important;
    border: 1px solid #FFCCD5;
    border-radius: 8px;
    padding: 6px 10px;
    color: #38272F !important;
    font-size: 13px;
    min-height: 24px;
}}

QLineEdit:focus,
QTextEdit:focus,
QPlainTextEdit:focus {{
    border: 1px solid #FF758F;
}}

/* Typography */
QLabel#headerTitle {{
    font-size: 15px;
    font-weight: 700;
    color: #590D22;
}}

QLabel#subTitle {{
    font-size: 12px;
    color: #A4133C;
}}

QLabel#successHighlight {{
    color: #A4133C;
    font-weight: 600;
    font-size: 12px;
}}

/* Sidebar Styles (Feminine) */
QFrame#sidebarFrame {{
    background-color: rgba(255, 255, 255, 0.95);
    border: 1px solid rgba(255, 175, 195, 0.85);
    border-radius: 12px;
}}

QLabel#sidebarTitle {{
    font-size: 16px;
    font-weight: 700;
    color: #800F2F;
}}

QLabel#sidebarSubtitle {{
    font-size: 10px;
    font-weight: 500;
    color: #A4133C;
}}

QFrame#sidebarDivider {{
    color: #FFCCD5;
    background-color: #FFCCD5;
    max-height: 1px;
}}

QPushButton#sidebarNavButton {{
    background-color: transparent;
    color: #590D22;
    border: 1px solid transparent;
    border-radius: 8px;
    padding: 8px 10px;
    font-size: 12px;
    font-weight: 600;
    text-align: left;
}}

QPushButton#sidebarNavButton:hover {{
    background-color: #FFF0F3;
    color: #A4133C;
    border-color: #FFCCD5;
}}

QPushButton#sidebarNavButton[active="true"] {{
    background-color: #FF4D6D;
    color: #FFFFFF;
    border: 1px solid #C9184A;
    font-weight: 700;
}}

QPushButton#sidebarSettingsButton {{
    background-color: #FFFFFF;
    color: #590D22;
    border: 1px solid #FFCCD5;
    border-radius: 8px;
    padding: 6px 14px;
    font-size: 12px;
    font-weight: 600;
    text-align: left;
}}

QPushButton#sidebarSettingsButton:hover {{
    background-color: #FFF0F3;
    color: #800F2F;
    border-color: #FF758F;
}}

QLabel#sidebarVersion {{
    font-size: 10px;
    color: #C97A8E;
}}

/* Drop Area for Court Decisions (Feminine) */
QFrame#courtDropArea,
QFrame#kartotekaDropArea {{
    background-color: #FFF9FA;
    border: 1.5px dashed #FFB3C1;
    border-radius: 8px;
}}

QFrame#courtDropArea:hover, QFrame#courtDropArea[dragOver="true"],
QFrame#kartotekaDropArea:hover, QFrame#kartotekaDropArea[dragOver="true"] {{
    background-color: #FFF0F3;
    border: 2px dashed #FF4D6D;
}}

QLabel#dropAreaText,
QLabel#kartotekaDropAreaText {{
    color: #A4133C;
    font-size: 12px;
    font-weight: 600;
}}

QLabel#formSectionHeader {{
    font-size: 12px;
    font-weight: 700;
    color: #800F2F;
    padding-top: 4px;
    padding-bottom: 2px;
}}

QLineEdit#formLineEdit {{
    background-color: #FFFFFF;
    border: 1px solid #FFCCD5;
    border-radius: 6px;
    padding: 5px 8px;
    font-size: 12px;
    min-height: 20px;
    color: #38272F;
}}

QLineEdit#formLineEdit:focus {{
    border: 1px solid #FF4D6D;
    background-color: #FFFDFE;
}}

QProgressBar#parsingProgressBar {{
    background-color: #FFE5EC;
    border-radius: 4px;
    border: none;
}}

QProgressBar#parsingProgressBar::chunk {{
    background-color: #FF4D6D;
    border-radius: 4px;
}}

QLabel#parsingStatusLabel {{
    font-size: 11px;
    color: #A4133C;
    font-weight: 600;
}}

/* Tables & Tree Views (Feminine Theme) */
QTableWidget,
QTableView {{
    background-color: #FFFFFF !important;
    background: #FFFFFF !important;
    color: #38272F !important;
    gridline-color: #FFE5EC;
    border: 1px solid #FFCCD5;
    border-radius: 8px;
    selection-background-color: #FFF0F3 !important;
    selection-color: #C9184A !important;
    outline: none;
    font-size: 13px;
}}

QTableWidget::item,
QTableView::item {{
    padding: 6px 8px;
    border: none;
    color: #38272F !important;
    background-color: #FFFFFF !important;
}}

QTableWidget::item:selected,
QTableView::item:selected {{
    background-color: #FFF0F3 !important;
    color: #C9184A !important;
    border: none !important;
    outline: none !important;
}}

QTableWidget::item:hover,
QTableView::item:hover {{
    background-color: #FCE7F3 !important;
    color: #9D174D !important;
}}

QHeaderView::section {{
    background-color: #FFF5F7 !important;
    color: #7A2838 !important;
    font-weight: 600;
    font-size: 12px;
    padding: 6px 8px;
    border: none;
    border-bottom: 1px solid #FFCCD5;
    border-right: 1px solid #FFE5EC;
}}

QTableCornerButton::section {{
    background-color: #FFF5F7 !important;
    border: none;
    border-bottom: 1px solid #FFCCD5;
    border-right: 1px solid #FFE5EC;
}}

/* Combo Boxes (Feminine Theme) */
QComboBox {{
    background-color: #FFFFFF !important;
    border: 1px solid #FFCCD5;
    border-radius: 8px;
    padding: 6px 12px;
    color: #38272F !important;
    font-size: 13px;
    min-height: 28px;
}}

QComboBox:hover {{
    border: 1px solid #FFB3C1;
}}

QComboBox:focus {{
    border: 1px solid #FF4D6D;
}}

QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 28px;
    border-left: none;
    border-top-right-radius: 8px;
    border-bottom-right-radius: 8px;
}}

QComboBox::down-arrow {{
    image: url("{ICONS_DIR}/arrow_down_dark.png");
    width: 12px;
    height: 12px;
}}

QComboBox QAbstractItemView {{
    background-color: #FFFFFF !important;
    background: #FFFFFF !important;
    color: #38272F !important;
    border: 1px solid #FFCCD5;
    border-radius: 8px;
    padding: 4px;
    selection-background-color: #FFF0F3 !important;
    selection-color: #C9184A !important;
    outline: none;
    font-size: 13px;
}}

QComboBox QAbstractItemView::item {{
    padding: 6px 10px;
    border-radius: 4px;
    color: #38272F !important;
    background: transparent;
    min-height: 24px;
}}

QComboBox QAbstractItemView::item:hover {{
    background-color: #FCE7F3 !important;
    color: #9D174D !important;
}}

QComboBox QAbstractItemView::item:selected {{
    background-color: #FFF0F3 !important;
    color: #C9184A !important;
    font-weight: 600;
}}

/* Auto-complete Popup (Feminine Theme) */
QCompleter QAbstractItemView,
QListView#completerPopup,
QListView#debtorCompleterPopup {{
    background-color: #FFFFFF !important;
    background: #FFFFFF !important;
    color: #38272F !important;
    border: 1px solid #FFCCD5;
    border-radius: 8px;
    padding: 4px;
    selection-background-color: #FFF0F3 !important;
    selection-color: #C9184A !important;
    outline: none;
    font-size: 12px;
}}

QCompleter QAbstractItemView::item,
QListView#completerPopup::item,
QListView#debtorCompleterPopup::item {{
    padding: 6px 10px;
    border-radius: 4px;
    color: #4A0E17 !important;
    background: transparent;
}}

QCompleter QAbstractItemView::item:hover,
QListView#completerPopup::item:hover,
QListView#debtorCompleterPopup::item:hover {{
    background-color: #FCE7F3 !important;
    color: #9D174D !important;
}}

QCompleter QAbstractItemView::item:selected,
QListView#completerPopup::item:selected,
QListView#debtorCompleterPopup::item:selected {{
    background-color: #FFF0F3 !important;
    color: #C9184A !important;
    font-weight: 600;
}}

/* Settings Dialog Sidebar (Feminine Theme) */
QFrame#settingsSidebar {{
    background-color: #FFF9FA !important;
    border-right: 1px solid #FFCCD5;
}}

QPushButton#settingsNavButton {{
    background: transparent;
    color: #7A2838;
    border: none;
    border-radius: 8px;
    padding: 10px 14px;
    text-align: left;
    font-size: 13px;
    font-weight: 500;
}}

QPushButton#settingsNavButton:hover {{
    background-color: #FFE5EC;
    color: #38272F;
}}

QPushButton#settingsNavButton[active="true"] {{
    background-color: #FFF0F3;
    color: #C9184A;
    font-weight: 700;
}}

/* Regions List Widget in Settings (Feminine) */
QListWidget#regionsListWidget {{
    background-color: #FFFFFF !important;
    border: 1px solid #FFCCD5;
    border-radius: 8px;
    padding: 4px;
    outline: none;
}}

QListWidget#regionsListWidget::item {{
    padding: 8px 10px;
    border-radius: 6px;
    color: #38272F !important;
    background: transparent;
    margin: 1px 0px;
}}

QListWidget#regionsListWidget::item:hover {{
    background-color: #FFE5EC !important;
    color: #38272F !important;
}}

QListWidget#regionsListWidget::item:selected {{
    background-color: #FFF0F3 !important;
    color: #C9184A !important;
    font-weight: 600;
}}

/* Dialog Bottom Bar */
QFrame#dialogBottomBar {{
    background-color: #FFFFFF !important;
    border-top: 1px solid #FFCCD5;
    border-radius: 0px;
}}
"""


# ==============================================================================
# Background Painters
# ==============================================================================


CAPPUCCINO_QSS = f"""
QMainWindow {{
    background: transparent;
    color: #2D241E;
    font-family: "Inter", "Segoe UI", Arial, sans-serif;
    font-size: 13px;
}}

QDialog {{
    background-color: #F7F1EB;
    color: #2D241E;
    font-family: "Inter", "Segoe UI", Arial, sans-serif;
    font-size: 13px;
}}

QWidget {{
    font-family: "Inter", "Segoe UI", Arial, sans-serif;
    font-size: 13px;
    color: #2D241E;
}}

/* Card Containers */
QFrame#cardFrame {{
    background-color: #FFFFFF;
    border: 1px solid #D7C7B7;
    border-radius: 12px;
}}

/* Group Boxes in Settings Dialog */
QGroupBox {{
    background-color: #FFFFFF;
    border: 1px solid #D7C7B7;
    border-radius: 10px;
    margin-top: 16px;
    padding-top: 0px;
    padding-bottom: 0px;
    padding-left: 0px;
    padding-right: 0px;
    font-weight: 600;
    color: #6F4528;
    font-size: 13px;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 14px;
    padding: 0 6px;
    background-color: #F7F1EB;
    color: #6F4528;
}}

/* Splitter - comfortable gap with centered thin divider line */
QSplitter::handle:horizontal {{
    background-color: #9C8573;
    margin: 6px 7px;
    border-radius: 1px;
}}

QSplitter::handle:horizontal:hover {{
    background-color: #8C5E3C;
}}

/* Tooltips */
QToolTip {{
    background-color: #3E3228;
    color: #FBF8F5;
    border: 1px solid #634E3E;
    border-radius: 6px;
    padding: 5px 9px;
    font-size: 12px;
    font-weight: 500;
}}

/* Gear Settings Button (Big & Prominent) */
QPushButton#settingsButton {{
    background-color: rgba(255, 255, 255, 0.95);
    border: 1px solid #D7C7B7;
    border-radius: 12px;
    padding: 0px;
    font-size: 24px;
    text-align: center;
}}

QPushButton#settingsButton:hover {{
    background-color: #F7F1EB;
    border-color: #8C5E3C;
}}

/* Standard Buttons */
QPushButton {{
    background-color: #FFFFFF;
    color: #2D241E;
    border: 1px solid #D7C7B7;
    border-radius: 8px;
    padding: 6px 16px;
    font-weight: 600;
    min-height: 24px;
    font-size: 13px;
}}

QPushButton:hover {{
    background-color: #F4EDE4;
    border-color: #7A6453;
}}

QPushButton:pressed {{
    background-color: #EAE0D5;
}}

QPushButton:disabled {{
    background-color: #FBF8F5;
    color: #9C8573;
    border-color: #EAE0D5;
}}

/* Primary Action Button (Dialogs & Build) */
QPushButton#primaryButton {{
    background-color: #8C5E3C;
    color: #FFFFFF;
    border: 1px solid #6F4528;
    border-radius: 8px;
    padding: 6px 20px;
    font-size: 13px;
    font-weight: 600;
    min-height: 24px;
}}

QPushButton#primaryButton:hover {{
    background-color: #6F4528;
}}

QPushButton#primaryButton:pressed {{
    background-color: #1E40AF;
}}

/* Big Main Screen Build Button */
QPushButton#mainBuildButton {{
    background-color: #8C5E3C;
    color: #FFFFFF;
    border: 1px solid #6F4528;
    border-radius: 10px;
    padding: 10px 42px;
    font-size: 15px;
    font-weight: 700;
    min-height: 28px;
}}

QPushButton#mainBuildButton:hover {{
    background-color: #6F4528;
}}

QPushButton#mainBuildButton:pressed {{
    background-color: #1E40AF;
}}

QPushButton#mainBuildButton:disabled {{
    background-color: #9C8573;
    border-color: #9C8573;
    color: #F4EDE4;
}}

/* Danger / Clear Button */
QPushButton#dangerButton {{
    background-color: #FFF1F2;
    color: #E11D48;
    border: 1px solid #FECDD3;
    padding: 6px 14px;
}}

QPushButton#dangerButton:hover {{
    background-color: #FFE4E6;
    border-color: #FDA4AF;
}}

/* Compact Tool Icon Buttons (Up, Down, Gear) - Explicit 0 padding */
QPushButton#toolIconBtn, QPushButton#iconButton {{
    background-color: #FFFFFF;
    border: 1px solid #D7C7B7;
    border-radius: 8px;
    padding: 0px;
    font-size: 13px;
    font-weight: bold;
    text-align: center;
}}

QPushButton#toolIconBtn:hover, QPushButton#iconButton:hover {{
    background-color: #F4EDE4;
    border-color: #7A6453;
}}

/* Preview Navigation Buttons (◀, ▶, −, +) */
QPushButton#previewNavBtn {{
    background-color: #FFFFFF;
    color: #2D241E;
    border: 1px solid #D7C7B7;
    border-radius: 8px;
    padding: 0px;
    font-size: 14px;
    font-weight: bold;
    text-align: center;
    min-width: 36px;
    min-height: 34px;
}}

QPushButton#previewNavBtn:hover {{
    background-color: #F4EDE4;
    border-color: #7A6453;
}}

/* Radio Buttons */
QRadioButton {{
    color: #2D241E;
    font-size: 13px;
    font-weight: 500;
    spacing: 10px;
    background: transparent;
    padding: 3px 0px;
}}

QRadioButton::indicator {{
    width: 20px;
    height: 20px;
    background: transparent;
}}

QRadioButton::indicator:unchecked {{
    image: url("{ICONS_DIR}/radio_unchecked.png");
}}

QRadioButton::indicator:checked {{
    image: url("{ICONS_DIR}/radio_checked_cappuccino.png");
}}

/* Checkboxes */
QCheckBox {{
    color: #2D241E;
    font-size: 13px;
    font-weight: 500;
    spacing: 10px;
    background: transparent;
    padding: 3px 0px;
}}

QCheckBox::indicator {{
    width: 20px;
    height: 20px;
    background: transparent;
}}

QCheckBox::indicator:unchecked {{
    image: url("{ICONS_DIR}/checkbox_unchecked.png");
}}

QCheckBox::indicator:checked {{
    image: url("{ICONS_DIR}/checkbox_checked_cappuccino.png");
}}

/* Lists */
QListWidget {{
    background-color: #FFFFFF;
    border: 1px solid #D7C7B7;
    border-radius: 10px;
    outline: none;
    padding: 4px;
}}

QListWidget::item {{
    background: transparent;
    border: none;
    padding: 0px;
    margin: 2px 0px;
}}

QListWidget::item:selected {{
    background: transparent;
    border: none;
}}

/* Scroll Area & Preview Viewport - ALWAYS WHITE */
QScrollArea {{
    background-color: #FFFFFF;
    border: 1px solid #D7C7B7;
    border-radius: 8px;
}}

QScrollArea > QWidget > QWidget {{
    background-color: #FFFFFF;
}}

/* Scrollbars */
QScrollBar:vertical {{
    border: none;
    background: #F4EDE4;
    width: 8px;
    border-radius: 4px;
    margin: 2px;
}}

QScrollBar::handle:vertical {{
    background: #9C8573;
    min-height: 24px;
    border-radius: 4px;
}}

QScrollBar::handle:vertical:hover {{
    background: #7A6453;
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QScrollBar:horizontal {{
    border: none;
    background: #F4EDE4;
    height: 8px;
    border-radius: 4px;
    margin: 2px;
}}

QScrollBar::handle:horizontal {{
    background: #9C8573;
    min-width: 24px;
    border-radius: 4px;
}}

QScrollBar::handle:horizontal:hover {{
    background: #7A6453;
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}

/* Line Edit / Input */
QLineEdit,
QTextEdit,
QPlainTextEdit {{
    background-color: #FFFFFF !important;
    background: #FFFFFF !important;
    border: 1px solid #D7C7B7;
    border-radius: 8px;
    padding: 6px 10px;
    color: #2D241E !important;
    font-size: 13px;
    min-height: 24px;
}}

QLineEdit:focus,
QTextEdit:focus,
QPlainTextEdit:focus {{
    border: 1px solid #8C5E3C;
}}

/* Typography */
QLabel#headerTitle {{
    font-size: 15px;
    font-weight: 700;
    color: #2D241E;
}}

QLabel#subTitle {{
    font-size: 12px;
    color: #7A6453;
}}

QLabel#successHighlight {{
    color: #6F4528;
    font-weight: 600;
    font-size: 12px;
}}

/* Sidebar Styles (Light) */
QFrame#sidebarFrame {{
    background-color: rgba(255, 255, 255, 0.92);
    border: 1px solid #D7C7B7;
    border-radius: 12px;
}}

QLabel#sidebarTitle {{
    font-size: 16px;
    font-weight: 700;
    color: #6F4528;
}}

QLabel#sidebarSubtitle {{
    font-size: 10px;
    font-weight: 500;
    color: #7A6453;
}}

QFrame#sidebarDivider {{
    color: #D7C7B7;
    background-color: #D7C7B7;
    max-height: 1px;
}}

QPushButton#sidebarNavButton {{
    background-color: transparent;
    color: #334155;
    border: 1px solid transparent;
    border-radius: 8px;
    padding: 8px 10px;
    font-size: 12px;
    font-weight: 600;
    text-align: left;
}}

QPushButton#sidebarNavButton:hover {{
    background-color: #F7F1EB;
    color: #6F4528;
    border-color: #D7C7B7;
}}

QPushButton#sidebarNavButton[active="true"] {{
    background-color: #8C5E3C;
    color: #FFFFFF;
    border: 1px solid #6F4528;
    font-weight: 700;
}}

QPushButton#sidebarSettingsButton {{
    background-color: #FFFFFF;
    color: #334155;
    border: 1px solid #D7C7B7;
    border-radius: 8px;
    padding: 6px 14px;
    font-size: 12px;
    font-weight: 600;
    text-align: left;
}}

QPushButton#sidebarSettingsButton:hover {{
    background-color: #F7F1EB;
    color: #6F4528;
    border-color: #8C5E3C;
}}

QLabel#sidebarVersion {{
    font-size: 10px;
    color: #9C8573;
}}

/* Drop Area for Court Decisions */
QFrame#courtDropArea,
QFrame#kartotekaDropArea {{
    background-color: #FBF8F5;
    border: 1.5px dashed #B0937C;
    border-radius: 8px;
}}

QFrame#courtDropArea:hover, QFrame#courtDropArea[dragOver="true"],
QFrame#kartotekaDropArea:hover, QFrame#kartotekaDropArea[dragOver="true"] {{
    background-color: #F7F1EB;
    border: 2px dashed #8C5E3C;
}}

QLabel#dropAreaText,
QLabel#kartotekaDropAreaText {{
    color: #6F4528;
    font-size: 12px;
    font-weight: 600;
}}

QLabel#formSectionHeader {{
    font-size: 12px;
    font-weight: 700;
    color: #6F4528;
    padding-top: 4px;
    padding-bottom: 2px;
}}

QLineEdit#formLineEdit {{
    background-color: #FFFFFF;
    border: 1px solid #D7C7B7;
    border-radius: 6px;
    padding: 5px 8px;
    font-size: 12px;
    min-height: 20px;
}}

QLineEdit#formLineEdit:focus {{
    border: 1px solid #8C5E3C;
    background-color: #FBF8F5;
}}

QProgressBar#parsingProgressBar {{
    background-color: #EAE0D5;
    border-radius: 4px;
    border: none;
}}

QProgressBar#parsingProgressBar::chunk {{
    background-color: #8C5E3C;
    border-radius: 4px;
}}

QLabel#parsingStatusLabel {{
    font-size: 11px;
    color: #6F4528;
    font-weight: 600;
}}

/* Tables & Tree Views (Light Theme) */
QTableWidget,
QTableView {{
    background-color: #FFFFFF !important;
    background: #FFFFFF !important;
    color: #2D241E !important;
    gridline-color: #EAE0D5;
    border: 1px solid #D7C7B7;
    border-radius: 8px;
    selection-background-color: #F2E9E1 !important;
    selection-color: #6F4528 !important;
    outline: none;
    font-size: 13px;
}}

QTableWidget::item,
QTableView::item {{
    padding: 6px 8px;
    border: none;
    color: #2D241E !important;
    background-color: #FFFFFF !important;
}}

QTableWidget::item:selected,
QTableView::item:selected {{
    background-color: #F2E9E1 !important;
    color: #6F4528 !important;
    border: none !important;
    outline: none !important;
}}

QTableWidget::item:hover,
QTableView::item:hover {{
    background-color: #EAE0D5 !important;
    color: #6F4528 !important;
}}

QHeaderView::section {{
    background-color: #FBF8F5 !important;
    color: #634E3E !important;
    font-weight: 600;
    font-size: 12px;
    padding: 6px 8px;
    border: none;
    border-bottom: 1px solid #D7C7B7;
    border-right: 1px solid #EAE0D5;
}}

QTableCornerButton::section {{
    background-color: #FBF8F5 !important;
    border: none;
    border-bottom: 1px solid #D7C7B7;
    border-right: 1px solid #EAE0D5;
}}

/* Combo Boxes (Light Theme) */
QComboBox {{
    background-color: #FFFFFF !important;
    border: 1px solid #D7C7B7;
    border-radius: 8px;
    padding: 6px 12px;
    color: #2D241E !important;
    font-size: 13px;
    min-height: 28px;
}}

QComboBox:hover {{
    border: 1px solid #9C8573;
}}

QComboBox:focus {{
    border: 1px solid #8C5E3C;
}}

QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 28px;
    border-left: none;
    border-top-right-radius: 8px;
    border-bottom-right-radius: 8px;
}}

QComboBox::down-arrow {{
    image: url("{ICONS_DIR}/arrow_down_dark.png");
    width: 12px;
    height: 12px;
}}

QComboBox QAbstractItemView {{
    background-color: #FFFFFF !important;
    background: #FFFFFF !important;
    color: #2D241E !important;
    border: 1px solid #D7C7B7;
    border-radius: 8px;
    padding: 4px;
    selection-background-color: #F2E9E1 !important;
    selection-color: #6F4528 !important;
    outline: none;
    font-size: 13px;
}}

QComboBox QAbstractItemView::item {{
    padding: 6px 10px;
    border-radius: 4px;
    color: #2D241E !important;
    background: transparent;
    min-height: 24px;
}}

QComboBox QAbstractItemView::item:hover {{
    background-color: #EAE0D5 !important;
    color: #6F4528 !important;
}}

QComboBox QAbstractItemView::item:selected {{
    background-color: #F2E9E1 !important;
    color: #6F4528 !important;
    font-weight: 600;
}}

/* Auto-complete Popup (Light Theme) */
QCompleter QAbstractItemView,
QListView#completerPopup,
QListView#debtorCompleterPopup {{
    background-color: #FFFFFF !important;
    background: #FFFFFF !important;
    color: #2D241E !important;
    border: 1px solid #D7C7B7;
    border-radius: 8px;
    padding: 4px;
    selection-background-color: #F2E9E1 !important;
    selection-color: #6F4528 !important;
    outline: none;
    font-size: 12px;
}}

QCompleter QAbstractItemView::item,
QListView#completerPopup::item,
QListView#debtorCompleterPopup::item {{
    padding: 6px 10px;
    border-radius: 4px;
    color: #3E3228 !important;
    background: transparent;
}}

QCompleter QAbstractItemView::item:hover,
QListView#completerPopup::item:hover,
QListView#debtorCompleterPopup::item:hover {{
    background-color: #EAE0D5 !important;
    color: #6F4528 !important;
}}

QCompleter QAbstractItemView::item:selected,
QListView#completerPopup::item:selected,
QListView#debtorCompleterPopup::item:selected {{
    background-color: #F2E9E1 !important;
    color: #6F4528 !important;
    font-weight: 600;
}}
/* Settings Dialog Sidebar (Cappuccino Theme) */
QFrame#settingsSidebar {{
    background-color: #FBF8F5 !important;
    border-right: 1px solid #D7C7B7;
}}

QPushButton#settingsNavButton {{
    background: transparent;
    color: #634E3E;
    border: none;
    border-radius: 8px;
    padding: 10px 14px;
    text-align: left;
    font-size: 13px;
    font-weight: 500;
}}

QPushButton#settingsNavButton:hover {{
    background-color: #EAE0D5;
    color: #2D241E;
}}

QPushButton#settingsNavButton[active="true"] {{
    background-color: #F2E9E1;
    color: #6F4528;
    font-weight: 700;
}}

/* Regions List Widget in Settings (Cappuccino) */
QListWidget#regionsListWidget {{
    background-color: #FFFFFF !important;
    border: 1px solid #D7C7B7;
    border-radius: 8px;
    padding: 4px;
    outline: none;
}}

QListWidget#regionsListWidget::item {{
    padding: 8px 10px;
    border-radius: 6px;
    color: #2D241E !important;
    background: transparent;
    margin: 1px 0px;
}}

QListWidget#regionsListWidget::item:hover {{
    background-color: #EAE0D5 !important;
    color: #2D241E !important;
}}

QListWidget#regionsListWidget::item:selected {{
    background-color: #F2E9E1 !important;
    color: #6F4528 !important;
    font-weight: 600;
}}

/* Dialog Bottom Bar */
QFrame#dialogBottomBar {{
    background-color: #FFFFFF !important;
    border-top: 1px solid #D7C7B7;
    border-radius: 0px;
}}
"""


LAVENDER_QSS = f"""
QMainWindow {{
    background: transparent;
    color: #1E1B4B;
    font-family: "Inter", "Segoe UI", Arial, sans-serif;
    font-size: 13px;
}}

QDialog {{
    background-color: #F5F3FF;
    color: #1E1B4B;
    font-family: "Inter", "Segoe UI", Arial, sans-serif;
    font-size: 13px;
}}

QWidget {{
    font-family: "Inter", "Segoe UI", Arial, sans-serif;
    font-size: 13px;
    color: #1E1B4B;
}}

/* Card Containers */
QFrame#cardFrame {{
    background-color: #FFFFFF;
    border: 1px solid #DDD6FE;
    border-radius: 12px;
}}

/* Group Boxes in Settings Dialog */
QGroupBox {{
    background-color: #FFFFFF;
    border: 1px solid #DDD6FE;
    border-radius: 10px;
    margin-top: 16px;
    padding-top: 0px;
    padding-bottom: 0px;
    padding-left: 0px;
    padding-right: 0px;
    font-weight: 600;
    color: #6D28D9;
    font-size: 13px;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 14px;
    padding: 0 6px;
    background-color: #F5F3FF;
    color: #6D28D9;
}}

/* Splitter - comfortable gap with centered thin divider line */
QSplitter::handle:horizontal {{
    background-color: #8B5CF6;
    margin: 6px 7px;
    border-radius: 1px;
}}

QSplitter::handle:horizontal:hover {{
    background-color: #7C3AED;
}}

/* Tooltips */
QToolTip {{
    background-color: #2E1065;
    color: #FAF8FF;
    border: 1px solid #4C1D95;
    border-radius: 6px;
    padding: 5px 9px;
    font-size: 12px;
    font-weight: 500;
}}

/* Gear Settings Button (Big & Prominent) */
QPushButton#settingsButton {{
    background-color: rgba(255, 255, 255, 0.95);
    border: 1px solid #DDD6FE;
    border-radius: 12px;
    padding: 0px;
    font-size: 24px;
    text-align: center;
}}

QPushButton#settingsButton:hover {{
    background-color: #F5F3FF;
    border-color: #7C3AED;
}}

/* Standard Buttons */
QPushButton {{
    background-color: #FFFFFF;
    color: #1E1B4B;
    border: 1px solid #DDD6FE;
    border-radius: 8px;
    padding: 6px 16px;
    font-weight: 600;
    min-height: 24px;
    font-size: 13px;
}}

QPushButton:hover {{
    background-color: #F5F3FF;
    border-color: #6D28D9;
}}

QPushButton:pressed {{
    background-color: #EDE9FE;
}}

QPushButton:disabled {{
    background-color: #FAF8FF;
    color: #8B5CF6;
    border-color: #EDE9FE;
}}

/* Primary Action Button (Dialogs & Build) */
QPushButton#primaryButton {{
    background-color: #7C3AED;
    color: #FFFFFF;
    border: 1px solid #6D28D9;
    border-radius: 8px;
    padding: 6px 20px;
    font-size: 13px;
    font-weight: 600;
    min-height: 24px;
}}

QPushButton#primaryButton:hover {{
    background-color: #6D28D9;
}}

QPushButton#primaryButton:pressed {{
    background-color: #1E40AF;
}}

/* Big Main Screen Build Button */
QPushButton#mainBuildButton {{
    background-color: #7C3AED;
    color: #FFFFFF;
    border: 1px solid #6D28D9;
    border-radius: 10px;
    padding: 10px 42px;
    font-size: 15px;
    font-weight: 700;
    min-height: 28px;
}}

QPushButton#mainBuildButton:hover {{
    background-color: #6D28D9;
}}

QPushButton#mainBuildButton:pressed {{
    background-color: #1E40AF;
}}

QPushButton#mainBuildButton:disabled {{
    background-color: #8B5CF6;
    border-color: #8B5CF6;
    color: #F5F3FF;
}}

/* Danger / Clear Button */
QPushButton#dangerButton {{
    background-color: #FFF1F2;
    color: #E11D48;
    border: 1px solid #FECDD3;
    padding: 6px 14px;
}}

QPushButton#dangerButton:hover {{
    background-color: #FFE4E6;
    border-color: #FDA4AF;
}}

/* Compact Tool Icon Buttons (Up, Down, Gear) - Explicit 0 padding */
QPushButton#toolIconBtn, QPushButton#iconButton {{
    background-color: #FFFFFF;
    border: 1px solid #DDD6FE;
    border-radius: 8px;
    padding: 0px;
    font-size: 13px;
    font-weight: bold;
    text-align: center;
}}

QPushButton#toolIconBtn:hover, QPushButton#iconButton:hover {{
    background-color: #F5F3FF;
    border-color: #6D28D9;
}}

/* Preview Navigation Buttons (◀, ▶, −, +) */
QPushButton#previewNavBtn {{
    background-color: #FFFFFF;
    color: #1E1B4B;
    border: 1px solid #DDD6FE;
    border-radius: 8px;
    padding: 0px;
    font-size: 14px;
    font-weight: bold;
    text-align: center;
    min-width: 36px;
    min-height: 34px;
}}

QPushButton#previewNavBtn:hover {{
    background-color: #F5F3FF;
    border-color: #6D28D9;
}}

/* Radio Buttons */
QRadioButton {{
    color: #1E1B4B;
    font-size: 13px;
    font-weight: 500;
    spacing: 10px;
    background: transparent;
    padding: 3px 0px;
}}

QRadioButton::indicator {{
    width: 20px;
    height: 20px;
    background: transparent;
}}

QRadioButton::indicator:unchecked {{
    image: url("{ICONS_DIR}/radio_unchecked.png");
}}

QRadioButton::indicator:checked {{
    image: url("{ICONS_DIR}/radio_checked_lavender.png");
}}

/* Checkboxes */
QCheckBox {{
    color: #1E1B4B;
    font-size: 13px;
    font-weight: 500;
    spacing: 10px;
    background: transparent;
    padding: 3px 0px;
}}

QCheckBox::indicator {{
    width: 20px;
    height: 20px;
    background: transparent;
}}

QCheckBox::indicator:unchecked {{
    image: url("{ICONS_DIR}/checkbox_unchecked.png");
}}

QCheckBox::indicator:checked {{
    image: url("{ICONS_DIR}/checkbox_checked_lavender.png");
}}

/* Lists */
QListWidget {{
    background-color: #FFFFFF;
    border: 1px solid #DDD6FE;
    border-radius: 10px;
    outline: none;
    padding: 4px;
}}

QListWidget::item {{
    background: transparent;
    border: none;
    padding: 0px;
    margin: 2px 0px;
}}

QListWidget::item:selected {{
    background: transparent;
    border: none;
}}

/* Scroll Area & Preview Viewport - ALWAYS WHITE */
QScrollArea {{
    background-color: #FFFFFF;
    border: 1px solid #DDD6FE;
    border-radius: 8px;
}}

QScrollArea > QWidget > QWidget {{
    background-color: #FFFFFF;
}}

/* Scrollbars */
QScrollBar:vertical {{
    border: none;
    background: #F5F3FF;
    width: 8px;
    border-radius: 4px;
    margin: 2px;
}}

QScrollBar::handle:vertical {{
    background: #8B5CF6;
    min-height: 24px;
    border-radius: 4px;
}}

QScrollBar::handle:vertical:hover {{
    background: #6D28D9;
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QScrollBar:horizontal {{
    border: none;
    background: #F5F3FF;
    height: 8px;
    border-radius: 4px;
    margin: 2px;
}}

QScrollBar::handle:horizontal {{
    background: #8B5CF6;
    min-width: 24px;
    border-radius: 4px;
}}

QScrollBar::handle:horizontal:hover {{
    background: #6D28D9;
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}

/* Line Edit / Input */
QLineEdit,
QTextEdit,
QPlainTextEdit {{
    background-color: #FFFFFF !important;
    background: #FFFFFF !important;
    border: 1px solid #DDD6FE;
    border-radius: 8px;
    padding: 6px 10px;
    color: #1E1B4B !important;
    font-size: 13px;
    min-height: 24px;
}}

QLineEdit:focus,
QTextEdit:focus,
QPlainTextEdit:focus {{
    border: 1px solid #7C3AED;
}}

/* Typography */
QLabel#headerTitle {{
    font-size: 15px;
    font-weight: 700;
    color: #1E1B4B;
}}

QLabel#subTitle {{
    font-size: 12px;
    color: #6D28D9;
}}

QLabel#successHighlight {{
    color: #6D28D9;
    font-weight: 600;
    font-size: 12px;
}}

/* Sidebar Styles (Light) */
QFrame#sidebarFrame {{
    background-color: rgba(255, 255, 255, 0.92);
    border: 1px solid #DDD6FE;
    border-radius: 12px;
}}

QLabel#sidebarTitle {{
    font-size: 16px;
    font-weight: 700;
    color: #6D28D9;
}}

QLabel#sidebarSubtitle {{
    font-size: 10px;
    font-weight: 500;
    color: #6D28D9;
}}

QFrame#sidebarDivider {{
    color: #DDD6FE;
    background-color: #DDD6FE;
    max-height: 1px;
}}

QPushButton#sidebarNavButton {{
    background-color: transparent;
    color: #334155;
    border: 1px solid transparent;
    border-radius: 8px;
    padding: 8px 10px;
    font-size: 12px;
    font-weight: 600;
    text-align: left;
}}

QPushButton#sidebarNavButton:hover {{
    background-color: #F5F3FF;
    color: #6D28D9;
    border-color: #DDD6FE;
}}

QPushButton#sidebarNavButton[active="true"] {{
    background-color: #7C3AED;
    color: #FFFFFF;
    border: 1px solid #6D28D9;
    font-weight: 700;
}}

QPushButton#sidebarSettingsButton {{
    background-color: #FFFFFF;
    color: #334155;
    border: 1px solid #DDD6FE;
    border-radius: 8px;
    padding: 6px 14px;
    font-size: 12px;
    font-weight: 600;
    text-align: left;
}}

QPushButton#sidebarSettingsButton:hover {{
    background-color: #F5F3FF;
    color: #6D28D9;
    border-color: #7C3AED;
}}

QLabel#sidebarVersion {{
    font-size: 10px;
    color: #8B5CF6;
}}

/* Drop Area for Court Decisions */
QFrame#courtDropArea,
QFrame#kartotekaDropArea {{
    background-color: #FAF8FF;
    border: 1.5px dashed #A78BFA;
    border-radius: 8px;
}}

QFrame#courtDropArea:hover, QFrame#courtDropArea[dragOver="true"],
QFrame#kartotekaDropArea:hover, QFrame#kartotekaDropArea[dragOver="true"] {{
    background-color: #F5F3FF;
    border: 2px dashed #7C3AED;
}}

QLabel#dropAreaText,
QLabel#kartotekaDropAreaText {{
    color: #6D28D9;
    font-size: 12px;
    font-weight: 600;
}}

QLabel#formSectionHeader {{
    font-size: 12px;
    font-weight: 700;
    color: #6D28D9;
    padding-top: 4px;
    padding-bottom: 2px;
}}

QLineEdit#formLineEdit {{
    background-color: #FFFFFF;
    border: 1px solid #DDD6FE;
    border-radius: 6px;
    padding: 5px 8px;
    font-size: 12px;
    min-height: 20px;
}}

QLineEdit#formLineEdit:focus {{
    border: 1px solid #7C3AED;
    background-color: #FAF8FF;
}}

QProgressBar#parsingProgressBar {{
    background-color: #EDE9FE;
    border-radius: 4px;
    border: none;
}}

QProgressBar#parsingProgressBar::chunk {{
    background-color: #7C3AED;
    border-radius: 4px;
}}

QLabel#parsingStatusLabel {{
    font-size: 11px;
    color: #6D28D9;
    font-weight: 600;
}}

/* Tables & Tree Views (Light Theme) */
QTableWidget,
QTableView {{
    background-color: #FFFFFF !important;
    background: #FFFFFF !important;
    color: #1E1B4B !important;
    gridline-color: #EDE9FE;
    border: 1px solid #DDD6FE;
    border-radius: 8px;
    selection-background-color: #EDE9FE !important;
    selection-color: #6D28D9 !important;
    outline: none;
    font-size: 13px;
}}

QTableWidget::item,
QTableView::item {{
    padding: 6px 8px;
    border: none;
    color: #1E1B4B !important;
    background-color: #FFFFFF !important;
}}

QTableWidget::item:selected,
QTableView::item:selected {{
    background-color: #EDE9FE !important;
    color: #6D28D9 !important;
    border: none !important;
    outline: none !important;
}}

QTableWidget::item:hover,
QTableView::item:hover {{
    background-color: #DDD6FE !important;
    color: #6D28D9 !important;
}}

QHeaderView::section {{
    background-color: #FAF8FF !important;
    color: #4C1D95 !important;
    font-weight: 600;
    font-size: 12px;
    padding: 6px 8px;
    border: none;
    border-bottom: 1px solid #DDD6FE;
    border-right: 1px solid #EDE9FE;
}}

QTableCornerButton::section {{
    background-color: #FAF8FF !important;
    border: none;
    border-bottom: 1px solid #DDD6FE;
    border-right: 1px solid #EDE9FE;
}}

/* Combo Boxes (Light Theme) */
QComboBox {{
    background-color: #FFFFFF !important;
    border: 1px solid #DDD6FE;
    border-radius: 8px;
    padding: 6px 12px;
    color: #1E1B4B !important;
    font-size: 13px;
    min-height: 28px;
}}

QComboBox:hover {{
    border: 1px solid #8B5CF6;
}}

QComboBox:focus {{
    border: 1px solid #7C3AED;
}}

QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 28px;
    border-left: none;
    border-top-right-radius: 8px;
    border-bottom-right-radius: 8px;
}}

QComboBox::down-arrow {{
    image: url("{ICONS_DIR}/arrow_down_dark.png");
    width: 12px;
    height: 12px;
}}

QComboBox QAbstractItemView {{
    background-color: #FFFFFF !important;
    background: #FFFFFF !important;
    color: #1E1B4B !important;
    border: 1px solid #DDD6FE;
    border-radius: 8px;
    padding: 4px;
    selection-background-color: #EDE9FE !important;
    selection-color: #6D28D9 !important;
    outline: none;
    font-size: 13px;
}}

QComboBox QAbstractItemView::item {{
    padding: 6px 10px;
    border-radius: 4px;
    color: #1E1B4B !important;
    background: transparent;
    min-height: 24px;
}}

QComboBox QAbstractItemView::item:hover {{
    background-color: #DDD6FE !important;
    color: #6D28D9 !important;
}}

QComboBox QAbstractItemView::item:selected {{
    background-color: #EDE9FE !important;
    color: #6D28D9 !important;
    font-weight: 600;
}}

/* Auto-complete Popup (Light Theme) */
QCompleter QAbstractItemView,
QListView#completerPopup,
QListView#debtorCompleterPopup {{
    background-color: #FFFFFF !important;
    background: #FFFFFF !important;
    color: #1E1B4B !important;
    border: 1px solid #DDD6FE;
    border-radius: 8px;
    padding: 4px;
    selection-background-color: #EDE9FE !important;
    selection-color: #6D28D9 !important;
    outline: none;
    font-size: 12px;
}}

QCompleter QAbstractItemView::item,
QListView#completerPopup::item,
QListView#debtorCompleterPopup::item {{
    padding: 6px 10px;
    border-radius: 4px;
    color: #2E1065 !important;
    background: transparent;
}}

QCompleter QAbstractItemView::item:hover,
QListView#completerPopup::item:hover,
QListView#debtorCompleterPopup::item:hover {{
    background-color: #DDD6FE !important;
    color: #6D28D9 !important;
}}

QCompleter QAbstractItemView::item:selected,
QListView#completerPopup::item:selected,
QListView#debtorCompleterPopup::item:selected {{
    background-color: #EDE9FE !important;
    color: #6D28D9 !important;
    font-weight: 600;
}}
/* Settings Dialog Sidebar (Lavender Theme) */
QFrame#settingsSidebar {{
    background-color: #FAF8FF !important;
    border-right: 1px solid #DDD6FE;
}}

QPushButton#settingsNavButton {{
    background: transparent;
    color: #4C1D95;
    border: none;
    border-radius: 8px;
    padding: 10px 14px;
    text-align: left;
    font-size: 13px;
    font-weight: 500;
}}

QPushButton#settingsNavButton:hover {{
    background-color: #EDE9FE;
    color: #1E1B4B;
}}

QPushButton#settingsNavButton[active="true"] {{
    background-color: #EDE9FE;
    color: #6D28D9;
    font-weight: 700;
}}

/* Regions List Widget in Settings (Lavender) */
QListWidget#regionsListWidget {{
    background-color: #FFFFFF !important;
    border: 1px solid #DDD6FE;
    border-radius: 8px;
    padding: 4px;
    outline: none;
}}

QListWidget#regionsListWidget::item {{
    padding: 8px 10px;
    border-radius: 6px;
    color: #1E1B4B !important;
    background: transparent;
    margin: 1px 0px;
}}

QListWidget#regionsListWidget::item:hover {{
    background-color: #EDE9FE !important;
    color: #1E1B4B !important;
}}

QListWidget#regionsListWidget::item:selected {{
    background-color: #EDE9FE !important;
    color: #6D28D9 !important;
    font-weight: 600;
}}

/* Dialog Bottom Bar */
QFrame#dialogBottomBar {{
    background-color: #FFFFFF !important;
    border-top: 1px solid #DDD6FE;
    border-radius: 0px;
}}
"""


class SkyBackgroundPainter:
    """
    Renders an atmospheric light sky-blue gradient with subtle,
    deeply blurred airy clouds / morning sky glow.
    """
    def __init__(self):
        rng = random.Random(123)
        self.clouds = []
        for _ in range(16):
            self.clouds.append({
                "x_rel": rng.uniform(0.05, 0.95),
                "y_rel": rng.uniform(0.05, 0.95),
                "rx": rng.uniform(120, 280),
                "ry": rng.uniform(60, 140),
                "opacity": rng.uniform(0.18, 0.32)
            })

    def draw(self, painter: QPainter, rect: QRectF):
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, True)

        # Fresh morning sky blue gradient
        grad = QLinearGradient(0, 0, rect.width() * 0.4, rect.height())
        grad.setColorAt(0.0, QColor("#DDF2FD"))
        grad.setColorAt(0.35, QColor("#BAE6FD"))
        grad.setColorAt(0.70, QColor("#A5D8F3"))
        grad.setColorAt(1.0, QColor("#C9E7F8"))
        painter.fillRect(rect, grad)

        w = rect.width()
        h = rect.height()

        for c in self.clouds:
            cx = c["x_rel"] * w
            cy = c["y_rel"] * h
            rx = c["rx"]
            ry = c["ry"]
            alpha = int(c["opacity"] * 255)

            radial = QRadialGradient(cx, cy, rx)
            c1 = QColor(255, 255, 255, alpha)
            c2 = QColor(255, 255, 255, int(alpha * 0.4))
            c3 = QColor(255, 255, 255, 0)
            radial.setColorAt(0.0, c1)
            radial.setColorAt(0.65, c2)
            radial.setColorAt(1.0, c3)

            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(radial))
            painter.drawEllipse(QPointF(cx, cy), rx, ry)

        painter.restore()


class FeminineBackgroundPainter:
    """
    Renders a saturated pastel gradient backdrop with deeply blurred
    decorative watercolor hearts and flowers.
    """
    def __init__(self):
        rng = random.Random(42)
        self.elements = []
        for _ in range(22):
            kind = rng.choice(["heart", "flower", "bokeh"])
            x_rel = rng.uniform(0.04, 0.96)
            y_rel = rng.uniform(0.04, 0.96)
            size = rng.uniform(80, 180)
            opacity = rng.uniform(0.24, 0.40)
            angle = rng.uniform(0, 360)
            self.elements.append({
                "kind": kind,
                "x_rel": x_rel,
                "y_rel": y_rel,
                "size": size,
                "opacity": opacity,
                "angle": angle,
                "color_pair": rng.choice([
                    (QColor(255, 140, 170), QColor(255, 210, 230)),
                    (QColor(255, 160, 195), QColor(255, 200, 220)),
                    (QColor(255, 120, 160), QColor(255, 180, 210)),
                    (QColor(255, 175, 204), QColor(255, 143, 171))
                ])
            })

    def draw(self, painter: QPainter, rect: QRectF):
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, True)

        # Base saturated pastel gradient
        grad = QLinearGradient(0, 0, rect.width(), rect.height())
        grad.setColorAt(0.0, QColor(255, 195, 212))
        grad.setColorAt(0.35, QColor(255, 175, 200))
        grad.setColorAt(0.70, QColor(255, 205, 222))
        grad.setColorAt(1.0, QColor(255, 182, 206))
        painter.fillRect(rect, grad)

        w = rect.width()
        h = rect.height()

        for el in self.elements:
            cx = el["x_rel"] * w
            cy = el["y_rel"] * h
            size = el["size"]
            c_inner, c_outer = el["color_pair"]
            alpha = int(el["opacity"] * 255)

            radial = QRadialGradient(cx, cy, size / 1.3)
            c1 = QColor(c_inner)
            c1.setAlpha(alpha)
            c2 = QColor(c_outer)
            c2.setAlpha(int(alpha * 0.45))
            c3 = QColor(c_outer)
            c3.setAlpha(0)
            radial.setColorAt(0.0, c1)
            radial.setColorAt(0.65, c2)
            radial.setColorAt(1.0, c3)

            painter.save()
            painter.translate(cx, cy)
            painter.rotate(el["angle"])
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(radial))

            path = QPainterPath()
            if el["kind"] == "heart":
                hs = size / 2.0
                path.moveTo(0, hs * 0.4)
                path.cubicTo(-hs, -hs * 0.4, -hs * 0.8, -hs * 0.9, 0, -hs * 0.3)
                path.cubicTo(hs * 0.8, -hs * 0.9, hs, -hs * 0.4, 0, hs * 0.4)
                painter.drawPath(path)
            elif el["kind"] == "flower":
                petals = 5
                r_petal = size / 2.2
                for p_idx in range(petals):
                    a = (p_idx * 2 * math.pi) / petals
                    px = math.cos(a) * (r_petal * 0.5)
                    py = math.sin(a) * (r_petal * 0.5)
                    path.addEllipse(QPointF(px, py), r_petal * 0.55, r_petal * 0.55)
                painter.drawPath(path)
            else:
                painter.drawEllipse(QPointF(0, 0), size / 2.0, size / 2.0)

            painter.restore()

        painter.restore()


class CappuccinoBackgroundPainter:
    def __init__(self):
        rng = random.Random(101)
        self.blobs = []
        for _ in range(16):
            self.blobs.append({
                "x_rel": rng.uniform(0.05, 0.95),
                "y_rel": rng.uniform(0.05, 0.95),
                "rx": rng.uniform(90, 220),
                "ry": rng.uniform(60, 140),
                "opacity": rng.uniform(0.18, 0.32)
            })

    def draw(self, painter: QPainter, rect: QRectF):
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, True)
        grad = QLinearGradient(0, 0, rect.width() * 0.4, rect.height())
        grad.setColorAt(0.0, QColor("#F5EBE1"))
        grad.setColorAt(0.35, QColor("#E8D8C8"))
        grad.setColorAt(0.70, QColor("#DCC7B5"))
        grad.setColorAt(1.0, QColor("#E4D3C2"))
        painter.fillRect(rect, grad)

        w = rect.width()
        h = rect.height()
        for b in self.blobs:
            cx = b["x_rel"] * w
            cy = b["y_rel"] * h
            rx = b["rx"]
            ry = b["ry"]
            alpha = int(b["opacity"] * 255)
            radial = QRadialGradient(cx, cy, rx)
            radial.setColorAt(0.0, QColor(255, 255, 255, alpha))
            radial.setColorAt(0.65, QColor(255, 255, 255, int(alpha * 0.4)))
            radial.setColorAt(1.0, QColor(255, 255, 255, 0))
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(radial))
            painter.drawEllipse(QPointF(cx, cy), rx, ry)
        painter.restore()


class LavenderBackgroundPainter:
    def __init__(self):
        rng = random.Random(202)
        self.blobs = []
        for _ in range(16):
            self.blobs.append({
                "x_rel": rng.uniform(0.05, 0.95),
                "y_rel": rng.uniform(0.05, 0.95),
                "rx": rng.uniform(90, 220),
                "ry": rng.uniform(60, 140),
                "opacity": rng.uniform(0.18, 0.32)
            })

    def draw(self, painter: QPainter, rect: QRectF):
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, True)
        grad = QLinearGradient(0, 0, rect.width() * 0.4, rect.height())
        grad.setColorAt(0.0, QColor("#F3E8FF"))
        grad.setColorAt(0.35, QColor("#E9D5FF"))
        grad.setColorAt(0.70, QColor("#DDD6FE"))
        grad.setColorAt(1.0, QColor("#E0E7FF"))
        painter.fillRect(rect, grad)

        w = rect.width()
        h = rect.height()
        for b in self.blobs:
            cx = b["x_rel"] * w
            cy = b["y_rel"] * h
            rx = b["rx"]
            ry = b["ry"]
            alpha = int(b["opacity"] * 255)
            radial = QRadialGradient(cx, cy, rx)
            radial.setColorAt(0.0, QColor(255, 255, 255, alpha))
            radial.setColorAt(0.65, QColor(255, 255, 255, int(alpha * 0.4)))
            radial.setColorAt(1.0, QColor(255, 255, 255, 0))
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(radial))
            painter.drawEllipse(QPointF(cx, cy), rx, ry)
        painter.restore()
