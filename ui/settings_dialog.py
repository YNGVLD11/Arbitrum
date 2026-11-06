import os
from PySide6.QtCore import Qt, QSettings, QStandardPaths, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFileDialog, QRadioButton, QButtonGroup,
    QCheckBox, QGroupBox
)
from ui.themes import THEME_LIGHT, THEME_FEMININE, get_app_icon


def get_default_downloads_dir() -> str:
    path = QStandardPaths.writableLocation(QStandardPaths.DownloadLocation)
    if not path or not os.path.exists(path):
        path = os.path.join(os.path.expanduser("~"), "Downloads")
    return os.path.normpath(path)


def get_desktop_dir() -> str:
    user_profile = os.environ.get("USERPROFILE", "")
    candidates = [
        os.path.join(user_profile, "Desktop"),
        os.path.join(user_profile, "OneDrive", "Рабочий стол"),
        os.path.join(user_profile, "OneDrive", "Desktop"),
        os.path.join(user_profile, "Рабочий стол"),
        QStandardPaths.writableLocation(QStandardPaths.DesktopLocation)
    ]
    for c in candidates:
        if c and os.path.exists(c):
            return os.path.normpath(c)
    return os.path.normpath(user_profile)


class AppSettings:
    """
    Manages persistent user preferences via QSettings.
    """
    def __init__(self):
        self.settings = QSettings("ArbitrReportBuilder", "Settings")

    @property
    def output_dir(self) -> str:
        val = self.settings.value("output_dir", "")
        if not val or not os.path.exists(val):
            return get_default_downloads_dir()
        return os.path.normpath(val)

    @output_dir.setter
    def output_dir(self, val: str):
        self.settings.setValue("output_dir", val)

    @property
    def theme(self) -> str:
        return self.settings.value("theme", THEME_LIGHT)

    @theme.setter
    def theme(self, val: str):
        self.settings.setValue("theme", val)

    @property
    def new_sheet_for_landscape(self) -> bool:
        return self.settings.value("new_sheet_for_landscape", True, type=bool)

    @new_sheet_for_landscape.setter
    def new_sheet_for_landscape(self, val: bool):
        self.settings.setValue("new_sheet_for_landscape", val)

    @property
    def auto_open_file(self) -> bool:
        return self.settings.value("auto_open_file", False, type=bool)

    @auto_open_file.setter
    def auto_open_file(self, val: bool):
        self.settings.setValue("auto_open_file", val)


class SettingsDialog(QDialog):
    """
    Modal settings configuration window with guaranteed solid background,
    working window close button, and matching action buttons.
    """
    settings_saved = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Настройки")
        self.setWindowIcon(get_app_icon())
        self.setWindowModality(Qt.ApplicationModal)
        self.setFixedSize(520, 560)

        # Standard dialog window flags so close button '✕' works reliably on Windows
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)

        self.app_settings = AppSettings()

        self._init_ui()
        self._load_values()

    def closeEvent(self, event):
        self.reject()
        event.accept()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.reject()
        else:
            super().keyPressEvent(event)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # Title
        title_lbl = QLabel("⚙️ Настройки")
        title_lbl.setObjectName("headerTitle")
        title_lbl.setStyleSheet("font-size: 16px; font-weight: 700;")
        layout.addWidget(title_lbl)

        # 1. Output Directory Group
        dir_group = QGroupBox("Папка для сохранения готовых отчётов")
        dir_layout = QVBoxLayout(dir_group)
        dir_layout.setContentsMargins(14, 20, 14, 16)
        dir_layout.setSpacing(10)

        dir_input_layout = QHBoxLayout()
        dir_input_layout.setSpacing(8)

        self.dir_edit = QLineEdit()
        self.dir_edit.setFixedHeight(36)
        self.dir_edit.setPlaceholderText("Выберите папку...")
        dir_input_layout.addWidget(self.dir_edit, stretch=1)

        self.browse_btn = QPushButton("Обзор...")
        self.browse_btn.setFixedHeight(36)
        self.browse_btn.clicked.connect(self._browse_dir)
        dir_input_layout.addWidget(self.browse_btn)

        dir_layout.addLayout(dir_input_layout)
        dir_layout.addSpacing(4)

        # Quick location shortcuts
        quick_layout = QHBoxLayout()
        quick_layout.setSpacing(8)

        desktop_btn = QPushButton("🖥️ Рабочий стол")
        desktop_btn.setFixedHeight(28)
        desktop_btn.setStyleSheet("font-size: 11px; padding: 2px 10px;")
        desktop_btn.clicked.connect(lambda: self.dir_edit.setText(get_desktop_dir()))
        quick_layout.addWidget(desktop_btn)

        downloads_btn = QPushButton("📁 Загрузки")
        downloads_btn.setFixedHeight(28)
        downloads_btn.setStyleSheet("font-size: 11px; padding: 2px 10px;")
        downloads_btn.clicked.connect(lambda: self.dir_edit.setText(get_default_downloads_dir()))
        quick_layout.addWidget(downloads_btn)

        quick_layout.addStretch()
        dir_layout.addLayout(quick_layout)

        layout.addWidget(dir_group)

        # 2. Theme Selection Group
        theme_group = QGroupBox("Тема оформления")
        theme_layout = QVBoxLayout(theme_group)
        theme_layout.setContentsMargins(14, 18, 14, 14)
        theme_layout.setSpacing(12)

        self.theme_btn_group = QButtonGroup(self)

        # Titles WITHOUT extra helper text in parentheses
        self.light_radio = QRadioButton("☀️ Обычная светлая")
        self.theme_btn_group.addButton(self.light_radio, 1)
        theme_layout.addWidget(self.light_radio)

        self.fem_radio = QRadioButton("🌸 Феминная")
        self.theme_btn_group.addButton(self.fem_radio, 2)
        theme_layout.addWidget(self.fem_radio)

        layout.addWidget(theme_group)

        # 3. Automation Options
        opts_group = QGroupBox("Параметры сборки")
        opts_layout = QVBoxLayout(opts_group)
        opts_layout.setContentsMargins(14, 18, 14, 14)
        opts_layout.setSpacing(10)

        self.landscape_break_cb = QCheckBox("Начинать альбомные документы (реестры) с нового листа")
        opts_layout.addWidget(self.landscape_break_cb)

        self.auto_open_cb = QCheckBox("Автоматически открывать готовый PDF сразу после завершения")
        opts_layout.addWidget(self.auto_open_cb)

        layout.addWidget(opts_group)

        layout.addStretch()

        # Action Buttons: Cancel and Save with identical heights and vertical alignment
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        btn_layout.addStretch()

        cancel_btn = QPushButton("Отмена")
        cancel_btn.setFixedHeight(36)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Сохранить")
        save_btn.setObjectName("primaryButton")
        save_btn.setFixedHeight(36)
        save_btn.clicked.connect(self._save_values)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

    def _load_values(self):
        self.dir_edit.setText(self.app_settings.output_dir)
        if self.app_settings.theme == THEME_FEMININE:
            self.fem_radio.setChecked(True)
        else:
            self.light_radio.setChecked(True)
        self.landscape_break_cb.setChecked(self.app_settings.new_sheet_for_landscape)
        self.auto_open_cb.setChecked(self.app_settings.auto_open_file)

    def _browse_dir(self):
        curr = self.dir_edit.text().strip()
        if not curr or not os.path.isdir(curr):
            curr = get_default_downloads_dir()
        curr = os.path.normpath(curr)

        d = QFileDialog.getExistingDirectory(
            self,
            "Выберите папку для сохранения",
            curr
        )
        if d:
            self.dir_edit.setText(os.path.normpath(d))

    def _save_values(self):
        self.app_settings.output_dir = self.dir_edit.text().strip()
        self.app_settings.theme = THEME_FEMININE if self.fem_radio.isChecked() else THEME_LIGHT
        self.app_settings.new_sheet_for_landscape = self.landscape_break_cb.isChecked()
        self.app_settings.auto_open_file = self.auto_open_cb.isChecked()
        self.settings_saved.emit()
        self.accept()
