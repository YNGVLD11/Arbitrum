import os
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QCheckBox, QRadioButton, QButtonGroup, QScrollArea,
    QFrame, QFileDialog, QMessageBox, QProgressBar, QToolTip
)
from PySide6.QtGui import QCursor
from ui.themes import THEME_FEMININE
from core.court_parser import CourtParserWorker, parse_court_decision, inflect_fio, to_nomn_fio
from core.inquiry_generator import TEMPLATES_CONFIG, generate_inquiries
from ui.progress_dialog import BuildProgressDialog
from ui.inquiry_success_dialog import InquirySuccessDialog


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

        self.label = QLabel("Перетащите решение или определение суда (PDF, DOCX)\nили нажмите для выбора файла")
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

    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.theme = settings.theme
        self.parser_worker = None
        self._init_ui()

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

        # Drop Zone
        self.drop_area = DropArea(self)
        self.drop_area.file_dropped.connect(self._load_file)
        self.drop_area.clicked.connect(self._open_file_dialog)
        left_layout.addWidget(self.drop_area)

        # Parsing Progress Bar (hidden by default)
        self.parse_progress_bar = QProgressBar()
        self.parse_progress_bar.setObjectName("parsingProgressBar")
        self.parse_progress_bar.setFixedHeight(8)
        self.parse_progress_bar.setTextVisible(False)
        self.parse_progress_bar.hide()
        left_layout.addWidget(self.parse_progress_bar)

        self.parse_status_lbl = QLabel("")
        self.parse_status_lbl.setObjectName("parsingStatusLabel")
        self.parse_status_lbl.hide()
        left_layout.addWidget(self.parse_status_lbl)

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
        self.edit_case_no = self._make_input("Номер дела (напр. А45-10470/2026)", "Номер арбитражного дела")
        self.edit_dec_date = self._make_input("Дата решения (напр. 07.05.2026)", "Дата судебного акта / решения")
        row_court.addWidget(self.edit_case_no, stretch=3)
        row_court.addWidget(self.edit_dec_date, stretch=2)
        form_layout.addLayout(row_court)

        self.edit_court_name = self._make_input("Наименование арбитражного суда", "Наименование арбитражного суда")
        form_layout.addWidget(self.edit_court_name)

        # Section 2: Должник
        form_layout.addSpacing(4)
        form_layout.addWidget(self._make_section_header("Данные должника"))
        
        row_fio = QHBoxLayout()
        self.edit_debtor_fio = self._make_input("ФИО должника (Именительный падеж)", "ФИО должника (в именительном падеже)")
        self.edit_debtor_fio.textChanged.connect(self._on_debtor_name_changed)
        self.edit_debtor_fio_gen = self._make_input("ФИО должника (Родительный падеж)", "ФИО должника (в родительном падеже: кого?)")
        row_fio.addWidget(self.edit_debtor_fio)
        row_fio.addWidget(self.edit_debtor_fio_gen)
        form_layout.addLayout(row_fio)

        row_debtor_b = QHBoxLayout()
        self.edit_debtor_birth = self._make_input("Дата рождения (ДД.ММ.ГГГГ)", "Дата рождения должника")
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
        self.edit_pass_series = self._make_input("Паспорт серия", "Серия паспорта должника (4 цифры)")
        self.edit_pass_num = self._make_input("Паспорт номер", "Номер паспорта должника (6 цифр)")
        self.edit_pass_date = self._make_input("Дата выдачи", "Дата выдачи паспорта должника")
        self.edit_pass_code = self._make_input("Код подразделения", "Код подразделения органа, выдавшего паспорт")
        row_pass1.addWidget(self.edit_pass_series)
        row_pass1.addWidget(self.edit_pass_num)
        row_pass1.addWidget(self.edit_pass_date)
        row_pass1.addWidget(self.edit_pass_code)
        form_layout.addLayout(row_pass1)

        self.edit_pass_issued_by = self._make_input("Кем выдан паспорт", "Кем выдан паспорт должника")
        form_layout.addWidget(self.edit_pass_issued_by)

        # Section 3: Семейное положение и супруг
        form_layout.addSpacing(4)
        form_layout.addWidget(self._make_section_header("Семейное положение"))

        spouse_status_layout = QHBoxLayout()
        spouse_status_layout.setSpacing(14)
        self.rb_not_married = QRadioButton("Не состоит в браке")
        self.rb_married = QRadioButton("В браке")
        self.rb_divorced = QRadioButton("В разводе (< 3 лет)")
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
        self.edit_spouse_fio = self._make_input("ФИО супруга(и)", "ФИО супруга(и) (в именительном падеже)")
        self.edit_spouse_fio.textChanged.connect(self._on_spouse_name_changed)
        self.edit_spouse_fio_instr = self._make_input("ФИО супруга (Творительный падеж: с кем?)", "ФИО супруга в творительном падеже (с кем: с супругом / супругой)")
        row_sp_fio.addWidget(self.edit_spouse_fio)
        row_sp_fio.addWidget(self.edit_spouse_fio_instr)
        spouse_cont_layout.addLayout(row_sp_fio)

        row_sp_b = QHBoxLayout()
        self.edit_spouse_birth = self._make_input("Дата рождения супруга(и)", "Дата рождения супруга(и)")
        self.edit_spouse_place = self._make_input("Место рождения супруга(и)", "Место рождения супруга(и)")
        self.edit_marriage_date = self._make_input("Дата заключения/расторжения брака", "Дата регистрации или прекращения брака")
        row_sp_b.addWidget(self.edit_spouse_birth)
        row_sp_b.addWidget(self.edit_spouse_place)
        row_sp_b.addWidget(self.edit_marriage_date)
        spouse_cont_layout.addLayout(row_sp_b)

        row_sp_ids = QHBoxLayout()
        self.edit_spouse_snils = self._make_input("СНИЛС супруга(и)", "СНИЛС супруга(и)")
        self.edit_spouse_inn = self._make_input("ИНН супруга(и)", "ИНН супруга(и)")
        row_sp_ids.addWidget(self.edit_spouse_snils)
        row_sp_ids.addWidget(self.edit_spouse_inn)
        spouse_cont_layout.addLayout(row_sp_ids)

        self.edit_spouse_addr = self._make_input("Адрес регистрации супруга(и) (если совпадает, можно оставить пустым)", "Адрес регистрации супруга(и)")
        spouse_cont_layout.addWidget(self.edit_spouse_addr)

        form_layout.addWidget(self.spouse_container)
        self.spouse_container.setEnabled(False)

        # Section 4: Финансовый управляющий
        form_layout.addSpacing(4)
        form_layout.addWidget(self._make_section_header("Финансовый управляющий"))
        
        row_mgr = QHBoxLayout()
        self.edit_mgr_fio = self._make_input("ФИО управляющего", "ФИО арбитражного / финансового управляющего")
        self.edit_mgr_fio.setText("Гусарова Ксения Андреевна")
        self.edit_mgr_phone = self._make_input("Телефон", "Контактный телефон финансового управляющего")
        self.edit_mgr_phone.setText("+7 (913) 989-01-63")
        self.edit_mgr_email = self._make_input("Эл. почта", "Электронная почта финансового управляющего")
        self.edit_mgr_email.setText("kseniya_gusarova@mail.ru")
        row_mgr.addWidget(self.edit_mgr_fio, stretch=3)
        row_mgr.addWidget(self.edit_mgr_phone, stretch=2)
        row_mgr.addWidget(self.edit_mgr_email, stretch=2)
        form_layout.addLayout(row_mgr)

        row_mgr_ids = QHBoxLayout()
        self.edit_mgr_inn = self._make_input("ИНН управляющего", "ИНН финансового управляющего")
        self.edit_mgr_inn.setText("380470431942")
        self.edit_mgr_snils = self._make_input("СНИЛС управляющего", "СНИЛС финансового управляющего")
        self.edit_mgr_snils.setText("136-556-599 95")
        self.edit_mgr_addr = self._make_input("Почтовый адрес для корреспонденции", "Почтовый адрес для направления корреспонденции")
        self.edit_mgr_addr.setText("630007, г. Новосибирск, а/я 1")
        row_mgr_ids.addWidget(self.edit_mgr_inn)
        row_mgr_ids.addWidget(self.edit_mgr_snils)
        row_mgr_ids.addWidget(self.edit_mgr_addr)
        form_layout.addLayout(row_mgr_ids)

        scroll.setWidget(form_widget)
        left_layout.addWidget(scroll, stretch=1)

        # Bottom toolbar: ONLY "Добавить" and "Очистить"
        left_btn_bar = QHBoxLayout()
        left_btn_bar.setSpacing(8)
        left_btn_bar.setContentsMargins(0, 4, 0, 0)

        self.btn_add = QPushButton("Добавить")
        self.btn_add.clicked.connect(self._open_file_dialog)
        left_btn_bar.addWidget(self.btn_add)

        left_btn_bar.addStretch()

        self.btn_clear = QPushButton("Очистить")
        self.btn_clear.setObjectName("dangerButton")
        self.btn_clear.clicked.connect(self.clear_fields)
        left_btn_bar.addWidget(self.btn_clear)

        left_layout.addLayout(left_btn_bar)
        cards_layout.addWidget(self.left_card, stretch=6)

        # =====================================================================
        # RIGHT CARD: Список ведомств с чекбоксами
        # =====================================================================
        self.right_card = QFrame()
        self.right_card.setObjectName("cardFrame")
        right_layout = QVBoxLayout(self.right_card)
        right_layout.setContentsMargins(16, 14, 16, 14)
        right_layout.setSpacing(10)

        right_header = QHBoxLayout()
        card2_title = QLabel("Список ведомств")
        card2_title.setObjectName("cardTitle")
        self.agencies_count_lbl = QLabel("")
        self.agencies_count_lbl.setObjectName("countLabel")
        right_header.addWidget(card2_title)
        right_header.addStretch()
        right_header.addWidget(self.agencies_count_lbl)
        right_layout.addLayout(right_header)

        # Scroll area for 18 checkboxes
        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setFrameShape(QFrame.NoFrame)
        right_scroll.setObjectName("agenciesScrollArea")

        agencies_widget = QWidget()
        agencies_layout = QVBoxLayout(agencies_widget)
        agencies_layout.setContentsMargins(4, 4, 4, 4)
        agencies_layout.setSpacing(8)

        self.checkboxes = {}
        for item in TEMPLATES_CONFIG:
            cb = QCheckBox(item["name"])
            cb.setChecked(True)
            cb.stateChanged.connect(self._update_agencies_count)
            self.checkboxes[item["id"]] = cb
            agencies_layout.addWidget(cb)

        agencies_layout.addStretch()
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
        cards_layout.addWidget(self.right_card, stretch=4)

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
        return HintLineEdit(placeholder, tooltip or placeholder, self)

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

    def _open_file_dialog(self):
        fpath, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите решение или определение суда",
            "",
            "Судебные акты (*.pdf *.docx *.doc);;PDF файлы (*.pdf);;Word документы (*.docx *.doc)"
        )
        if fpath:
            self._load_file(fpath)

    def _load_file(self, file_path: str):
        self.drop_area.label.setText(f"Загружен: {os.path.basename(file_path)}")
        self.parse_progress_bar.show()
        self.parse_progress_bar.setValue(10)
        self.parse_status_lbl.show()
        self.parse_status_lbl.setText("Анализ документа...")

        self.parser_worker = CourtParserWorker(file_path)
        self.parser_worker.progress.connect(self._on_parse_progress)
        self.parser_worker.finished_signal.connect(self._on_parse_finished)
        self.parser_worker.failed_signal.connect(self._on_parse_failed)
        self.parser_worker.start()

    def _on_parse_progress(self, val: int, msg: str):
        self.parse_progress_bar.setValue(val)
        self.parse_status_lbl.setText(msg)

    def _on_parse_finished(self, data: dict):
        if data.get("manager_fio"):
            self.edit_mgr_fio.setText(data["manager_fio"])
        if data.get("manager_inn"):
            self.edit_mgr_inn.setText(data["manager_inn"])
        if data.get("manager_snils"):
            self.edit_mgr_snils.setText(data["manager_snils"])
        self.parse_progress_bar.hide()
        self.parse_status_lbl.hide()

        # Populate Fields
        self.edit_case_no.setText(data.get("case_number", ""))
        self.edit_dec_date.setText(data.get("decision_date", ""))
        self.edit_court_name.setText(data.get("court_name", ""))

        self.edit_debtor_fio.setText(data.get("debtor_fio", ""))
        self.edit_debtor_fio_gen.setText(data.get("debtor_fio_gen", ""))
        self.edit_debtor_birth.setText(data.get("debtor_birth_date", ""))
        self.edit_debtor_place.setText(data.get("debtor_birth_place", ""))
        self.edit_debtor_addr.setText(data.get("debtor_address", ""))
        self.edit_debtor_snils.setText(data.get("debtor_snils", ""))
        self.edit_debtor_inn.setText(data.get("debtor_inn", ""))

        self.edit_pass_series.setText(data.get("debtor_passport_series", ""))
        self.edit_pass_num.setText(data.get("debtor_passport_number", ""))
        self.edit_pass_issued_by.setText(data.get("debtor_passport_issued_by", ""))
        self.edit_pass_date.setText(data.get("debtor_passport_date", ""))
        self.edit_pass_code.setText(data.get("debtor_passport_code", ""))

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

    def _on_parse_failed(self, err: str):
        self.parse_progress_bar.hide()
        self.parse_status_lbl.hide()
        QMessageBox.warning(self, "Ошибка разбора файла", f"Не удалось автоматически извлечь данные:\n{err}\n\nВы можете заполнить реквизиты вручную.")

    def clear_fields(self):
        self.drop_area.label.setText("Перетащите решение или определение суда (PDF, DOCX)\nили нажмите для выбора файла")
        self.edit_case_no.clear()
        self.edit_dec_date.clear()
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

        if not self.edit_mgr_fio.text():

            self.edit_mgr_fio.setText("Гусарова Ксения Андреевна")

        if not self.edit_mgr_inn.text():

            self.edit_mgr_inn.setText("380470431942")

        if not self.edit_mgr_snils.text():

            self.edit_mgr_snils.setText("136-556-599 95")

        if not self.edit_mgr_addr.text():

            self.edit_mgr_addr.setText("630007, г. Новосибирск, а/я 1")

        if not self.edit_mgr_phone.text():

            self.edit_mgr_phone.setText("+7 (913) 989-01-63")

        if not self.edit_mgr_email.text():

            self.edit_mgr_email.setText("kseniya_gusarova@mail.ru")
        if not self.edit_mgr_fio.text():
            self.edit_mgr_fio.setText("Гусарова Ксения Андреевна")
        if not self.edit_mgr_inn.text():
            self.edit_mgr_inn.setText("380470431942")
        if not self.edit_mgr_snils.text():
            self.edit_mgr_snils.setText("136-556-599 95")
        if not self.edit_mgr_addr.text():
            self.edit_mgr_addr.setText("630007, г. Новосибирск, а/я 1")
        if not self.edit_mgr_phone.text():
            self.edit_mgr_phone.setText("+7 (913) 989-01-63")
        if not self.edit_mgr_email.text():
            self.edit_mgr_email.setText("kseniya_gusarova@mail.ru")

    def get_data_dict(self) -> dict:
        spouse_st = "not_married"
        if self.rb_married.isChecked():
            spouse_st = "married"
        elif self.rb_divorced.isChecked():
            spouse_st = "divorced"

        return {
            "court_name": self.edit_court_name.text().strip(),
            "case_number": self.edit_case_no.text().strip(),
            "decision_date": self.edit_dec_date.text().strip(),
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

        # Choose destination folder
        base_dir = self.settings.output_dir
        out_dir = QFileDialog.getExistingDirectory(
            self,
            "Выберите папку для сохранения запросов",
            base_dir
        )
        if not out_dir:
            return

        # Templates directory
        base_app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        tmpl_dir = os.path.join(base_app_dir, "assets", "templates")

        prog_dlg = BuildProgressDialog(self)
        prog_dlg.setWindowTitle("Формирование запросов")

        def _do_generate():
            try:
                res = generate_inquiries(
                    data=data,
                    selected_template_ids=selected_ids,
                    output_base_dir=out_dir,
                    templates_dir=tmpl_dir,
                    progress_callback=prog_dlg.set_progress
                )
                prog_dlg.accept()
                success_dlg = InquirySuccessDialog(
                    output_dir=res["output_dir"],
                    inquiries_count=res["files_count"],
                    parent=self
                )
                success_dlg.exec()
            except Exception as e:
                prog_dlg.reject()
                QMessageBox.critical(self, "Ошибка формирования", f"Произошла ошибка:\n{e}")

        from PySide6.QtCore import QTimer
        QTimer.singleShot(100, _do_generate)
        prog_dlg.exec()

    def set_theme(self, theme: str):
        self.theme = theme
