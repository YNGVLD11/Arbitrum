import os
import json
from PySide6.QtCore import Qt, Signal, QObject, QEvent, QPoint
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QCheckBox, QRadioButton, QButtonGroup, QScrollArea,
    QFrame, QFileDialog, QMessageBox, QProgressBar, QToolTip, QCompleter
)
from PySide6.QtGui import QCursor
from ui.themes import THEME_FEMININE
from core.court_parser import CourtParserWorker, parse_court_decision, inflect_fio, to_nomn_fio
from core.inquiry_generator import TEMPLATES_CONFIG, generate_inquiries
from core.database import DatabaseManager
from ui.progress_dialog import BuildProgressDialog
from ui.inquiry_success_dialog import InquirySuccessDialog


class _CompleterPopupFilter(QObject):
    """
    Event filter that forces the QCompleter popup list to always appear
    directly beneath the target QLineEdit.
    """
    def __init__(self, line_edit: QLineEdit, parent=None):
        super().__init__(parent)
        self.line_edit = line_edit

    def eventFilter(self, obj, event):
        res = super().eventFilter(obj, event)
        if event.type() in (QEvent.Show, QEvent.Resize):
            if self.line_edit and self.line_edit.isVisible():
                pos = self.line_edit.mapToGlobal(QPoint(0, self.line_edit.height() + 2))
                obj.move(pos)
        return res


class HintLineEdit(QLineEdit):
    """
    Enhanced QLineEdit that displays a tooltip hint directly under the mouse cursor
    on hover so users can easily identify what the field represents even when filled.
    """
    def __init__(self, placeholder: str = "", hint_text: str = "", parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self.hint_text = hint_text or placeholder
        self.setToolTip(self.hint_text)
        self.setObjectName("formLineEdit")

    def enterEvent(self, event):
        super().enterEvent(event)
        if self.hint_text:
            QToolTip.showText(QCursor.pos(), self.hint_text, self)

    def leaveEvent(self, event):
        super().leaveEvent(event)
        QToolTip.hideText()


class CreditorRowWidget(QWidget):
    """
    A single row in the dynamic creditors list:
    Name, Address, INN, and a Delete ('✕') button.
    """
    deleted = Signal(object)

    def __init__(self, name: str = "", address: str = "", inn: str = "", parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(6)

        name_str = "" if isinstance(name, bool) else str(name or "")
        addr_str = "" if isinstance(address, bool) else str(address or "")
        inn_str = "" if isinstance(inn, bool) else str(inn or "")

        self.edit_name = HintLineEdit("Наименование кредитора", "Наименование банка, МФО или организации", self)
        self.edit_name.setText(name_str)

        self.edit_addr = HintLineEdit("Адрес кредитора", "Юридический / почтовый адрес кредитора", self)
        self.edit_addr.setText(addr_str)

        self.edit_inn = HintLineEdit("ИНН", "ИНН кредитора", self)
        self.edit_inn.setText(inn_str)
        self.edit_inn.setFixedWidth(110)

        self.btn_del = QPushButton("✕", self)
        self.btn_del.setToolTip("Удалить кредитора")
        self.btn_del.setFixedSize(26, 26)
        self.btn_del.setObjectName("dangerButton")
        self.btn_del.setCursor(Qt.PointingHandCursor)
        self.btn_del.clicked.connect(lambda: self.deleted.emit(self))

        layout.addWidget(self.edit_name, stretch=3)
        layout.addWidget(self.edit_addr, stretch=4)
        layout.addWidget(self.edit_inn)
        layout.addWidget(self.btn_del)

    def get_data(self) -> dict:
        return {
            "name": self.edit_name.text().strip(),
            "address": self.edit_addr.text().strip(),
            "inn": self.edit_inn.text().strip()
        }


class DropArea(QFrame):
    file_dropped = Signal(str)
    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setObjectName("courtDropArea")
        self.setFixedHeight(75)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setAlignment(Qt.AlignCenter)

        self.label = QLabel("Перетащите решение или определение суда в формате PDF или Word\nили нажмите для выбора файла")
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setObjectName("dropAreaText")
        self.label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        layout.addWidget(self.label)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                ext = os.path.splitext(url.toLocalFile())[1].lower()
                if ext in [".pdf", ".docx", ".doc"]:
                    event.acceptProposedAction()
                    self.setProperty("dragOver", True)
                    self.style().unpolish(self)
                    self.style().polish(self)
                    return
        event.ignore()

    def dragLeaveEvent(self, event):
        self.setProperty("dragOver", False)
        self.style().unpolish(self)
        self.style().polish(self)

    def dropEvent(self, event):
        self.setProperty("dragOver", False)
        self.style().unpolish(self)
        self.style().polish(self)
        for url in event.mimeData().urls():
            fpath = url.toLocalFile()
            ext = os.path.splitext(fpath)[1].lower()
            if ext in [".pdf", ".docx", ".doc"]:
                self.file_dropped.emit(fpath)
                break

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class InquiryGeneratorPanel(QWidget):
    generation_requested = Signal()
    debtor_parsed = Signal(dict)

    def __init__(self, settings, db_manager: DatabaseManager = None, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.db_manager = db_manager or DatabaseManager()
        self.theme = settings.theme
        self.parser_worker = None
        self.creditor_rows: list[CreditorRowWidget] = []
        self._debtors_cache = []
        self._init_ui()
        self.refresh_debtors_list()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(12)

        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(18)

        # =====================================================================
        # LEFT CARD: Реквизиты дела и должника
        # =====================================================================
        self.left_card = QFrame()
        self.left_card.setObjectName("cardFrame")
        left_layout = QVBoxLayout(self.left_card)
        left_layout.setContentsMargins(16, 14, 16, 14)
        left_layout.setSpacing(10)

        card1_title = QLabel("Реквизиты дела и должника")
        card1_title.setObjectName("cardTitle")
        left_layout.addWidget(card1_title)

        # Выбор должника из картотеки (выпадающий список)
        debtor_select_layout = QVBoxLayout()
        debtor_select_layout.setSpacing(6)

        lbl_select_debtor = QLabel("Выбор должника из базы:")
        lbl_select_debtor.setStyleSheet("font-size: 12px; font-weight: 600; color: #475569;")
        debtor_select_layout.addWidget(lbl_select_debtor)

        self.debtor_combo = QComboBox(self)
        self.debtor_combo.setObjectName("debtorSelectorCombo")
        self.debtor_combo.setEditable(False)
        self.debtor_combo.setFixedHeight(40)
        self.debtor_combo.currentIndexChanged.connect(self._on_debtor_combo_selected)
        debtor_select_layout.addWidget(self.debtor_combo)

        left_layout.addLayout(debtor_select_layout)

        # Form Scroll Area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setObjectName("formScrollArea")

        form_widget = QWidget()
        form_layout = QVBoxLayout(form_widget)
        form_layout.setContentsMargins(0, 4, 6, 4)
        form_layout.setSpacing(6)

        # Section 1: Суд и дело
        form_layout.addWidget(self._make_section_header("Дело и суд"))
        
        row_court = QHBoxLayout()
        self.edit_case_no = self._make_input("Номер дела", "Номер арбитражного дела")
        self.edit_dec_date = self._make_input("Дата решения суда", "Дата судебного акта / решения")
        row_court.addWidget(self.edit_case_no, stretch=3)
        row_court.addWidget(self.edit_dec_date, stretch=2)
        form_layout.addLayout(row_court)

        self.edit_court_name = self._make_input("Наименование арбитражного суда", "Наименование арбитражного суда")
        form_layout.addWidget(self.edit_court_name)

        # Added field: Дата принятия заявления
        self.edit_petition_date = self._make_input("Дата принятия заявления", "Дата принятия заявления к производству судом (для расчета 3-летнего периода запроса сведений)")
        form_layout.addWidget(self.edit_petition_date)

        # Section 2: Должник
        form_layout.addSpacing(4)
        form_layout.addWidget(self._make_section_header("Данные должника"))
        
        row_fio = QHBoxLayout()
        self.edit_debtor_fio = self._make_input("ФИО должника", "ФИО должника (в именительном падеже)")
        self.edit_debtor_fio.textChanged.connect(self._on_debtor_name_changed)
        self.edit_debtor_fio_gen = self._make_input("ФИО должника в родительном падеже", "ФИО должника (в родительном падеже: кого?)")
        row_fio.addWidget(self.edit_debtor_fio)
        row_fio.addWidget(self.edit_debtor_fio_gen)
        form_layout.addLayout(row_fio)

        row_debtor_b = QHBoxLayout()
        self.edit_debtor_birth = self._make_input("Дата рождения", "Дата рождения должника")
        self.edit_debtor_place = self._make_input("Место рождения", "Место рождения должника")
        row_debtor_b.addWidget(self.edit_debtor_birth, stretch=2)
        row_debtor_b.addWidget(self.edit_debtor_place, stretch=3)
        form_layout.addLayout(row_debtor_b)

        row_debtor_ids = QHBoxLayout()
        self.edit_debtor_snils = self._make_input("СНИЛС", "СНИЛС должника")
        self.edit_debtor_inn = self._make_input("ИНН", "ИНН должника")
        row_debtor_ids.addWidget(self.edit_debtor_snils)
        row_debtor_ids.addWidget(self.edit_debtor_inn)
        form_layout.addLayout(row_debtor_ids)

        self.edit_debtor_addr = self._make_input("Адрес регистрации по месту жительства", "Адрес регистрации должника")
        form_layout.addWidget(self.edit_debtor_addr)

        row_pass1 = QHBoxLayout()
        self.edit_pass_series = self._make_input("Паспорт серия", "Серия паспорта должника")
        self.edit_pass_num = self._make_input("Паспорт номер", "Номер паспорта должника")
        self.edit_pass_date = self._make_input("Дата выдачи", "Дата выдачи паспорта должника")
        self.edit_pass_code = self._make_input("Код подразделения", "Код подразделения органа, выдавшего паспорт")
        row_pass1.addWidget(self.edit_pass_series)
        row_pass1.addWidget(self.edit_pass_num)
        row_pass1.addWidget(self.edit_pass_date)
        row_pass1.addWidget(self.edit_pass_code)
        form_layout.addLayout(row_pass1)

        self.edit_pass_issued_by = self._make_input("Кем выдан паспорт", "Кем выдан паспорт должника")
        form_layout.addWidget(self.edit_pass_issued_by)

        # Section: Работодатель должника
        form_layout.addSpacing(4)
        emp_hdr_layout = QHBoxLayout()
        emp_hdr_layout.addWidget(self._make_section_header("Место работы должника"))
        self.cb_employed = QCheckBox("Должник трудоустроен", self)
        self.cb_employed.setChecked(False)
        self.cb_employed.toggled.connect(self._on_employed_toggled)
        emp_hdr_layout.addSpacing(10)
        emp_hdr_layout.addWidget(self.cb_employed)
        emp_hdr_layout.addStretch()
        form_layout.addLayout(emp_hdr_layout)

        self.employer_container = QWidget()
        emp_cont_layout = QVBoxLayout(self.employer_container)
        emp_cont_layout.setContentsMargins(0, 2, 0, 0)
        emp_cont_layout.setSpacing(6)

        row_emp = QHBoxLayout()
        self.edit_emp_name = self._make_input("Наименование работодателя", "Наименование организации-работодателя (ООО, ПАО, ИП)")
        self.edit_emp_inn = self._make_input("ИНН работодателя", "ИНН работодателя")
        self.edit_emp_inn.setFixedWidth(130)
        row_emp.addWidget(self.edit_emp_name, stretch=3)
        row_emp.addWidget(self.edit_emp_inn, stretch=1)
        emp_cont_layout.addLayout(row_emp)

        self.edit_emp_addr = self._make_input("Адрес работодателя", "Адрес местонахождения работодателя")
        emp_cont_layout.addWidget(self.edit_emp_addr)

        form_layout.addWidget(self.employer_container)
        self.employer_container.setEnabled(False)

        # Section: Кредиторы (Банки и МФО)
        form_layout.addSpacing(4)
        cred_hdr_layout = QHBoxLayout()
        cred_hdr_layout.addWidget(self._make_section_header("Кредиторы (банки, МФО, инспекции)"))
        cred_hdr_layout.addStretch()

        self.btn_add_creditor = QPushButton("+ Добавить кредитора", self)
        self.btn_add_creditor.setObjectName("addCreditorBtn")
        self.btn_add_creditor.setCursor(Qt.PointingHandCursor)
        self.btn_add_creditor.clicked.connect(lambda: self._add_creditor_row())
        cred_hdr_layout.addWidget(self.btn_add_creditor)
        form_layout.addLayout(cred_hdr_layout)

        self.creditors_layout = QVBoxLayout()
        self.creditors_layout.setContentsMargins(0, 0, 0, 0)
        self.creditors_layout.setSpacing(4)
        form_layout.addLayout(self.creditors_layout)

        # Section 3: Семейное положение и супруг
        form_layout.addSpacing(4)
        form_layout.addWidget(self._make_section_header("Семейное положение"))

        spouse_status_layout = QHBoxLayout()
        spouse_status_layout.setSpacing(14)
        self.rb_not_married = QRadioButton("Не состоит в браке")
        self.rb_married = QRadioButton("В браке")
        self.rb_divorced = QRadioButton("В разводе менее 3 лет")
        self.rb_not_married.setChecked(True)

        self.spouse_group = QButtonGroup(self)
        self.spouse_group.addButton(self.rb_not_married, 0)
        self.spouse_group.addButton(self.rb_married, 1)
        self.spouse_group.addButton(self.rb_divorced, 2)
        self.spouse_group.idClicked.connect(self._on_spouse_status_changed)

        spouse_status_layout.addWidget(self.rb_not_married)
        spouse_status_layout.addWidget(self.rb_married)
        spouse_status_layout.addWidget(self.rb_divorced)
        spouse_status_layout.addStretch()
        form_layout.addLayout(spouse_status_layout)

        # Spouse fields container
        self.spouse_container = QWidget()
        spouse_cont_layout = QVBoxLayout(self.spouse_container)
        spouse_cont_layout.setContentsMargins(0, 4, 0, 0)
        spouse_cont_layout.setSpacing(6)

        row_sp_fio = QHBoxLayout()
        self.edit_spouse_fio = self._make_input("ФИО супруга", "ФИО супруга")
        self.edit_spouse_fio.textChanged.connect(self._on_spouse_name_changed)
        self.edit_spouse_fio_instr = self._make_input("ФИО супруга в творительном падеже", "ФИО супруга в творительном падеже")
        row_sp_fio.addWidget(self.edit_spouse_fio)
        row_sp_fio.addWidget(self.edit_spouse_fio_instr)
        spouse_cont_layout.addLayout(row_sp_fio)

        row_sp_b = QHBoxLayout()
        self.edit_spouse_birth = self._make_input("Дата рождения супруга", "Дата рождения супруга")
        self.edit_spouse_place = self._make_input("Место рождения супруга", "Место рождения супруга")
        self.edit_marriage_date = self._make_input("Дата заключения или расторжения брака", "Дата регистрации или прекращения брака")
        row_sp_b.addWidget(self.edit_spouse_birth)
        row_sp_b.addWidget(self.edit_spouse_place)
        row_sp_b.addWidget(self.edit_marriage_date)
        spouse_cont_layout.addLayout(row_sp_b)

        row_sp_ids = QHBoxLayout()
        self.edit_spouse_snils = self._make_input("СНИЛС супруга", "СНИЛС супруга")
        self.edit_spouse_inn = self._make_input("ИНН супруга", "ИНН супруга")
        row_sp_ids.addWidget(self.edit_spouse_snils)
        row_sp_ids.addWidget(self.edit_spouse_inn)
        spouse_cont_layout.addLayout(row_sp_ids)

        self.edit_spouse_addr = self._make_input("Адрес регистрации супруга", "Адрес регистрации супруга")
        spouse_cont_layout.addWidget(self.edit_spouse_addr)

        form_layout.addWidget(self.spouse_container)
        self.spouse_container.setEnabled(False)

        # Section 4: Финансовый управляющий
        form_layout.addSpacing(4)
        form_layout.addWidget(self._make_section_header("Финансовый управляющий"))
        
        row_mgr = QHBoxLayout()
        self.edit_mgr_fio = self._make_input("ФИО управляющего", "ФИО арбитражного / финансового управляющего")
        self.edit_mgr_phone = self._make_input("Телефон", "Контактный телефон финансового управляющего")
        self.edit_mgr_email = self._make_input("Эл. почта", "Электронная почта финансового управляющего")
        row_mgr.addWidget(self.edit_mgr_fio, stretch=3)
        row_mgr.addWidget(self.edit_mgr_phone, stretch=2)
        row_mgr.addWidget(self.edit_mgr_email, stretch=2)
        form_layout.addLayout(row_mgr)

        row_mgr_ids = QHBoxLayout()
        self.edit_mgr_inn = self._make_input("ИНН управляющего", "ИНН финансового управляющего")
        self.edit_mgr_snils = self._make_input("СНИЛС управляющего", "СНИЛС финансового управляющего")
        self.edit_mgr_addr = self._make_input("Почтовый адрес для корреспонденции", "Почтовый адрес для направления корреспонденции")
        row_mgr_ids.addWidget(self.edit_mgr_inn)
        row_mgr_ids.addWidget(self.edit_mgr_snils)
        row_mgr_ids.addWidget(self.edit_mgr_addr)
        form_layout.addLayout(row_mgr_ids)

        self._fill_default_manager_values()

        scroll.setWidget(form_widget)
        left_layout.addWidget(scroll, stretch=1)

        # Bottom toolbar: ONLY "Очистить"
        left_btn_bar = QHBoxLayout()
        left_btn_bar.setSpacing(8)
        left_btn_bar.setContentsMargins(0, 4, 0, 0)

        left_btn_bar.addStretch()

        self.btn_clear = QPushButton("Очистить")
        self.btn_clear.setObjectName("dangerButton")
        self.btn_clear.clicked.connect(self.clear_fields)
        left_btn_bar.addWidget(self.btn_clear)

        left_layout.addLayout(left_btn_bar)
        cards_layout.addWidget(self.left_card, stretch=6)

        # =====================================================================
        # RIGHT CARD: Список ведомств с чекбоксами (20 шаблонов)
        # =====================================================================
        self.right_card = QFrame()
        self.right_card.setObjectName("cardFrame")
        right_layout = QVBoxLayout(self.right_card)
        right_layout.setContentsMargins(16, 14, 16, 14)
        right_layout.setSpacing(10)

        right_header = QHBoxLayout()
        card2_title = QLabel("Список ведомств и шаблонов")
        card2_title.setObjectName("cardTitle")
        self.agencies_count_lbl = QLabel("")
        self.agencies_count_lbl.setObjectName("countLabel")
        right_header.addWidget(card2_title)
        right_header.addStretch()
        right_header.addWidget(self.agencies_count_lbl)
        right_layout.addLayout(right_header)

        # Scroll area for 20 checkboxes
        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setFrameShape(QFrame.NoFrame)
        right_scroll.setObjectName("agenciesScrollArea")

        agencies_widget = QWidget()
        agencies_grid = QGridLayout(agencies_widget)
        agencies_grid.setContentsMargins(4, 4, 4, 4)
        agencies_grid.setHorizontalSpacing(14)
        agencies_grid.setVerticalSpacing(10)

        mid = (len(TEMPLATES_CONFIG) + 1) // 2
        self.checkboxes = {}
        for i, item in enumerate(TEMPLATES_CONFIG):
            cb = QCheckBox(item["name"])
            # Employer template is unchecked by default until debtor is marked employed
            if item["id"] == "employer":
                cb.setChecked(False)
            else:
                cb.setChecked(True)
            cb.stateChanged.connect(self._update_agencies_count)
            self.checkboxes[item["id"]] = cb
            row = i if i < mid else i - mid
            col = 0 if i < mid else 1
            agencies_grid.addWidget(cb, row, col)

        agencies_grid.setRowStretch(mid, 1)
        right_scroll.setWidget(agencies_widget)
        right_layout.addWidget(right_scroll, stretch=1)

        # Bottom toolbar on right card: ONLY "Выбрать все" and "Снять выделение"
        right_btn_bar = QHBoxLayout()
        right_btn_bar.setSpacing(8)
        right_btn_bar.setContentsMargins(0, 4, 0, 0)

        self.btn_select_all = QPushButton("Выбрать все")
        self.btn_select_all.clicked.connect(self._select_all_agencies)
        right_btn_bar.addWidget(self.btn_select_all)

        self.btn_deselect_all = QPushButton("Снять выделение")
        self.btn_deselect_all.clicked.connect(self._deselect_all_agencies)
        right_btn_bar.addWidget(self.btn_deselect_all)

        right_layout.addLayout(right_btn_bar)
        cards_layout.addWidget(self.right_card, stretch=5)

        main_layout.addLayout(cards_layout, stretch=1)

        # =====================================================================
        # BOTTOM ACTION BAR: Centered "Сформировать запросы" button
        # =====================================================================
        bottom_bar = QHBoxLayout()
        bottom_bar.setContentsMargins(0, 4, 0, 0)
        bottom_bar.addStretch()

        self.btn_generate = QPushButton("Сформировать запросы")
        self.btn_generate.setObjectName("mainBuildButton")
        self.btn_generate.clicked.connect(self._start_generation)
        bottom_bar.addWidget(self.btn_generate)

        bottom_bar.addStretch()
        main_layout.addLayout(bottom_bar)

        self._update_agencies_count()

    def _make_section_header(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("formSectionHeader")
        return lbl

    def _make_input(self, placeholder: str, tooltip: str = "") -> HintLineEdit:
        line_edit = HintLineEdit(placeholder, tooltip or placeholder, self)
        if "адрес" in placeholder.lower():
            self._setup_address_completer(line_edit)
        return line_edit

    def _setup_address_completer(self, line_edit: QLineEdit):
        """Sets up address auto-completion with region and city prefixes from assets/regions.json."""
        if not hasattr(self, "_cached_address_prefixes"):
            prefixes = []
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            json_path = os.path.join(base_dir, "assets", "regions.json")
            if os.path.exists(json_path):
                try:
                    with open(json_path, "r", encoding="utf-8") as f:
                        regions_data = json.load(f)
                    for reg_id, reg in regions_data.items():
                        for city in reg.get("cities", []):
                            pref = city.get("prefix", "").strip()
                            if pref and pref not in prefixes:
                                prefixes.append(pref)
                except Exception:
                    pass
            self._cached_address_prefixes = prefixes

        if self._cached_address_prefixes:
            completer = QCompleter(self._cached_address_prefixes, line_edit)
            completer.setCaseSensitivity(Qt.CaseInsensitive)
            completer.setFilterMode(Qt.MatchContains)
            completer.setMaxVisibleItems(8)
            popup = completer.popup()
            if popup:
                popup.setObjectName("completerPopup")
                popup_filter = _CompleterPopupFilter(line_edit, popup)
                popup.installEventFilter(popup_filter)
            line_edit.setCompleter(completer)

    def _on_debtor_name_changed(self, text: str):
        nomn = to_nomn_fio(text.strip())
        gent = inflect_fio(nomn, 'gent')
        if not self.edit_debtor_fio_gen.text() or self.edit_debtor_fio_gen.hasFocus() is False:
            self.edit_debtor_fio_gen.setText(gent)

    def _on_spouse_name_changed(self, text: str):
        nomn = to_nomn_fio(text.strip())
        instr = inflect_fio(nomn, 'ablt')
        if not self.edit_spouse_fio_instr.text() or self.edit_spouse_fio_instr.hasFocus() is False:
            self.edit_spouse_fio_instr.setText(instr)

    def _on_spouse_status_changed(self, btn_id: int):
        has_spouse = (btn_id in (1, 2))
        self.spouse_container.setEnabled(has_spouse)

    def _on_employed_toggled(self, checked: bool):
        self.employer_container.setEnabled(checked)
        if "employer" in self.checkboxes:
            self.checkboxes["employer"].setChecked(checked)

    def _add_creditor_row(self, name: str = "", address: str = "", inn: str = ""):
        if isinstance(name, bool):
            name = ""
        row = CreditorRowWidget(name=name, address=address, inn=inn, parent=self)
        row.deleted.connect(self._remove_creditor_row)
        self.creditor_rows.append(row)
        self.creditors_layout.addWidget(row)
        row.show()

    def _remove_creditor_row(self, row_widget: CreditorRowWidget):
        if row_widget in self.creditor_rows:
            self.creditor_rows.remove(row_widget)
            self.creditors_layout.removeWidget(row_widget)
            row_widget.deleteLater()

    def _select_all_agencies(self):
        for cb in self.checkboxes.values():
            cb.setChecked(True)
        self._update_agencies_count()

    def _deselect_all_agencies(self):
        for cb in self.checkboxes.values():
            cb.setChecked(False)
        self._update_agencies_count()

    def _update_agencies_count(self):
        sel_count = sum(1 for cb in self.checkboxes.values() if cb.isChecked())
        total = len(self.checkboxes)
        self.agencies_count_lbl.setText(f"{sel_count} из {total} выбрано")
        self.btn_generate.setEnabled(sel_count > 0)

    def refresh_debtors_list(self):
        """Refreshes debtor records from SQLite database into debtor_combo."""
        if not hasattr(self, "debtor_combo"):
            return
        self._debtors_cache = self.db_manager.get_debtors()
        self.debtor_combo.blockSignals(True)
        self.debtor_combo.clear()
        self.debtor_combo.addItem("— Выберите должника из списка —", userData=None)

        for d in self._debtors_cache:
            name = d.get("full_name", "").strip()
            case = d.get("case_number", "").strip()
            display_text = f"{name} (Дело: {case})" if case else name
            self.debtor_combo.addItem(display_text, userData=d["id"])

        self.debtor_combo.setCurrentIndex(0)
        self.debtor_combo.blockSignals(False)

    def _on_debtor_combo_selected(self, index: int):
        if index <= 0:
            return
        debtor_id = self.debtor_combo.currentData()
        if not debtor_id:
            return
        debtor = self.db_manager.get_debtor_by_id(debtor_id)
        if debtor:
            self.load_debtor(debtor)

    def load_debtor(self, debtor: dict):
        """Populates all Module 2 fields with data from a debtor dictionary."""
        raw = debtor.get("parsed_raw") or {}
        merged = dict(debtor)
        merged.update(raw)
        self.set_data_dict(merged)

    def set_data_dict(self, data: dict):
        """Sets form fields from dictionary."""
        self.edit_case_no.setText(data.get("case_number", ""))
        self.edit_dec_date.setText(data.get("decision_date", ""))
        self.edit_petition_date.setText(data.get("petition_date", ""))
        self.edit_court_name.setText(data.get("court_name", ""))

        self.edit_debtor_fio.setText(data.get("debtor_fio") or data.get("full_name", ""))
        self.edit_debtor_fio_gen.setText(data.get("debtor_fio_gen", ""))
        self.edit_debtor_birth.setText(data.get("debtor_birth_date", ""))
        self.edit_debtor_place.setText(data.get("debtor_birth_place", ""))
        self.edit_debtor_addr.setText(data.get("debtor_address") or data.get("address", ""))
        self.edit_debtor_snils.setText(data.get("debtor_snils") or data.get("snils", ""))
        self.edit_debtor_inn.setText(data.get("debtor_inn") or data.get("inn", ""))

        self.edit_pass_series.setText(data.get("debtor_passport_series", ""))
        self.edit_pass_num.setText(data.get("debtor_passport_number", ""))
        self.edit_pass_issued_by.setText(data.get("debtor_passport_issued_by", ""))
        self.edit_pass_date.setText(data.get("debtor_passport_date", ""))
        self.edit_pass_code.setText(data.get("debtor_passport_code", ""))

        # Employer
        emp = bool(data.get("employer_employed", False))
        self.cb_employed.setChecked(emp)
        self._on_employed_toggled(emp)
        self.edit_emp_name.setText(data.get("employer_name", ""))
        self.edit_emp_addr.setText(data.get("employer_address", ""))
        self.edit_emp_inn.setText(data.get("employer_inn", ""))

        # Creditors
        for row in list(self.creditor_rows):
            self._remove_creditor_row(row)
        for cred in data.get("creditors", []):
            self._add_creditor_row(cred.get("name", ""), cred.get("address", ""), cred.get("inn", ""))

        # Spouse
        status = data.get("spouse_status", "not_married")
        if status == "married":
            self.rb_married.setChecked(True)
            self._on_spouse_status_changed(1)
        elif status == "divorced":
            self.rb_divorced.setChecked(True)
            self._on_spouse_status_changed(2)
        else:
            self.rb_not_married.setChecked(True)
            self._on_spouse_status_changed(0)

        self.edit_spouse_fio.setText(data.get("spouse_fio", ""))
        self.edit_spouse_fio_instr.setText(data.get("spouse_fio_instr", ""))
        self.edit_spouse_birth.setText(data.get("spouse_birth_date", ""))
        self.edit_spouse_place.setText(data.get("spouse_birth_place", ""))
        self.edit_spouse_addr.setText(data.get("spouse_address", ""))
        self.edit_spouse_snils.setText(data.get("spouse_snils", ""))
        self.edit_spouse_inn.setText(data.get("spouse_inn", ""))
        self.edit_marriage_date.setText(data.get("marriage_date", ""))

        # Manager
        if data.get("manager_fio"):
            self.edit_mgr_fio.setText(data.get("manager_fio", ""))
        if data.get("manager_phone"):
            self.edit_mgr_phone.setText(data.get("manager_phone", ""))
        if data.get("manager_email"):
            self.edit_mgr_email.setText(data.get("manager_email", ""))
        if data.get("manager_inn"):
            self.edit_mgr_inn.setText(data.get("manager_inn", ""))
        if data.get("manager_snils"):
            self.edit_mgr_snils.setText(data.get("manager_snils", ""))
        if data.get("manager_corr_address"):
            self.edit_mgr_addr.setText(data.get("manager_corr_address", ""))

    def clear_fields(self):
        if hasattr(self, "debtor_combo"):
            self.debtor_combo.blockSignals(True)
            self.debtor_combo.setCurrentIndex(0)
            self.debtor_combo.blockSignals(False)
        self.edit_case_no.clear()
        self.edit_dec_date.clear()
        self.edit_petition_date.clear()
        self.edit_court_name.clear()
        self.edit_debtor_fio.clear()
        self.edit_debtor_fio_gen.clear()
        self.edit_debtor_birth.clear()
        self.edit_debtor_place.clear()
        self.edit_debtor_addr.clear()
        self.edit_debtor_snils.clear()
        self.edit_debtor_inn.clear()
        self.edit_pass_series.clear()
        self.edit_pass_num.clear()
        self.edit_pass_issued_by.clear()
        self.edit_pass_date.clear()
        self.edit_pass_code.clear()

        # Clear employer
        self.cb_employed.setChecked(False)
        self.edit_emp_name.clear()
        self.edit_emp_addr.clear()
        self.edit_emp_inn.clear()

        # Clear creditors
        for row in list(self.creditor_rows):
            self._remove_creditor_row(row)

        self.rb_not_married.setChecked(True)
        self._on_spouse_status_changed(0)
        self.edit_spouse_fio.clear()
        self.edit_spouse_fio_instr.clear()
        self.edit_spouse_birth.clear()
        self.edit_spouse_place.clear()
        self.edit_spouse_addr.clear()
        self.edit_spouse_snils.clear()
        self.edit_spouse_inn.clear()
        self.edit_marriage_date.clear()

        self._fill_default_manager_values()

    def _fill_default_manager_values(self):
        """Fills financial manager fields with user default values from settings."""
        self.edit_mgr_fio.setText(self.settings.manager_fio)
        self.edit_mgr_phone.setText(self.settings.manager_phone)
        self.edit_mgr_email.setText(self.settings.manager_email)
        self.edit_mgr_inn.setText(self.settings.manager_inn)
        self.edit_mgr_snils.setText(self.settings.manager_snils)
        self.edit_mgr_addr.setText(self.settings.manager_corr_address)

    def get_data_dict(self) -> dict:
        spouse_st = "not_married"
        if self.rb_married.isChecked():
            spouse_st = "married"
        elif self.rb_divorced.isChecked():
            spouse_st = "divorced"

        creditors_data = [row.get_data() for row in self.creditor_rows if row.get_data()["name"] or row.get_data()["address"]]

        return {
            "court_name": self.edit_court_name.text().strip(),
            "case_number": self.edit_case_no.text().strip(),
            "decision_date": self.edit_dec_date.text().strip(),
            "petition_date": self.edit_petition_date.text().strip(),
            "debtor_fio": self.edit_debtor_fio.text().strip(),
            "debtor_fio_gen": self.edit_debtor_fio_gen.text().strip() or self.edit_debtor_fio.text().strip(),
            "debtor_birth_date": self.edit_debtor_birth.text().strip(),
            "debtor_birth_place": self.edit_debtor_place.text().strip(),
            "debtor_address": self.edit_debtor_addr.text().strip(),
            "debtor_snils": self.edit_debtor_snils.text().strip(),
            "debtor_inn": self.edit_debtor_inn.text().strip(),
            "debtor_passport_series": self.edit_pass_series.text().strip(),
            "debtor_passport_number": self.edit_pass_num.text().strip(),
            "debtor_passport_issued_by": self.edit_pass_issued_by.text().strip(),
            "debtor_passport_date": self.edit_pass_date.text().strip(),
            "debtor_passport_code": self.edit_pass_code.text().strip(),
            "employer_employed": self.cb_employed.isChecked(),
            "employer_name": self.edit_emp_name.text().strip() if self.cb_employed.isChecked() else "",
            "employer_address": self.edit_emp_addr.text().strip() if self.cb_employed.isChecked() else "",
            "employer_inn": self.edit_emp_inn.text().strip() if self.cb_employed.isChecked() else "",
            "creditors": creditors_data,
            "spouse_status": spouse_st,
            "spouse_fio": self.edit_spouse_fio.text().strip(),
            "spouse_fio_instr": self.edit_spouse_fio_instr.text().strip(),
            "spouse_birth_date": self.edit_spouse_birth.text().strip(),
            "spouse_birth_place": self.edit_spouse_place.text().strip(),
            "spouse_address": self.edit_spouse_addr.text().strip() or self.edit_debtor_addr.text().strip(),
            "spouse_snils": self.edit_spouse_snils.text().strip(),
            "spouse_inn": self.edit_spouse_inn.text().strip(),
            "marriage_date": self.edit_marriage_date.text().strip(),
            "manager_fio": self.edit_mgr_fio.text().strip(),
            "manager_phone": self.edit_mgr_phone.text().strip(),
            "manager_email": self.edit_mgr_email.text().strip(),
            "manager_inn": self.edit_mgr_inn.text().strip(),
            "manager_snils": self.edit_mgr_snils.text().strip(),
            "manager_corr_address": self.edit_mgr_addr.text().strip(),
        }

    def _start_generation(self):
        data = self.get_data_dict()
        if not data["debtor_fio"]:
            QMessageBox.warning(self, "Внимание", "Заполните ФИО должника перед формированием запросов.")
            return

        selected_ids = [tid for tid, cb in self.checkboxes.items() if cb.isChecked()]
        if not selected_ids:
            QMessageBox.warning(self, "Внимание", "Выберите хотя бы одно ведомство из списка.")
            return

        base_dir = self.settings.output_dir
        out_dir = QFileDialog.getExistingDirectory(
            self,
            "Выберите папку для сохранения запросов",
            base_dir
        )
        if not out_dir:
            return

        templates_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "templates")
        if not os.path.exists(templates_dir):
            templates_dir = os.path.join(os.path.abspath("."), "assets", "templates")

        progress = BuildProgressDialog(parent=self)
        progress.setWindowTitle("Формирование запросов...")
        progress.show()

        res = None
        try:
            res = generate_inquiries(
                data=data,
                selected_template_ids=selected_ids,
                output_base_dir=out_dir,
                templates_dir=templates_dir,
                progress_callback=progress.set_progress
            )
        except Exception as e:
            progress.close()
            QMessageBox.critical(self, "Ошибка формирования", f"Произошла ошибка при создании документов:\n{str(e)}")
            return

        progress.close()

        if res and res.get("files_count", 0) > 0:
            target_folder = res["output_dir"]
            files_count = res["files_count"]
            diag = InquirySuccessDialog(
                output_dir=target_folder,
                files_count=files_count,
                parent=self
            )
            diag.exec()

    def set_theme(self, theme_name: str):
        self.theme = theme_name
