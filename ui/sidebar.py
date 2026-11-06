from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFrame
)
from PySide6.QtGui import QIcon, QFont
from ui.themes import THEME_FEMININE, get_app_icon


class NavButton(QPushButton):
    """
    Sidebar Navigation Item Button with clean rounded pill style.
    """
    def __init__(self, text: str, page_index: int, parent=None):
        super().__init__(text, parent)
        self.page_index = page_index
        self.setFixedHeight(44)
        self.setCursor(Qt.PointingHandCursor)
        self.setObjectName("sidebarNavButton")
        self.setProperty("active", False)

    def set_active(self, active: bool):
        self.setProperty("active", active)
        self.style().unpolish(self)
        self.style().polish(self)


class Sidebar(QFrame):
    """
    Left Navigation Sidebar for switching between modules:
    - Сборка отчёта АУ
    - Генератор запросов
    """
    page_changed = Signal(int)
    settings_clicked = Signal()

    def __init__(self, theme: str = "light", parent=None):
        super().__init__(parent)
        self.theme = theme
        self.current_page = 0
        self.setObjectName("sidebarFrame")
        self.setFixedWidth(170)

        self._init_ui()
        self.set_theme(theme)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 16, 8, 16)
        layout.setSpacing(8)

        # Header: App Title "Арбитум" (without subtitle)
        header_layout = QVBoxLayout()
        header_layout.setSpacing(0)
        header_layout.setContentsMargins(2, 0, 2, 8)

        title_lbl = QLabel("Арбитум")
        title_lbl.setObjectName("sidebarTitle")
        title_font = QFont("Segoe UI", 16, QFont.Bold)
        title_lbl.setFont(title_font)
        title_lbl.setAlignment(Qt.AlignCenter)

        header_layout.addWidget(title_lbl)
        layout.addLayout(header_layout)

        # Divider
        divider = QFrame()
        divider.setObjectName("sidebarDivider")
        divider.setFrameShape(QFrame.HLine)
        divider.setFrameShadow(QFrame.Sunken)
        layout.addWidget(divider)
        layout.addSpacing(6)

        # Navigation Buttons
        self.btn_report = NavButton("Сборка отчёта АУ", 0, self)
        self.btn_report.clicked.connect(lambda: self._on_btn_clicked(0))
        layout.addWidget(self.btn_report)

        self.btn_inquiry = NavButton("Генератор запросов", 1, self)
        self.btn_inquiry.clicked.connect(lambda: self._on_btn_clicked(1))
        layout.addWidget(self.btn_inquiry)

        layout.addStretch()

        # Bottom Settings Button
        self.btn_settings = QPushButton("⚙️  Настройки", self)
        self.btn_settings.setObjectName("sidebarSettingsButton")
        self.btn_settings.setFixedHeight(40)
        self.btn_settings.setCursor(Qt.PointingHandCursor)
        self.btn_settings.clicked.connect(self.settings_clicked.emit)
        layout.addWidget(self.btn_settings)

        # Version label
        ver_lbl = QLabel("Версия 1.1.0")
        ver_lbl.setAlignment(Qt.AlignCenter)
        ver_lbl.setObjectName("sidebarVersion")
        layout.addWidget(ver_lbl)

        self._update_nav_selection()

    def set_current_page(self, page_index: int):
        self.current_page = page_index
        self._update_nav_selection()

    def _on_btn_clicked(self, page_index: int):
        if self.current_page != page_index:
            self.current_page = page_index
            self._update_nav_selection()
            self.page_changed.emit(page_index)

    def _update_nav_selection(self):
        self.btn_report.set_active(self.current_page == 0)
        self.btn_inquiry.set_active(self.current_page == 1)

    def set_theme(self, theme: str):
        self.theme = theme
        self._update_nav_selection()
