import os
import json
from PySide6.QtCore import Qt, QSettings, QStandardPaths, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QLineEdit, QTextEdit, QFileDialog, QRadioButton, QButtonGroup,
    QGroupBox, QFrame, QStackedWidget, QListWidget, QListWidgetItem,
    QScrollArea, QMessageBox, QWidget, QInputDialog
)
from ui.themes import (
    THEME_LIGHT, THEME_FEMININE, THEME_CAPPUCCINO, THEME_LAVENDER, get_app_icon
)
from core.updater import (
    CURRENT_VERSION, CheckUpdateThread, DownloadUpdateThread, restart_and_replace
)
from core.database import DatabaseManager


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

    # -------------------------------------------------------------------------
    # Реквизиты АУ по умолчанию
    # -------------------------------------------------------------------------
    @property
    def manager_fio(self) -> str:
        return self.settings.value("manager_fio", "Гусарова Ксения Андреевна")

    @manager_fio.setter
    def manager_fio(self, val: str):
        self.settings.setValue("manager_fio", val)

    @property
    def manager_phone(self) -> str:
        return self.settings.value("manager_phone", "+7 (913) 989-01-63")

    @manager_phone.setter
    def manager_phone(self, val: str):
        self.settings.setValue("manager_phone", val)

    @property
    def manager_email(self) -> str:
        return self.settings.value("manager_email", "kseniya_gusarova@mail.ru")

    @manager_email.setter
    def manager_email(self, val: str):
        self.settings.setValue("manager_email", val)

    @property
    def manager_inn(self) -> str:
        return self.settings.value("manager_inn", "380470431942")

    @manager_inn.setter
    def manager_inn(self, val: str):
        self.settings.setValue("manager_inn", val)

    @property
    def manager_snils(self) -> str:
        return self.settings.value("manager_snils", "136-556-599 95")

    @manager_snils.setter
    def manager_snils(self, val: str):
        self.settings.setValue("manager_snils", val)

    @property
    def manager_corr_address(self) -> str:
        return self.settings.value("manager_corr_address", "630007, г. Новосибирск, а/я 1")

    @manager_corr_address.setter
    def manager_corr_address(self, val: str):
        self.settings.setValue("manager_corr_address", val)


class SettingsDialog(QDialog):
    """
    Модальное окно настроек со структурированным боковым меню (сайдбаром):
    1. Основные / Сборка отчёта
    2. Реквизиты АУ
    3. Регионы и ведомства
    """
    settings_saved = Signal()
    backup_restored = Signal()

    def __init__(self, parent=None, db_manager: DatabaseManager = None):
        super().__init__(parent)
        self.setWindowTitle("Настройки — Арбитрум")
        self.setWindowIcon(get_app_icon())
        self.setWindowModality(Qt.ApplicationModal)
        self.resize(780, 560)
        self.setMinimumSize(700, 480)

        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
        self.app_settings = AppSettings()
        self.db_manager = db_manager or DatabaseManager()
        from core.database import get_regions_json_path
        self.regions_file_path = get_regions_json_path()
        self.regions_data = {}
        self._load_regions_from_file()

        self._init_ui()
        self._load_values()

    def _load_regions_from_file(self):
        if os.path.exists(self.regions_file_path):
            try:
                with open(self.regions_file_path, "r", encoding="utf-8") as f:
                    self.regions_data = json.load(f)
            except Exception:
                self.regions_data = {}

    def _save_regions_to_file(self):
        try:
            with open(self.regions_file_path, "w", encoding="utf-8") as f:
                json.dump(self.regions_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            QMessageBox.warning(self, "Ошибка сохранения", f"Не удалось сохранить regions.json:\n{e}")

    def _init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Main horizontal area: Left Sidebar + Right Stacked Pages
        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # -------------------------------------------------------------
        # 1. Left Sidebar
        # -------------------------------------------------------------
        self.sidebar_frame = QFrame(self)
        self.sidebar_frame.setObjectName("settingsSidebar")
        self.sidebar_frame.setFixedWidth(200)

        sidebar_layout = QVBoxLayout(self.sidebar_frame)
        sidebar_layout.setContentsMargins(12, 16, 12, 16)
        sidebar_layout.setSpacing(6)

        title_lbl = QLabel("Настройки")
        title_lbl.setObjectName("headerTitle")
        title_lbl.setStyleSheet("font-size: 15px; font-weight: 700; padding-bottom: 8px;")
        sidebar_layout.addWidget(title_lbl)

        self.nav_btns = []
        tab_names = [
            ("Основные / Отчёт", 0),
            ("Реквизиты АУ", 1),
            ("Регионы и ведомства", 2),
            ("Резервные копии", 3),
            ("Обновления", 4)
        ]
        for name, idx in tab_names:
            btn = QPushButton(name, self.sidebar_frame)
            btn.setObjectName("settingsNavButton")
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked=False, i=idx: self._switch_tab(i))
            sidebar_layout.addWidget(btn)
            self.nav_btns.append(btn)

        sidebar_layout.addStretch()
        content_layout.addWidget(self.sidebar_frame)

        # -------------------------------------------------------------
        # 2. Right Stacked Pages
        # -------------------------------------------------------------
        self.pages_stack = QStackedWidget(self)
        self.pages_stack.setObjectName("settingsStack")

        # Page 0: General & Report
        self.pages_stack.addWidget(self._create_general_page())

        # Page 1: Manager Requisites
        self.pages_stack.addWidget(self._create_manager_page())

        # Page 2: Regions & Agencies
        self.pages_stack.addWidget(self._create_regions_page())

        # Page 3: Backup & Restore
        self.pages_stack.addWidget(self._create_backup_page())

        # Page 4: Updates
        self.pages_stack.addWidget(self._create_updates_page())

        content_layout.addWidget(self.pages_stack, stretch=1)
        root_layout.addLayout(content_layout, stretch=1)

        # -------------------------------------------------------------
        # 3. Bottom Button Bar (Сохранить / Отмена)
        # -------------------------------------------------------------
        bottom_bar = QFrame(self)
        bottom_bar.setObjectName("dialogBottomBar")
        bottom_layout = QHBoxLayout(bottom_bar)
        bottom_layout.setContentsMargins(18, 10, 18, 10)
        bottom_layout.setSpacing(10)

        bottom_layout.addStretch()

        cancel_btn = QPushButton("Отмена", bottom_bar)
        cancel_btn.setObjectName("secondaryButton")
        cancel_btn.setFixedHeight(34)
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)
        bottom_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Сохранить", bottom_bar)
        save_btn.setObjectName("primaryButton")
        save_btn.setFixedHeight(34)
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.clicked.connect(self._save_values)
        bottom_layout.addWidget(save_btn)

        root_layout.addWidget(bottom_bar)

        self._switch_tab(0)

    def _switch_tab(self, index: int):
        self.pages_stack.setCurrentIndex(index)
        for i, btn in enumerate(self.nav_btns):
            btn.setProperty("active", i == index)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    # =========================================================================
    # Page 0: Основные / Сборка отчёта
    # =========================================================================
    def _create_general_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        # Output Dir
        dir_group = QGroupBox("Папка для сохранения готовых отчётов")
        dir_layout = QVBoxLayout(dir_group)
        dir_layout.setContentsMargins(14, 12, 14, 12)
        dir_layout.setSpacing(8)

        dir_input_layout = QHBoxLayout()
        dir_input_layout.setSpacing(8)
        self.dir_edit = QLineEdit()
        self.dir_edit.setFixedHeight(34)
        dir_input_layout.addWidget(self.dir_edit, stretch=1)

        self.browse_btn = QPushButton("Обзор...")
        self.browse_btn.setObjectName("secondaryButton")
        self.browse_btn.setFixedHeight(34)
        self.browse_btn.setCursor(Qt.PointingHandCursor)
        self.browse_btn.clicked.connect(self._browse_dir)
        dir_input_layout.addWidget(self.browse_btn)
        dir_layout.addLayout(dir_input_layout)
        layout.addWidget(dir_group)

        # Output Format
        fmt_group = QGroupBox("Формат выходного файла")
        fmt_layout = QHBoxLayout(fmt_group)
        fmt_layout.setContentsMargins(14, 10, 14, 10)
        fmt_layout.setSpacing(20)

        self.fmt_btn_group = QButtonGroup(self)
        self.pdf_radio = QRadioButton("Формат PDF")
        self.docx_radio = QRadioButton("Формат Word")
        self.fmt_btn_group.addButton(self.pdf_radio, 1)
        self.fmt_btn_group.addButton(self.docx_radio, 2)
        fmt_layout.addWidget(self.pdf_radio)
        fmt_layout.addWidget(self.docx_radio)
        fmt_layout.addStretch()
        self.pdf_radio.toggled.connect(self._on_format_changed)
        layout.addWidget(fmt_group)

        # Layout Mode
        self.mode_group = QGroupBox("Режим компоновки страниц")
        mode_layout = QVBoxLayout(self.mode_group)
        mode_layout.setContentsMargins(14, 10, 14, 10)
        mode_layout.setSpacing(6)

        self.mode_btn_group = QButtonGroup(self)
        self.standard_radio = QRadioButton("По одной странице на лист")
        self.twoup_radio = QRadioButton("По две страницы на листе A4")
        self.mode_btn_group.addButton(self.standard_radio, 1)
        self.mode_btn_group.addButton(self.twoup_radio, 2)
        mode_layout.addWidget(self.standard_radio)
        mode_layout.addWidget(self.twoup_radio)
        layout.addWidget(self.mode_group)

        # Themes (2x2 Grid)
        theme_group = QGroupBox("Тема оформления")
        theme_grid = QGridLayout(theme_group)
        theme_grid.setContentsMargins(14, 10, 14, 10)
        theme_grid.setHorizontalSpacing(20)
        theme_grid.setVerticalSpacing(8)

        self.theme_btn_group = QButtonGroup(self)
        self.light_radio = QRadioButton("Светлая (классическая)")
        self.fem_radio = QRadioButton("Розовая")
        self.cap_radio = QRadioButton("Капучино")
        self.lav_radio = QRadioButton("Лаванда")
        self.theme_btn_group.addButton(self.light_radio, 1)
        self.theme_btn_group.addButton(self.fem_radio, 2)
        self.theme_btn_group.addButton(self.cap_radio, 3)
        self.theme_btn_group.addButton(self.lav_radio, 4)

        theme_grid.addWidget(self.light_radio, 0, 0)
        theme_grid.addWidget(self.fem_radio, 0, 1)
        theme_grid.addWidget(self.cap_radio, 1, 0)
        theme_grid.addWidget(self.lav_radio, 1, 1)
        layout.addWidget(theme_group)

        layout.addStretch()
        return page

    # =========================================================================
    # Page 1: Реквизиты АУ по умолчанию
    # =========================================================================
    def _create_manager_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        mgr_group = QGroupBox("Реквизиты арбитражного управляющего")
        form_layout = QVBoxLayout(mgr_group)
        form_layout.setContentsMargins(14, 12, 14, 12)
        form_layout.setSpacing(8)

        row1 = QHBoxLayout()
        v_fio = QVBoxLayout()
        v_fio.setSpacing(3)
        lbl_fio = QLabel("ФИО управляющего:")
        lbl_fio.setStyleSheet("font-size: 11px; color: #64748B;")
        self.edit_mgr_fio = QLineEdit()
        v_fio.addWidget(lbl_fio)
        v_fio.addWidget(self.edit_mgr_fio)
        row1.addLayout(v_fio, stretch=3)

        v_phone = QVBoxLayout()
        v_phone.setSpacing(3)
        lbl_phone = QLabel("Телефон:")
        lbl_phone.setStyleSheet("font-size: 11px; color: #64748B;")
        self.edit_mgr_phone = QLineEdit()
        v_phone.addWidget(lbl_phone)
        v_phone.addWidget(self.edit_mgr_phone)
        row1.addLayout(v_phone, stretch=2)
        form_layout.addLayout(row1)

        row2 = QHBoxLayout()
        v_email = QVBoxLayout()
        v_email.setSpacing(3)
        lbl_email = QLabel("Электронная почта:")
        lbl_email.setStyleSheet("font-size: 11px; color: #64748B;")
        self.edit_mgr_email = QLineEdit()
        v_email.addWidget(lbl_email)
        v_email.addWidget(self.edit_mgr_email)
        row2.addLayout(v_email)

        v_inn = QVBoxLayout()
        v_inn.setSpacing(3)
        lbl_inn = QLabel("ИНН:")
        lbl_inn.setStyleSheet("font-size: 11px; color: #64748B;")
        self.edit_mgr_inn = QLineEdit()
        v_inn.addWidget(lbl_inn)
        v_inn.addWidget(self.edit_mgr_inn)
        row2.addLayout(v_inn)

        v_snils = QVBoxLayout()
        v_snils.setSpacing(3)
        lbl_snils = QLabel("СНИЛС:")
        lbl_snils.setStyleSheet("font-size: 11px; color: #64748B;")
        self.edit_mgr_snils = QLineEdit()
        v_snils.addWidget(lbl_snils)
        v_snils.addWidget(self.edit_mgr_snils)
        row2.addLayout(v_snils)
        form_layout.addLayout(row2)

        v_addr = QVBoxLayout()
        v_addr.setSpacing(3)
        lbl_addr = QLabel("Почтовый адрес для корреспонденции:")
        lbl_addr.setStyleSheet("font-size: 11px; color: #64748B;")
        self.edit_mgr_addr = QLineEdit()
        v_addr.addWidget(lbl_addr)
        v_addr.addWidget(self.edit_mgr_addr)
        form_layout.addLayout(v_addr)

        layout.addWidget(mgr_group)

        layout.addStretch()
        return page

    # =========================================================================
    # Page 2: Регионы и ведомства
    # =========================================================================
    def _create_regions_page(self) -> QWidget:
        page = QWidget()
        layout = QHBoxLayout(page)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(14)

        # Левая колонка: Список регионов + кнопка добавления
        left_col = QVBoxLayout()
        left_col.setSpacing(8)

        lbl_reg = QLabel("Регионы в справочнике:")
        lbl_reg.setStyleSheet("font-size: 12px; font-weight: 600; color: #475569;")
        left_col.addWidget(lbl_reg)

        self.regions_list = QListWidget()
        self.regions_list.setObjectName("regionsListWidget")
        self.regions_list.setFixedWidth(220)
        self.regions_list.currentRowChanged.connect(self._on_region_selected)
        left_col.addWidget(self.regions_list, stretch=1)

        btn_add_reg = QPushButton("Добавить регион")
        btn_add_reg.setObjectName("secondaryButton")
        btn_add_reg.setFixedHeight(34)
        btn_add_reg.setCursor(Qt.PointingHandCursor)
        btn_add_reg.clicked.connect(self._on_add_region)
        left_col.addWidget(btn_add_reg)

        layout.addLayout(left_col)

        # Правая колонка: Детали выбранного региона (Скроллируемая форма)
        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setFrameShape(QFrame.NoFrame)

        self.region_detail_widget = QWidget()
        self.region_form_layout = QVBoxLayout(self.region_detail_widget)
        self.region_form_layout.setContentsMargins(10, 4, 16, 12)
        self.region_form_layout.setSpacing(12)

        # Название и склонение
        row_names = QHBoxLayout()
        row_names.setSpacing(10)

        v_reg_name = QVBoxLayout()
        v_reg_name.setSpacing(4)
        lbl_rname = QLabel("Название региона:")
        lbl_rname.setStyleSheet("font-size: 11px; color: #64748B; font-weight: 600;")
        self.edit_reg_name = QLineEdit()
        self.edit_reg_name.setFixedHeight(32)
        v_reg_name.addWidget(lbl_rname)
        v_reg_name.addWidget(self.edit_reg_name)
        row_names.addLayout(v_reg_name, stretch=3)

        v_reg_adj = QVBoxLayout()
        v_reg_adj.setSpacing(4)
        lbl_radj = QLabel("В родительном падеже (кого? чего?):")
        lbl_radj.setStyleSheet("font-size: 11px; color: #64748B; font-weight: 600;")
        self.edit_reg_adj = QLineEdit()
        self.edit_reg_adj.setFixedHeight(32)
        v_reg_adj.addWidget(lbl_radj)
        v_reg_adj.addWidget(self.edit_reg_adj)
        row_names.addLayout(v_reg_adj, stretch=2)
        self.region_form_layout.addLayout(row_names)

        # Ключевые слова
        v_kw = QVBoxLayout()
        v_kw.setSpacing(4)
        lbl_kw = QLabel("Ключевые слова для автоопределения (через запятую):")
        lbl_kw.setStyleSheet("font-size: 11px; color: #64748B; font-weight: 600;")
        self.edit_reg_keywords = QLineEdit()
        self.edit_reg_keywords.setFixedHeight(32)
        v_kw.addWidget(lbl_kw)
        v_kw.addWidget(self.edit_reg_keywords)
        self.region_form_layout.addLayout(v_kw)

        # Города для подсказок
        v_cities = QVBoxLayout()
        v_cities.setSpacing(4)
        lbl_cit = QLabel("Города региона для подсказок (через запятую):")
        lbl_cit.setStyleSheet("font-size: 11px; color: #64748B; font-weight: 600;")
        self.edit_reg_cities = QLineEdit()
        self.edit_reg_cities.setFixedHeight(32)
        v_cities.addWidget(lbl_cit)
        v_cities.addWidget(self.edit_reg_cities)
        self.region_form_layout.addLayout(v_cities)

        # Адреса ведомств региона
        lbl_ag = QLabel("Адреса ведомств региона (для запросов):")
        lbl_ag.setStyleSheet("font-size: 12px; color: #0369A1; font-weight: 700; margin-top: 10px; margin-bottom: 2px;")
        self.region_form_layout.addWidget(lbl_ag)

        self.agency_fields = {}
        agency_labels = [
            ("sfr", "СФР (Социальный фонд):"),
            ("gibdd", "ГИБДД:"),
            ("zags", "Управление ЗАГС:"),
            ("ifns", "ИФНС (Налоговая):"),
            ("fssp", "ФССП (Судебные приставы):"),
            ("admin", "Администрация города / мэрия:"),
            ("bti", "БТИ / Центр кадастровой оценки:"),
            ("gims", "ГИМС МЧС:"),
            ("gostekhnadzor", "Гостехнадзор:"),
            ("rosgvardiya", "Росгвардия:"),
            ("rosreestr", "Росреестр:"),
            ("rosimushchestvo", "Росимущество:"),
            ("uvm", "УВМ (Управление по вопросам миграции):"),
        ]

        for code, label_text in agency_labels:
            v_ag = QVBoxLayout()
            v_ag.setSpacing(4)
            lbl = QLabel(label_text)
            lbl.setStyleSheet("font-size: 11px; color: #475569; font-weight: 600;")
            edit = QTextEdit()
            edit.setFixedHeight(48)
            edit.setLineWrapMode(QTextEdit.WidgetWidth)
            edit.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            edit.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            edit.textChanged.connect(lambda e=edit: self._auto_resize_text_edit(e))
            v_ag.addWidget(lbl)
            v_ag.addWidget(edit)
            self.region_form_layout.addLayout(v_ag)
            self.agency_fields[code] = edit

        right_scroll.setWidget(self.region_detail_widget)
        layout.addWidget(right_scroll, stretch=1)

        self._populate_regions_list()
        return page

    def _auto_resize_text_edit(self, edit: QTextEdit):
        doc = edit.document()
        doc_height = int(doc.size().height()) + 14
        target_height = max(44, min(doc_height, 160))
        if edit.height() != target_height:
            edit.setFixedHeight(target_height)

    def _populate_regions_list(self):
        self.regions_list.blockSignals(True)
        self.regions_list.clear()
        self.region_keys = list(self.regions_data.keys())
        for k in self.region_keys:
            reg = self.regions_data[k]
            name = reg.get("name", k)
            self.regions_list.addItem(name)
        self.regions_list.blockSignals(False)
        if self.region_keys:
            self.regions_list.setCurrentRow(0)
            self._display_region(self.region_keys[0])

    def _on_region_selected(self, row: int):
        if 0 <= row < len(self.region_keys):
            # Save previous if needed or load
            reg_key = self.region_keys[row]
            self._display_region(reg_key)

    def _display_region(self, reg_key: str):
        reg = self.regions_data.get(reg_key, {})
        self.current_selected_reg_key = reg_key

        self.edit_reg_name.setText(reg.get("name", ""))
        self.edit_reg_adj.setText(reg.get("region_adj", ""))
        self.edit_reg_keywords.setText(", ".join(reg.get("keywords", [])))

        cities_names = [c.get("name", "") for c in reg.get("cities", []) if c.get("name")]
        self.edit_reg_cities.setText(", ".join(cities_names))

        agencies = reg.get("agencies", {})
        for code, edit in self.agency_fields.items():
            edit.setPlainText(agencies.get(code, ""))
            self._auto_resize_text_edit(edit)

    def _save_current_displayed_region(self):
        if not hasattr(self, "current_selected_reg_key") or not self.current_selected_reg_key:
            return
        reg_key = self.current_selected_reg_key
        if reg_key not in self.regions_data:
            self.regions_data[reg_key] = {}

        reg = self.regions_data[reg_key]
        reg["name"] = self.edit_reg_name.text().strip()
        reg["region_adj"] = self.edit_reg_adj.text().strip()

        kws = [k.strip() for k in self.edit_reg_keywords.text().split(",") if k.strip()]
        reg["keywords"] = kws

        cities_list = []
        raw_cities = [c.strip() for c in self.edit_reg_cities.text().split(",") if c.strip()]
        for cname in raw_cities:
            prefix = f"{reg['name']}, г. {cname}, "
            cities_list.append({"name": cname, "prefix": prefix})
        reg["cities"] = cities_list

        agencies = {}
        for code, edit in self.agency_fields.items():
            val = edit.toPlainText().strip()
            if val:
                agencies[code] = val
        reg["agencies"] = agencies

    def _on_add_region(self):
        name, ok = QInputDialog.getText(self, "Новый регион", "Введите название нового региона (например: Омская область):")
        if not ok or not name.strip():
            return
        name_clean = name.strip()
        # Generate simple ascii key
        key = f"region_{len(self.regions_data) + 1}"
        self.regions_data[key] = {
            "name": name_clean,
            "region_adj": name_clean,
            "keywords": [name_clean.lower()],
            "cities": [{"name": name_clean, "prefix": f"{name_clean}, "}],
            "agencies": {}
        }
        self._populate_regions_list()
        # Select the newly added region
        self.regions_list.setCurrentRow(len(self.region_keys) - 1)

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

        t = self.app_settings.theme
        if t == THEME_FEMININE:
            self.fem_radio.setChecked(True)
        elif t == THEME_CAPPUCCINO:
            self.cap_radio.setChecked(True)
        elif t == THEME_LAVENDER:
            self.lav_radio.setChecked(True)
        else:
            self.light_radio.setChecked(True)

        self._on_format_changed()

        # Manager
        self.edit_mgr_fio.setText(self.app_settings.manager_fio)
        self.edit_mgr_phone.setText(self.app_settings.manager_phone)
        self.edit_mgr_email.setText(self.app_settings.manager_email)
        self.edit_mgr_inn.setText(self.app_settings.manager_inn)
        self.edit_mgr_snils.setText(self.app_settings.manager_snils)
        self.edit_mgr_addr.setText(self.app_settings.manager_corr_address)

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

    # =========================================================================
    # Page 3: Резервное копирование и восстановление
    # =========================================================================
    def _create_backup_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(14)

        # 1. Информационная группа о текущей базе данных
        info_group = QGroupBox("Состояние базы данных")
        info_layout = QVBoxLayout(info_group)
        info_layout.setContentsMargins(16, 14, 16, 14)
        info_layout.setSpacing(8)

        self.lbl_db_path = QLabel()
        self.lbl_db_path.setWordWrap(True)
        self.lbl_db_path.setStyleSheet("font-size: 12px; color: #334155;")

        self.lbl_db_stats = QLabel()
        self.lbl_db_stats.setStyleSheet("font-size: 12px; color: #334155;")

        info_layout.addWidget(self.lbl_db_path)
        info_layout.addWidget(self.lbl_db_stats)

        # Кнопка открыть папку с базой
        btn_open_folder = QPushButton("Открыть папку с базой данных")
        btn_open_folder.setObjectName("secondaryButton")
        btn_open_folder.setFixedHeight(34)
        btn_open_folder.setCursor(Qt.PointingHandCursor)
        btn_open_folder.clicked.connect(self._on_open_db_folder)
        info_layout.addWidget(btn_open_folder)

        layout.addWidget(info_group)

        # 2. Управление резервными копиями
        backup_group = QGroupBox("Резервное копирование и перенос данных")
        b_layout = QVBoxLayout(backup_group)
        b_layout.setContentsMargins(16, 14, 16, 14)
        b_layout.setSpacing(12)

        desc_lbl = QLabel(
            "Вы можете в любой момент сохранить резервную копию всей картотеки должников в защищенный zip-архив "
            "для переноса на другой компьютер или восстановления в случае непредвиденных обстоятельств."
        )
        desc_lbl.setWordWrap(True)
        desc_lbl.setStyleSheet("font-size: 12px; color: #64748B; line-height: 1.4;")
        b_layout.addWidget(desc_lbl)

        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(12)

        self.btn_create_backup = QPushButton("Создать резервную копию...")
        self.btn_create_backup.setObjectName("secondaryButton")
        self.btn_create_backup.setFixedHeight(34)
        self.btn_create_backup.setCursor(Qt.PointingHandCursor)
        self.btn_create_backup.clicked.connect(self._on_create_backup)
        buttons_layout.addWidget(self.btn_create_backup)

        self.btn_restore_backup = QPushButton("Восстановить из копии...")
        self.btn_restore_backup.setObjectName("secondaryButton")
        self.btn_restore_backup.setFixedHeight(34)
        self.btn_restore_backup.setCursor(Qt.PointingHandCursor)
        self.btn_restore_backup.clicked.connect(self._on_restore_backup)
        buttons_layout.addWidget(self.btn_restore_backup)

        buttons_layout.addStretch()
        b_layout.addLayout(buttons_layout)

        layout.addWidget(backup_group)
        layout.addStretch()

        self._refresh_db_stats()
        return page

    def _refresh_db_stats(self):
        stats = self.db_manager.get_stats()
        path = stats.get("db_path", "")
        size = stats.get("size_bytes", 0)
        cnt = stats.get("debtor_count", 0)

        size_kb = size / 1024.0
        size_str = f"{size_kb:.1f} КБ" if size_kb < 1024 else f"{(size_kb / 1024.0):.2f} МБ"

        self.lbl_db_path.setText(f"<b>Файл базы данных:</b><br>{path}")
        self.lbl_db_stats.setText(f"<b>Записей в картотеке:</b> {cnt} &nbsp;&nbsp;|&nbsp;&nbsp; <b>Размер файла:</b> {size_str}")

    def _on_open_db_folder(self):
        stats = self.db_manager.get_stats()
        db_dir = os.path.dirname(stats.get("db_path", ""))
        if os.path.isdir(db_dir):
            try:
                os.startfile(db_dir)
            except Exception as e:
                QMessageBox.warning(self, "Ошибка", f"Не удалось открыть папку:\n{e}")
        else:
            QMessageBox.information(self, "Папка отсутствует", "Папка базы данных ещё не создана.")

    def _on_create_backup(self):
        import datetime
        now_str = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
        default_filename = f"Резервная_копия_Арбитрум_{now_str}.zip"
        default_dir = os.path.join(get_desktop_dir(), default_filename)

        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить резервную копию",
            default_dir,
            "Архивы ZIP (*.zip)"
        )
        if not save_path:
            return

        try:
            self.db_manager.create_backup(save_path)
            QMessageBox.information(
                self,
                "Резервная копия создана",
                f"Резервная копия картотеки должников успешно сохранена в файл:\n\n{save_path}"
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Ошибка создания копии",
                f"Не удалось создать резервную копию:\n{e}"
            )

    def _on_restore_backup(self):
        zip_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите файл резервной копии",
            get_desktop_dir(),
            "Архивы ZIP (*.zip)"
        )
        if not zip_path:
            return

        box = QMessageBox(self)
        box.setWindowTitle("Подтверждение восстановления")
        box.setIcon(QMessageBox.Warning)
        box.setText(
            "Внимание! Восстановление из резервной копии заменит текущую картотеку должников "
            "данными из выбранного архива.\n\n"
            "Вы уверены, что хотите продолжить?"
        )
        btn_yes = box.addButton("Да, восстановить", QMessageBox.YesRole)
        btn_no = box.addButton("Отмена", QMessageBox.NoRole)
        box.setDefaultButton(btn_no)
        box.exec()

        if box.clickedButton() != btn_yes:
            return

        try:
            restored_count = self.db_manager.restore_backup(zip_path)
            self._refresh_db_stats()
            self.backup_restored.emit()
            QMessageBox.information(
                self,
                "Восстановление завершено",
                f"База данных успешно восстановлена!\n\nВосстановлено записей должников: {restored_count}"
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Ошибка восстановления",
                f"Не удалось восстановить базу данных из архива:\n{e}"
            )

    def _on_create_backup(self):
        import datetime
        now_str = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
        default_filename = f"Резервная_копия_Арбитрум_{now_str}.zip"
        default_dir = os.path.join(get_desktop_dir(), default_filename)

        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить резервную копию",
            default_dir,
            "Архивы ZIP (*.zip)"
        )
        if not save_path:
            return

        try:
            self.db_manager.create_backup(save_path)
            QMessageBox.information(
                self,
                "Резервная копия создана",
                f"Резервная копия картотеки должников успешно сохранена в файл:\n\n{save_path}"
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Ошибка создания копии",
                f"Не удалось создать резервную копию:\n{e}"
            )

    def _on_restore_backup(self):
        zip_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите файл резервной копии",
            get_desktop_dir(),
            "Архивы ZIP (*.zip)"
        )
        if not zip_path:
            return

        box = QMessageBox(self)
        box.setWindowTitle("Подтверждение восстановления")
        box.setIcon(QMessageBox.Warning)
        box.setText(
            "Внимание! Восстановление из резервной копии заменит текущую картотеку должников "
            "данными из выбранного архива.\n\n"
            "Вы уверены, что хотите продолжить?"
        )
        btn_yes = box.addButton("Да, восстановить", QMessageBox.YesRole)
        btn_no = box.addButton("Отмена", QMessageBox.NoRole)
        box.setDefaultButton(btn_no)
        box.exec()

        if box.clickedButton() != btn_yes:
            return

        try:
            restored_count = self.db_manager.restore_backup(zip_path)
            self._refresh_db_stats()
            self.backup_restored.emit()
            QMessageBox.information(
                self,
                "Восстановление завершено",
                f"База данных успешно восстановлена!\n\nВосстановлено записей должников: {restored_count}"
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Ошибка восстановления",
                f"Не удалось восстановить базу данных из архива:\n{e}"
            )

    # =========================================================================
    # Page 4: Обновления программы
    # =========================================================================
    def _create_updates_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(14)

        upd_group = QGroupBox("Обновление системы Арбитрум")
        g_layout = QVBoxLayout(upd_group)
        g_layout.setContentsMargins(16, 14, 16, 14)
        g_layout.setSpacing(10)

        # Version info
        row_ver = QHBoxLayout()
        lbl_v_title = QLabel("Текущая версия:")
        lbl_v_title.setStyleSheet("font-size: 13px; color: #64748B;")
        self.lbl_current_ver = QLabel(f"<b>{CURRENT_VERSION}</b>")
        self.lbl_current_ver.setStyleSheet("font-size: 13px; color: #0F172A;")
        row_ver.addWidget(lbl_v_title)
        row_ver.addWidget(self.lbl_current_ver)
        row_ver.addStretch()
        g_layout.addLayout(row_ver)

        # Status Label
        self.lbl_update_status = QLabel("Нажмите кнопку ниже для проверки наличия новой версии.")
        self.lbl_update_status.setWordWrap(True)
        self.lbl_update_status.setStyleSheet("color: #475569; font-size: 12px; padding: 4px 0;")
        g_layout.addWidget(self.lbl_update_status)

        # Check button
        btn_row = QHBoxLayout()
        self.btn_check_update = QPushButton("Проверить обновления", upd_group)
        self.btn_check_update.setObjectName("secondaryButton")
        self.btn_check_update.setCursor(Qt.PointingHandCursor)
        self.btn_check_update.setFixedHeight(34)
        self.btn_check_update.clicked.connect(self._start_check_update)
        btn_row.addWidget(self.btn_check_update)

        self.btn_apply_update = QPushButton("Обновить и перезапустить", upd_group)
        self.btn_apply_update.setObjectName("mainBuildButton")
        self.btn_apply_update.setCursor(Qt.PointingHandCursor)
        self.btn_apply_update.setFixedHeight(34)
        self.btn_apply_update.setVisible(False)
        self.btn_apply_update.clicked.connect(self._start_download_update)
        btn_row.addWidget(self.btn_apply_update)

        btn_row.addStretch()
        g_layout.addLayout(btn_row)

        # Release notes text
        self.notes_box = QTextEdit()
        self.notes_box.setReadOnly(True)
        self.notes_box.setPlaceholderText("Описание изменений нового релиза появится здесь...")
        self.notes_box.setMaximumHeight(160)
        self.notes_box.setVisible(False)
        g_layout.addWidget(self.notes_box)

        layout.addWidget(upd_group)
        layout.addStretch()

        self._update_download_url = ""
        self._download_temp_file = ""
        return page

    def _start_check_update(self):
        self.btn_check_update.setEnabled(False)
        self.btn_check_update.setText("Проверка...")
        self.lbl_update_status.setText("Связываемся с сервером обновлений...")
        self.lbl_update_status.setStyleSheet("color: #2563EB; font-size: 12px;")
        self.btn_apply_update.setVisible(False)
        self.notes_box.setVisible(False)

        self.check_thread = CheckUpdateThread()
        self.check_thread.check_finished.connect(self._on_check_update_finished)
        self.check_thread.check_failed.connect(self._on_check_update_failed)
        self.check_thread.start()

    def _on_check_update_finished(self, has_update: bool, new_ver: str, notes: str, download_url: str):
        self.btn_check_update.setEnabled(True)
        self.btn_check_update.setText("Проверить обновления")

        if has_update:
            self._update_download_url = download_url
            self.lbl_update_status.setText(f"Доступна новая версия: <b>{new_ver}</b>!")
            self.lbl_update_status.setStyleSheet("color: #16A34A; font-size: 13px;")
            self.notes_box.setPlainText(notes)
            self.notes_box.setVisible(True)
            if download_url:
                self.btn_apply_update.setVisible(True)
                self.btn_apply_update.setText(f"Скачать и обновить до {new_ver}")
            else:
                self.lbl_update_status.setText(f"Доступна версия {new_ver}, но установочный файл ещё загружается разработчиком.")
        else:
            self.lbl_update_status.setText("У вас установлена самая последняя версия приложения.")
            self.lbl_update_status.setStyleSheet("color: #16A34A; font-size: 12px;")

    def _on_check_update_failed(self, error_msg: str):
        self.btn_check_update.setEnabled(True)
        self.btn_check_update.setText("Проверить обновления")
        self.lbl_update_status.setText(f"Не удалось проверить обновления: {error_msg}")
        self.lbl_update_status.setStyleSheet("color: #DC2626; font-size: 12px;")

    def _start_download_update(self):
        if not self._update_download_url:
            QMessageBox.warning(self, "Ошибка", "Ссылка для скачивания обновления не найдена.")
            return

        self.btn_apply_update.setEnabled(False)
        self.btn_check_update.setEnabled(False)
        self.lbl_update_status.setText("Подготовка к скачиванию...")
        self.lbl_update_status.setStyleSheet("color: #2563EB; font-size: 12px;")

        self.dl_thread = DownloadUpdateThread(self._update_download_url)
        self.dl_thread.progress.connect(self._on_download_progress)
        self.dl_thread.download_finished.connect(self._on_download_finished)
        self.dl_thread.download_failed.connect(self._on_download_failed)
        self.dl_thread.start()

    def _on_download_progress(self, percent: int, downloaded_mb: float, total_mb: float):
        if total_mb > 0:
            self.lbl_update_status.setText(f"Загрузка обновления: <b>{downloaded_mb:.1f} МБ</b> из <b>{total_mb:.1f} МБ</b> ({percent}%)")
        else:
            self.lbl_update_status.setText(f"Загрузка обновления: <b>{downloaded_mb:.1f} МБ</b>...")

    def _on_download_finished(self, temp_path: str):
        self.lbl_update_status.setText("Обновление скачано! Перезапуск приложения...")
        self.lbl_update_status.setStyleSheet("color: #16A34A; font-size: 12px; font-weight: bold;")
        try:
            restart_and_replace(temp_path)
        except RuntimeError as e:
            QMessageBox.information(
                self,
                "Обновление загружено",
                f"Файл обновления успешно сохранен:\n{temp_path}\n\n"
                "Так как программа запущена в режиме разработки (из исходного кода), "
                "автоматическая замена .exe пропущена."
            )
            self.btn_apply_update.setEnabled(True)
            self.btn_check_update.setEnabled(True)

    def _on_download_failed(self, err: str):
        self.btn_apply_update.setEnabled(True)
        self.btn_check_update.setEnabled(True)
        self.lbl_update_status.setText(f"Ошибка загрузки обновления: {err}")
        self.lbl_update_status.setStyleSheet("color: #DC2626; font-size: 12px;")

    def _save_values(self):
        # 1. General & Report
        self.app_settings.output_dir = self.dir_edit.text().strip()
        if self.fem_radio.isChecked():
            theme = THEME_FEMININE
        elif self.cap_radio.isChecked():
            theme = THEME_CAPPUCCINO
        elif self.lav_radio.isChecked():
            theme = THEME_LAVENDER
        else:
            theme = THEME_LIGHT
        self.app_settings.theme = theme
        self.app_settings.output_format = "docx" if self.docx_radio.isChecked() else "pdf"
        self.app_settings.layout_mode = "standard" if self.standard_radio.isChecked() else "2up"

        # 2. Manager requisites
        self.app_settings.manager_fio = self.edit_mgr_fio.text().strip()
        self.app_settings.manager_phone = self.edit_mgr_phone.text().strip()
        self.app_settings.manager_email = self.edit_mgr_email.text().strip()
        self.app_settings.manager_inn = self.edit_mgr_inn.text().strip()
        self.app_settings.manager_snils = self.edit_mgr_snils.text().strip()
        self.app_settings.manager_corr_address = self.edit_mgr_addr.text().strip()

        # 3. Save displayed region & file
        self._save_current_displayed_region()
        self._save_regions_to_file()

        self.settings_saved.emit()
        self.accept()
