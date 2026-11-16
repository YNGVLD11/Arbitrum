import os
import json
from PySide6.QtCore import Qt, Signal, QObject, QEvent, QPoint
from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QCheckBox, QRadioButton, QButtonGroup, QScrollArea,
    QFrame, QMessageBox, QCompleter
)
from ui.inquiry_panel import HintLineEdit, CreditorRowWidget, _CompleterPopupFilter
from core.court_parser import inflect_fio, to_nomn_fio


class DebtorEditDialog(QDialog):
    """
    Модальное окно добавления или редактирования полной карточки должника.
    Содержит все поля реквизитов дела, суда, должника, работодателя, кредиторов и супруга.
    """
    debtor_saved = Signal(dict)

    def __init__(self, debtor_data: dict = None, debtor_id: int = None, parent=None):
        super().__init__(parent)
        self.debtor_id = debtor_id
        self.initial_data = debtor_data or {}
        self.creditor_rows: list[CreditorRowWidget] = []

        title = "Редактирование карточки должника" if debtor_id else "Добавление должника в картотеку"
        self.setWindowTitle(title)
        self.resize(780, 680)
        self.setMinimumSize(650, 500)

        self._init_ui()
        if self.initial_data:
            self.load_data(self.initial_data)

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 16, 18, 16)
        main_layout.setSpacing(12)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setObjectName("formScrollArea")

        form_widget = QWidget()
        form_layout = QVBoxLayout(form_widget)
        form_layout.setContentsMargins(12, 8, 12, 8)
        form_layout.setSpacing(8)

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

        self.edit_petition_date = self._make_input("Дата принятия заявления", "Дата принятия заявления к производству")
        form_layout.addWidget(self.edit_petition_date)

        # Section 2: Должник
        form_layout.addSpacing(4)
        form_layout.addWidget(self._make_section_header("Данные должника"))

        row_debtor_fio = QHBoxLayout()
        self.edit_debtor_fio = self._make_input("ФИО должника", "Фамилия Имя Отчество должника")
        self.edit_debtor_fio.textChanged.connect(self._on_debtor_name_changed)
        self.edit_debtor_fio_gen = self._make_input("ФИО должника в родительном падеже", "ФИО в родительном падеже (кого?)")
        row_debtor_fio.addWidget(self.edit_debtor_fio)
        row_debtor_fio.addWidget(self.edit_debtor_fio_gen)
        form_layout.addLayout(row_debtor_fio)

        row_debtor_b = QHBoxLayout()
        self.edit_debtor_birth = self._make_input("Дата рождения", "Дата рождения должника")
        self.edit_debtor_place = self._make_input("Место рождения", "Место рождения должника")
        row_debtor_b.addWidget(self.edit_debtor_birth)
        row_debtor_b.addWidget(self.edit_debtor_place)
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

        # Section: Место работы должника
        form_layout.addSpacing(4)
        emp_hdr = QHBoxLayout()
        emp_hdr.addWidget(self._make_section_header("Место работы должника"))
        self.cb_employed = QCheckBox("Должник трудоустроен", self)
        self.cb_employed.setChecked(False)
        self.cb_employed.toggled.connect(self._on_employed_toggled)
        emp_hdr.addSpacing(10)
        emp_hdr.addWidget(self.cb_employed)
        emp_hdr.addStretch()
        form_layout.addLayout(emp_hdr)

        self.employer_container = QWidget()
        emp_cont_layout = QVBoxLayout(self.employer_container)
        emp_cont_layout.setContentsMargins(0, 2, 0, 0)
        emp_cont_layout.setSpacing(6)

        row_emp = QHBoxLayout()
        self.edit_emp_name = self._make_input("Наименование работодателя", "Наименование работодателя (ООО, ПАО, ИП)")
        self.edit_emp_inn = self._make_input("ИНН работодателя", "ИНН работодателя")
        self.edit_emp_inn.setFixedWidth(130)
        row_emp.addWidget(self.edit_emp_name, stretch=3)
        row_emp.addWidget(self.edit_emp_inn, stretch=1)
        emp_cont_layout.addLayout(row_emp)

        self.edit_emp_addr = self._make_input("Адрес работодателя", "Адрес местонахождения работодателя")
        emp_cont_layout.addWidget(self.edit_emp_addr)
        form_layout.addWidget(self.employer_container)
        self.employer_container.setEnabled(False)

        # Section: Кредиторы
        form_layout.addSpacing(4)
        cred_hdr = QHBoxLayout()
        cred_hdr.addWidget(self._make_section_header("Кредиторы (банки, МФО, инспекции)"))
        cred_hdr.addStretch()
        self.btn_add_creditor = QPushButton("+ Добавить кредитора", self)
        self.btn_add_creditor.setObjectName("addCreditorBtn")
        self.btn_add_creditor.setCursor(Qt.PointingHandCursor)
        self.btn_add_creditor.clicked.connect(lambda: self._add_creditor_row())
        cred_hdr.addWidget(self.btn_add_creditor)
        form_layout.addLayout(cred_hdr)

        self.creditors_layout = QVBoxLayout()
        self.creditors_layout.setContentsMargins(0, 0, 0, 0)
        self.creditors_layout.setSpacing(4)
        form_layout.addLayout(self.creditors_layout)

        # Section: Семейное положение
        form_layout.addSpacing(4)
        form_layout.addWidget(self._make_section_header("Семейное положение"))
        sp_status_layout = QHBoxLayout()
        sp_status_layout.setSpacing(14)
        self.rb_not_married = QRadioButton("Не состоит в браке")
        self.rb_married = QRadioButton("В браке")
        self.rb_divorced = QRadioButton("В разводе менее 3 лет")
        self.rb_not_married.setChecked(True)

        self.spouse_group = QButtonGroup(self)
        self.spouse_group.addButton(self.rb_not_married, 0)
        self.spouse_group.addButton(self.rb_married, 1)
        self.spouse_group.addButton(self.rb_divorced, 2)
        self.spouse_group.idClicked.connect(self._on_spouse_status_changed)

        sp_status_layout.addWidget(self.rb_not_married)
        sp_status_layout.addWidget(self.rb_married)
        sp_status_layout.addWidget(self.rb_divorced)
        sp_status_layout.addStretch()
        form_layout.addLayout(sp_status_layout)

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
        self.edit_marriage_date = self._make_input("Дата заключения или расторжения брака", "Дата регистрации брака")
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

        scroll.setWidget(form_widget)
        main_layout.addWidget(scroll, stretch=1)

        # Bottom Buttons: Сохранить и Отмена
        btn_bar = QHBoxLayout()
        btn_bar.addStretch()

        self.btn_cancel = QPushButton("Отмена")
        self.btn_cancel.clicked.connect(self.reject)
        btn_bar.addWidget(self.btn_cancel)

        self.btn_save = QPushButton("Сохранить в картотеку")
        self.btn_save.setObjectName("mainBuildButton")
        self.btn_save.clicked.connect(self._save_and_accept)
        btn_bar.addWidget(self.btn_save)

        main_layout.addLayout(btn_bar)

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
        if not self.edit_debtor_fio_gen.text() or not self.edit_debtor_fio_gen.hasFocus():
            self.edit_debtor_fio_gen.setText(gent)

    def _on_spouse_name_changed(self, text: str):
        nomn = to_nomn_fio(text.strip())
        instr = inflect_fio(nomn, 'ablt')
        if not self.edit_spouse_fio_instr.text() or not self.edit_spouse_fio_instr.hasFocus():
            self.edit_spouse_fio_instr.setText(instr)

    def _on_spouse_status_changed(self, btn_id: int):
        self.spouse_container.setEnabled(btn_id in (1, 2))

    def _on_employed_toggled(self, checked: bool):
        self.employer_container.setEnabled(checked)

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

    def load_data(self, data: dict):
        self.edit_case_no.setText(str(data.get("case_number", "")))
        self.edit_dec_date.setText(str(data.get("decision_date", "")))
        self.edit_petition_date.setText(str(data.get("petition_date", "")))
        self.edit_court_name.setText(str(data.get("court_name", "")))

        self.edit_debtor_fio.setText(str(data.get("debtor_fio", "") or data.get("full_name", "")))
        self.edit_debtor_fio_gen.setText(str(data.get("debtor_fio_gen", "")))
        self.edit_debtor_birth.setText(str(data.get("debtor_birth_date", "")))
        self.edit_debtor_place.setText(str(data.get("debtor_birth_place", "")))
        self.edit_debtor_addr.setText(str(data.get("debtor_address", "") or data.get("address", "")))
        self.edit_debtor_snils.setText(str(data.get("debtor_snils", "") or data.get("snils", "")))
        self.edit_debtor_inn.setText(str(data.get("debtor_inn", "") or data.get("inn", "")))

        # Passport
        pass_s = str(data.get("debtor_passport_series", ""))
        pass_n = str(data.get("debtor_passport_number", ""))
        pass_raw = str(data.get("passport_data", ""))
        if not pass_s and not pass_n and pass_raw:
            parts = pass_raw.split(None, 1)
            if len(parts) == 2:
                pass_s, pass_n = parts[0], parts[1]
            else:
                pass_n = pass_raw
        self.edit_pass_series.setText(pass_s)
        self.edit_pass_num.setText(pass_n)
        self.edit_pass_issued_by.setText(str(data.get("debtor_passport_issued_by", "")))
        self.edit_pass_date.setText(str(data.get("debtor_passport_date", "")))
        self.edit_pass_code.setText(str(data.get("debtor_passport_code", "")))

        # Employer
        emp_on = bool(data.get("employer_employed", False) or data.get("employer_name"))
        self.cb_employed.setChecked(emp_on)
        self.edit_emp_name.setText(str(data.get("employer_name", "")))
        self.edit_emp_addr.setText(str(data.get("employer_address", "")))
        self.edit_emp_inn.setText(str(data.get("employer_inn", "")))

        # Creditors
        for r in list(self.creditor_rows):
            self._remove_creditor_row(r)
        for c in data.get("creditors", []):
            self._add_creditor_row(name=c.get("name", ""), address=c.get("address", ""), inn=c.get("inn", ""))

        # Spouse
        sp_st = data.get("spouse_status", "not_married")
        if sp_st == "married":
            self.rb_married.setChecked(True)
            self._on_spouse_status_changed(1)
        elif sp_st == "divorced":
            self.rb_divorced.setChecked(True)
            self._on_spouse_status_changed(2)
        else:
            self.rb_not_married.setChecked(True)
            self._on_spouse_status_changed(0)

        self.edit_spouse_fio.setText(str(data.get("spouse_fio", "")))
        self.edit_spouse_fio_instr.setText(str(data.get("spouse_fio_instr", "")))
        self.edit_spouse_birth.setText(str(data.get("spouse_birth_date", "")))
        self.edit_spouse_place.setText(str(data.get("spouse_birth_place", "")))
        self.edit_spouse_addr.setText(str(data.get("spouse_address", "")))
        self.edit_spouse_snils.setText(str(data.get("spouse_snils", "")))
        self.edit_spouse_inn.setText(str(data.get("spouse_inn", "")))
        self.edit_marriage_date.setText(str(data.get("marriage_date", "")))

    def get_data_dict(self) -> dict:
        spouse_st = "not_married"
        if self.rb_married.isChecked():
            spouse_st = "married"
        elif self.rb_divorced.isChecked():
            spouse_st = "divorced"

        creditors_data = [
            row.get_data() for row in self.creditor_rows
            if row.get_data()["name"] or row.get_data()["address"]
        ]

        fio = self.edit_debtor_fio.text().strip()
        fio_gen = self.edit_debtor_fio_gen.text().strip() or fio

        return {
            "court_name": self.edit_court_name.text().strip(),
            "case_number": self.edit_case_no.text().strip(),
            "decision_date": self.edit_dec_date.text().strip(),
            "petition_date": self.edit_petition_date.text().strip(),
            "debtor_fio": fio,
            "full_name": fio,
            "debtor_fio_gen": fio_gen,
            "debtor_birth_date": self.edit_debtor_birth.text().strip(),
            "debtor_birth_place": self.edit_debtor_place.text().strip(),
            "debtor_address": self.edit_debtor_addr.text().strip(),
            "address": self.edit_debtor_addr.text().strip(),
            "debtor_snils": self.edit_debtor_snils.text().strip(),
            "snils": self.edit_debtor_snils.text().strip(),
            "debtor_inn": self.edit_debtor_inn.text().strip(),
            "inn": self.edit_debtor_inn.text().strip(),
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
        }

    def _save_and_accept(self):
        data = self.get_data_dict()
        if not data["debtor_fio"]:
            QMessageBox.warning(self, "Внимание", "Поле «ФИО должника» обязательно для заполнения.")
            return
        self.debtor_saved.emit(data)
        self.accept()
