import os
from PySide6.QtCore import Qt, QSettings, QStandardPaths, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFileDialog, QRadioButton, QButtonGroup,
    QGroupBox
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
    def layout_mode(self) -> str:
        """'2up' (default) or 'standard'"""
        return self.settings.value("layout_mode", "2up")

    @layout_mode.setter
    def layout_mode(self, val: str):
        self.settings.setValue("layout_mode", val)

    @property
    def output_format(self) -> str:
        """'pdf' (default) or 'docx'"""
        return self.settings.value("output_format", "pdf")

    @output_format.setter
    def output_format(self, val: str):
        self.settings.setValue("output_format", val)

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
    Modal settings configuration window with layout mode, output format,
    theme and directory selections.
    """
    settings_saved = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Настройки")
        self.setWindowIcon(get_app_icon())
        self.setWindowModality(Qt.ApplicationModal)
        self.setFixedSize(520, 600)

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
        layout.setSpacing(14)

        # Title
        title_lbl = QLabel("⚙️ Настройки")
        title_lbl.setObjectName("headerTitle")
        title_lbl.setStyleSheet("font-size: 16px; font-weight: 700;")
        layout.addWidget(title_lbl)

        # 1. Output Directory Group
        dir_group = QGroupBox("Папка для сохранения готовых отчётов")
        dir_layout = QVBoxLayout(dir_group)
        dir_layout.setContentsMargins(16, 12, 16, 12)
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

        # 2. Output Format Group (PDF vs DOCX)
        fmt_group = QGroupBox("Формат выходного файла")
        fmt_layout = QHBoxLayout(fmt_group)
        fmt_layout.setContentsMargins(16, 12, 16, 12)
        fmt_layout.setSpacing(20)

        self.fmt_btn_group = QButtonGroup(self)
        self.pdf_radio = QRadioButton("📄 Формат PDF")
        self.docx_radio = QRadioButton("📝 Формат Word")
        self.fmt_btn_group.addButton(self.pdf_radio, 1)
        self.fmt_btn_group.addButton(self.docx_radio, 2)
        fmt_layout.addWidget(self.pdf_radio)
        fmt_layout.addWidget(self.docx_radio)
        fmt_layout.addStretch()
        self.pdf_radio.toggled.connect(self._on_format_changed)
        layout.addWidget(fmt_group)

        # 3. Layout Mode Group (1 страница vs 2 страницы на лист A4)
        self.mode_group = QGroupBox("Режим компоновки страниц")
        mode_layout = QVBoxLayout(self.mode_group)
        mode_layout.setContentsMargins(16, 12, 16, 12)
        mode_layout.setSpacing(10)

        self.mode_btn_group = QButtonGroup(self)
        self.standard_radio = QRadioButton("По одной странице на лист")
        self.twoup_radio = QRadioButton("По две страницы на листе A4")
        self.mode_btn_group.addButton(self.standard_radio, 1)
        self.mode_btn_group.addButton(self.twoup_radio, 2)
        mode_layout.addWidget(self.standard_radio)
        mode_layout.addWidget(self.twoup_radio)
        layout.addWidget(self.mode_group)

        # 4. Theme Selection Group
        theme_group = QGroupBox("Тема оформления")
        theme_layout = QVBoxLayout(theme_group)
        theme_layout.setContentsMargins(16, 12, 16, 12)
        theme_layout.setSpacing(10)

        self.theme_btn_group = QButtonGroup(self)
        self.light_radio = QRadioButton("☀️ Обычная светлая")
        self.fem_radio = QRadioButton("🌸 Феминная")
        self.theme_btn_group.addButton(self.light_radio, 1)
        self.theme_btn_group.addButton(self.fem_radio, 2)
        theme_layout.addWidget(self.light_radio)
        theme_layout.addWidget(self.fem_radio)
        layout.addWidget(theme_group)

        layout.addStretch()

        # Action Buttons
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

    def _on_format_changed(self):
        is_pdf = self.pdf_radio.isChecked()
        self.mode_group.setEnabled(is_pdf)
        if not is_pdf:
            self.standard_radio.setChecked(True)

    def _load_values(self):
        self.dir_edit.setText(self.app_settings.output_dir)

        if self.app_settings.output_format == "docx":
            self.docx_radio.setChecked(True)
        else:
            self.pdf_radio.setChecked(True)

        if self.app_settings.layout_mode == "standard":
            self.standard_radio.setChecked(True)
        else:
            self.twoup_radio.setChecked(True)

        if self.app_settings.theme == THEME_FEMININE:
            self.fem_radio.setChecked(True)
        else:
            self.light_radio.setChecked(True)

        self._on_format_changed()

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
        self.app_settings.output_format = "docx" if self.docx_radio.isChecked() else "pdf"
        self.app_settings.layout_mode = "standard" if self.standard_radio.isChecked() else "2up"
        self.settings_saved.emit()
        self.accept()
