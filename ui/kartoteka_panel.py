import os
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QFrame,
    QFileDialog, QMessageBox, QScrollArea, QSplitter,
    QStackedWidget, QApplication, QCheckBox, QTextEdit
)
from PySide6.QtGui import QIcon
from core.database import DatabaseManager
from core.court_parser import parse_court_decision
from core.deadlines import calculate_deadlines
from core.debtor_exporter import (
    export_debtor_to_text, export_all_debtors_to_text, parse_debtor_from_text
)
from core.publications_generator import (
    generate_kommersant_doc, generate_efrsb_doc, generate_consent_doc, format_short_fio
)
from core.converter import convert_word_to_pdf
from ui.inquiry_success_dialog import InquirySuccessDialog
from ui.debtor_dialog import DebtorEditDialog

THEME_ACTIVE_BTN_COLORS = {
    "light": "#2563EB",
    "feminine": "#FF4D6D",
    "cappuccino": "#8F5E38",
    "lavender": "#7C3AED",
}

THEME_SELECTION_BG_COLORS = {
    "light": "#EFF6FF",
    "feminine": "#FFF0F3",
    "cappuccino": "#F2E9E1",
    "lavender": "#EDE9FE",
}

THEME_SELECTION_BORDER_COLORS = {
    "light": "#BFDBFE",
    "feminine": "#FFCCD5",
    "cappuccino": "#D7C7B7",
    "lavender": "#DDD6FE",
}

FIRST_CONTACT_DOCS = [
    ("pass", "Паспорт (все заполненные страницы)", True),
    ("inn", "ИНН", True),
    ("snils", "СНИЛС", True),
    ("marriage_kids", "Свидетельство о браке, о рождении детей", True),
    ("deals", "Документы по сделкам (договоры о продаже)", True),
    ("creditors", "Сведения о кредиторах (кто, сколько должны)", True),
    ("bank_stmts", "Выписки по текущим счетам (2-3 справок будет достаточно)", True),
    ("gosuslugi", "Логин и пароль от госуслуг", True),
]


class KartotekaDropArea(QFrame):
    """
    Пунктирная область Drag & Drop для импорта судебных актов прямо в картотеку.
    """
    file_dropped = Signal(str)
    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("kartotekaDropArea")
        self.setAcceptDrops(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(64)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        self.label = QLabel("Перетащите решение суда (PDF/Word) для добавления должника\nили нажмите для выбора файла", self)
        self.label.setObjectName("kartotekaDropAreaText")
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setWordWrap(True)
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


class KartotekaPanel(QWidget):
    debtor_selected_for_inquiry = Signal(dict)
    debtors_changed = Signal()

    def __init__(self, db_manager: DatabaseManager, settings, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.settings = settings
        self.current_debtors = []
        self.selected_debtor = None
        self.script_mode = "first"  # "first" или "court"

        self.current_theme = "light"
        if hasattr(self.settings, "theme"):
            self.current_theme = self.settings.theme or "light"

        self._init_ui()
        self.refresh_table()

    def set_theme(self, theme_name: str):
        self.current_theme = theme_name
        self._update_tab_button_styles()
        self._update_script_container_style()

    def _update_script_container_style(self):
        bg = THEME_SELECTION_BG_COLORS.get(self.current_theme, "#EFF6FF")
        border = THEME_SELECTION_BORDER_COLORS.get(self.current_theme, "#BFDBFE")
        if hasattr(self, "script_container"):
            self.script_container.setStyleSheet(
                f"QFrame {{ background-color: {bg}; border: 1px solid {border}; border-radius: 8px; }}"
            )

    def _update_tab_button_styles(self):
        active_color = THEME_ACTIVE_BTN_COLORS.get(self.current_theme, "#2563EB")
        idx = self.right_stack.currentIndex()
        tabs = [self.btn_tab_props, self.btn_tab_deadlines, self.btn_tab_script]

        for i, btn in enumerate(tabs):
            if i == idx:
                btn.setStyleSheet(
                    f"background-color: {active_color}; color: #FFFFFF; font-weight: 700; font-size: 12px; border-radius: 6px; padding: 0 10px;"
                )
            else:
                btn.setStyleSheet(
                    "background-color: #E2E8F0; color: #475569; font-weight: 600; font-size: 12px; border-radius: 6px; padding: 0 10px;"
                )

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(12)

        # Верхняя панель управления: белая скругленная карточка
        top_card = QFrame()
        top_card.setObjectName("cardFrame")
        top_card_layout = QHBoxLayout(top_card)
        top_card_layout.setContentsMargins(14, 12, 14, 12)
        top_card_layout.setSpacing(14)

        # Слева: Блок "Перетащите решение суда..."
        self.drop_area = KartotekaDropArea(self)
        self.drop_area.file_dropped.connect(self._import_from_court_file)
        self.drop_area.clicked.connect(self._open_court_file_dialog)
        top_card_layout.addWidget(self.drop_area, stretch=3)

        # Справа: Кнопка "Импорт" и "Экспорт"
        exp_imp_layout = QHBoxLayout()
        exp_imp_layout.setSpacing(8)

        self.btn_import_txt = QPushButton("Импорт", self)
        self.btn_import_txt.setFixedHeight(44)
        self.btn_import_txt.setCursor(Qt.PointingHandCursor)
        self.btn_import_txt.setToolTip("Импорт должников из текстового файла (.txt) или базы данных / архива (.db, .sqlite, .zip) с автоматическим объединением")
        self.btn_import_txt.clicked.connect(self._import_from_text_file)
        exp_imp_layout.addWidget(self.btn_import_txt)

        self.btn_export_txt = QPushButton("Экспорт", self)
        self.btn_export_txt.setFixedHeight(44)
        self.btn_export_txt.setCursor(Qt.PointingHandCursor)
        self.btn_export_txt.setToolTip("Экспорт карточки выбранного должника или всей базы данных")
        self.btn_export_txt.clicked.connect(self._on_export_clicked)
        exp_imp_layout.addWidget(self.btn_export_txt)

        top_card_layout.addLayout(exp_imp_layout, stretch=2)

        main_layout.addWidget(top_card)

        # Центральный сплиттер (как в модуле 1):
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setHandleWidth(16)
        self.splitter.setChildrenCollapsible(True)

        # Левая часть: Таблица
        table_frame = QFrame()
        table_frame.setObjectName("cardFrame")
        table_layout = QVBoxLayout(table_frame)
        table_layout.setContentsMargins(14, 12, 14, 12)
        table_layout.setSpacing(8)

        table_hdr = QHBoxLayout()
        lbl_tbl_title = QLabel("Список должников в базе")
        lbl_tbl_title.setObjectName("cardTitle")
        self.lbl_count = QLabel("0 записей")
        self.lbl_count.setObjectName("countLabel")
        table_hdr.addWidget(lbl_tbl_title)
        table_hdr.addStretch()
        table_hdr.addWidget(self.lbl_count)
        table_layout.addLayout(table_hdr)

        self.table = QTableWidget(0, 4, self)
        self.table.setObjectName("kartotekaTable")
        self.table.setHorizontalHeaderLabels(["ID", "ФИО должника", "Номер дела", "Адрес регистрации"])
        self.table.setColumnHidden(0, True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setColumnWidth(1, 260)
        self.table.setColumnWidth(2, 140)
        self.table.setColumnWidth(3, 220)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self._on_table_selection_changed)
        self.table.itemDoubleClicked.connect(self._on_table_double_clicked)
        table_layout.addWidget(self.table)

        tbl_actions = QHBoxLayout()
        tbl_actions.setSpacing(8)

        self.btn_add_manual = QPushButton("Добавить", self)
        self.btn_add_manual.setObjectName("primaryButton")
        self.btn_add_manual.setFixedHeight(34)
        self.btn_add_manual.setCursor(Qt.PointingHandCursor)
        self.btn_add_manual.clicked.connect(self._on_add_manual)
        tbl_actions.addWidget(self.btn_add_manual)

        self.btn_edit_selected = QPushButton("Редактировать")
        self.btn_edit_selected.setFixedHeight(34)
        self.btn_edit_selected.clicked.connect(self._edit_selected_debtor)
        self.btn_edit_selected.setEnabled(False)
        tbl_actions.addWidget(self.btn_edit_selected)

        self.btn_delete_selected = QPushButton("Удалить")
        self.btn_delete_selected.setObjectName("dangerButton")
        self.btn_delete_selected.setFixedHeight(34)
        self.btn_delete_selected.clicked.connect(self._delete_selected_debtor)
        self.btn_delete_selected.setEnabled(False)
        tbl_actions.addWidget(self.btn_delete_selected)

        tbl_actions.addStretch()
        table_layout.addLayout(tbl_actions)

        self.splitter.addWidget(table_frame)

        # Правая часть: Подробная информация с переключателем вкладок (Реквизиты / Сроки / Скрипт)
        info_frame = QFrame()
        info_frame.setObjectName("cardFrame")
        info_layout = QVBoxLayout(info_frame)
        info_layout.setContentsMargins(14, 12, 14, 12)
        info_layout.setSpacing(8)

        # Tab buttons bar
        tabs_header = QHBoxLayout()
        tabs_header.setSpacing(6)

        self.btn_tab_props = QPushButton("Реквизиты")
        self.btn_tab_props.setObjectName("secondaryButton")
        self.btn_tab_props.setCursor(Qt.PointingHandCursor)
        self.btn_tab_props.setFixedHeight(30)
        self.btn_tab_props.clicked.connect(lambda: self._switch_right_tab(0))
        tabs_header.addWidget(self.btn_tab_props)

        self.btn_tab_deadlines = QPushButton("Сроки")
        self.btn_tab_deadlines.setObjectName("secondaryButton")
        self.btn_tab_deadlines.setCursor(Qt.PointingHandCursor)
        self.btn_tab_deadlines.setFixedHeight(30)
        self.btn_tab_deadlines.clicked.connect(lambda: self._switch_right_tab(1))
        tabs_header.addWidget(self.btn_tab_deadlines)

        self.btn_tab_script = QPushButton("Скрипт-сообщение")
        self.btn_tab_script.setObjectName("secondaryButton")
        self.btn_tab_script.setCursor(Qt.PointingHandCursor)
        self.btn_tab_script.setFixedHeight(30)
        self.btn_tab_script.clicked.connect(lambda: self._switch_right_tab(2))
        tabs_header.addWidget(self.btn_tab_script)

        tabs_header.addStretch()
        info_layout.addLayout(tabs_header)

        # Right stacked widget
        self.right_stack = QStackedWidget()

        # Tab 0: Реквизиты
        tab_props_widget = QWidget()
        v_props = QVBoxLayout(tab_props_widget)
        v_props.setContentsMargins(0, 4, 0, 4)
        v_props.setSpacing(8)

        info_scroll = QScrollArea()
        info_scroll.setWidgetResizable(True)
        info_scroll.setFrameShape(QFrame.NoFrame)
        info_scroll.setObjectName("infoScrollArea")

        self.info_content = QLabel("Выберите должника из списка слева\nдля просмотра информации")
        self.info_content.setObjectName("kartotekaInfoLabel")
        self.info_content.setTextFormat(Qt.PlainText)
        self.info_content.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
        self.info_content.setWordWrap(True)
        self.info_content.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.info_content.setContentsMargins(12, 10, 12, 10)
        self.info_content.setStyleSheet("QLabel#kartotekaInfoLabel { line-height: 1.45; font-size: 13px; }")
        info_scroll.setWidget(self.info_content)
        v_props.addWidget(info_scroll, stretch=1)

        # Подвал первой вкладки: кнопка формирования заявления-согласия
        self.btn_gen_consent = QPushButton("Сформировать согласие")
        self.btn_gen_consent.setObjectName("primaryButton")
        self.btn_gen_consent.setFixedHeight(34)
        self.btn_gen_consent.setCursor(Qt.PointingHandCursor)
        self.btn_gen_consent.setEnabled(False)
        self.btn_gen_consent.clicked.connect(self._generate_consent_doc)
        v_props.addWidget(self.btn_gen_consent)

        self.right_stack.addWidget(tab_props_widget)

        # Tab 1: Сроки
        tab_deadlines_widget = QWidget()
        v_deadlines = QVBoxLayout(tab_deadlines_widget)
        v_deadlines.setContentsMargins(0, 4, 0, 4)
        v_deadlines.setSpacing(8)

        dl_scroll = QScrollArea()
        dl_scroll.setWidgetResizable(True)
        dl_scroll.setFrameShape(QFrame.NoFrame)

        self.deadlines_content = QLabel("Выберите должника для расчёта контрольных сроков.")
        self.deadlines_content.setTextFormat(Qt.RichText)
        self.deadlines_content.setWordWrap(True)
        self.deadlines_content.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.deadlines_content.setContentsMargins(12, 10, 12, 10)
        dl_scroll.setWidget(self.deadlines_content)
        v_deadlines.addWidget(dl_scroll, stretch=1)

        # Подвал второй вкладки: аккуратная стандартная кнопка генерации с гарантированным отступом
        self.btn_gen_publications = QPushButton("Сформировать письма в ЕФРСБ и Коммерсантъ")
        self.btn_gen_publications.setObjectName("primaryButton")
        self.btn_gen_publications.setFixedHeight(34)
        self.btn_gen_publications.setCursor(Qt.PointingHandCursor)
        self.btn_gen_publications.setEnabled(False)
        self.btn_gen_publications.clicked.connect(self._generate_publications_docs)
        v_deadlines.addWidget(self.btn_gen_publications)

        self.right_stack.addWidget(tab_deadlines_widget)

        # Tab 2: Скрипт-сообщение
        tab_script_widget = QWidget()
        v_script = QVBoxLayout(tab_script_widget)
        v_script.setContentsMargins(0, 4, 0, 0)
        v_script.setSpacing(8)

        self.cb_grid_layout = QVBoxLayout()
        self.cb_grid_layout.setSpacing(6)
        self.script_checkboxes = []
        v_script.addLayout(self.cb_grid_layout)
        self._rebuild_script_checkboxes()

        sep_script = QFrame()
        sep_script.setFrameShape(QFrame.HLine)
        sep_script.setStyleSheet("background-color: #E5E7EB; max-height: 1px; border: none; margin: 4px 0;")
        v_script.addWidget(sep_script)

        self.script_container = QFrame()
        self._update_script_container_style()
        sc_layout = QVBoxLayout(self.script_container)
        sc_layout.setContentsMargins(10, 8, 10, 10)
        sc_layout.setSpacing(4)

        sc_top = QHBoxLayout()
        sc_top.setContentsMargins(0, 0, 0, 0)
        sc_top.addStretch()

        self.btn_copy_script = QPushButton(self.script_container)
        self.btn_copy_script.setCursor(Qt.PointingHandCursor)
        self.btn_copy_script.setToolTip("Копировать в буфер обмена")
        self.btn_copy_script.setFixedSize(26, 26)

        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        copy_icon_path = os.path.join(base_dir, "assets", "icons", "copy_icon.png").replace("\\", "/")
        self.copy_icon = QIcon(copy_icon_path)

        self.btn_copy_script.setIcon(self.copy_icon)
        self.btn_copy_script.setStyleSheet(
            "QPushButton { border: 1px solid #CBD5E1; background: #FFFFFF; border-radius: 4px; padding: 0px; } "
            "QPushButton:hover { background-color: #F1F5F9; border-color: #94A3B8; }"
        )
        self.btn_copy_script.clicked.connect(self._on_copy_script_clicked)
        sc_top.addWidget(self.btn_copy_script)
        sc_layout.addLayout(sc_top)

        self.script_text_edit = QTextEdit()
        self.script_text_edit.setStyleSheet(
            "QTextEdit { border: none; font-size: 13px; color: #0F172A; line-height: 1.45; background: transparent; padding: 2px; }"
        )
        sc_layout.addWidget(self.script_text_edit, stretch=1)
        v_script.addWidget(self.script_container, stretch=1)

        self.right_stack.addWidget(tab_script_widget)

        info_layout.addWidget(self.right_stack, stretch=1)

        self._switch_right_tab(0)

        self.splitter.addWidget(info_frame)
        self.splitter.setCollapsible(0, False)
        self.splitter.setCollapsible(1, True)
        self.splitter.setSizes([720, 360])

        main_layout.addWidget(self.splitter, stretch=1)

    def refresh_table(self, select_debtor_id: int = None):
        """Перезагружает список должников из базы данных в таблицу и сохраняет горизонтальную позицию скролла."""
        self.current_debtors = self.db_manager.get_debtors()
        self.table.setRowCount(0)
        self.lbl_count.setText(f"{len(self.current_debtors)} записей")

        target_row = -1
        for row_idx, d in enumerate(self.current_debtors):
            self.table.insertRow(row_idx)

            id_val = d["id"]
            id_item = QTableWidgetItem(str(id_val))
            id_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row_idx, 0, id_item)

            fio_item = QTableWidgetItem(d.get("full_name", ""))
            self.table.setItem(row_idx, 1, fio_item)

            case_item = QTableWidgetItem(d.get("case_number", ""))
            self.table.setItem(row_idx, 2, case_item)

            addr_item = QTableWidgetItem(d.get("address", ""))
            self.table.setItem(row_idx, 3, addr_item)

            if select_debtor_id is not None and id_val == select_debtor_id:
                target_row = row_idx

        if target_row >= 0:
            self.table.selectRow(target_row)
        else:
            self._on_table_selection_changed()

        # Всегда держим левый край таблицы на виду (колонка ФИО)
        self.table.horizontalScrollBar().setValue(0)
        self.debtors_changed.emit()

    def _switch_right_tab(self, index: int):
        self.right_stack.setCurrentIndex(index)
        self._update_tab_button_styles()

    def _on_table_selection_changed(self):
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            self.selected_debtor = None
            self.info_content.setText("Выберите должника из списка слева\nдля просмотра информации")
            self.deadlines_content.setText("Выберите должника для расчёта контрольных сроков.")
            self.script_text_edit.clear()
            self.btn_edit_selected.setEnabled(False)
            self.btn_delete_selected.setEnabled(False)
            self.btn_gen_consent.setEnabled(False)
            self.btn_gen_publications.setEnabled(False)
            return

        row = selected_rows[0].row()
        if 0 <= row < len(self.current_debtors):
            self.selected_debtor = self.current_debtors[row]
            self.btn_edit_selected.setEnabled(True)
            self.btn_delete_selected.setEnabled(True)
            self.btn_gen_consent.setEnabled(True)
            self.btn_gen_publications.setEnabled(True)
            self._render_debtor_info(self.selected_debtor)
            self._render_debtor_deadlines(self.selected_debtor)
            self._update_script_message_text()

    def _render_debtor_info(self, debtor: dict):
        text = export_debtor_to_text(debtor)
        self.info_content.setText(text)

    def _render_debtor_deadlines(self, debtor: dict):
        raw = debtor.get("parsed_raw") or {}
        dec_date_str = debtor.get("decision_date") or raw.get("decision_date") or ""

        if not dec_date_str:
            self.deadlines_content.setText(
                "<div style='font-size: 13px; color: #64748B; padding: 14px; background: #FFFFFF; border: 1px solid #E5E7EB; border-radius: 8px;'>"
                "<b>Дата решения суда не указана в карточке должника.</b><br><br>"
                "Для автоматического расчета дедлайнов (ЕФРСБ, Коммерсантъ, Запросы) "
                "нажмите <i>'Редактировать'</i> и укажите дату судебного акта."
                "</div>"
            )
            return

        dl = calculate_deadlines(dec_date_str)
        if not dl:
            self.deadlines_content.setText(
                f"<div style='font-size: 13px; color: #991B1B; padding: 14px; background: #FEE2E2; border-radius: 8px;'>"
                f"Не удалось распознать дату судебного акта: <b>{dec_date_str}</b>"
                "</div>"
            )
            return

        efrsb = dl["efrsb"]
        kom = dl["kommersant"]
        inq = dl["inquiries_start"]

        blocks = []

        # 1. ЕФРСБ (если не просрочен)
        if not efrsb.get("is_overdue", False):
            blocks.append(f"""
            <div style='padding: 14px 0; border-bottom: 1px solid #E5E7EB;'>
                <table style='width: 100%; border-collapse: collapse;'>
                    <tr>
                        <td style='vertical-align: middle;'>
                            <div style='font-size: 13px; font-weight: 700; color: #0F172A;'>{efrsb['title']}</div>
                        </td>
                        <td style='text-align: right; vertical-align: middle;'>
                            <span style='background-color: {efrsb['badge']['bg']}; color: {efrsb['badge']['color']}; padding: 3px 8px; border-radius: 12px; font-size: 11px; font-weight: 600;'>{efrsb['badge']['text']}</span>
                        </td>
                    </tr>
                </table>
                <div style='margin-top: 5px; font-size: 12px; color: #334155;'>
                    Крайний срок: <b>{efrsb['date']}</b>
                </div>
            </div>
            """)

        # 2. Коммерсантъ (если не просрочен)
        if not kom.get("is_overdue", False):
            blocks.append(f"""
            <div style='padding: 14px 0; border-bottom: 1px solid #E5E7EB;'>
                <table style='width: 100%; border-collapse: collapse;'>
                    <tr>
                        <td style='vertical-align: middle;'>
                            <div style='font-size: 13px; font-weight: 700; color: #0F172A;'>{kom['title']}</div>
                        </td>
                        <td style='text-align: right; vertical-align: middle;'>
                            <span style='background-color: {kom['badge']['bg']}; color: {kom['badge']['color']}; padding: 3px 8px; border-radius: 12px; font-size: 11px; font-weight: 600;'>{kom['badge']['text']}</span>
                        </td>
                    </tr>
                </table>
                <div style='margin-top: 5px; font-size: 12px; color: #334155;'>
                    Крайний срок: <b>{kom['date']}</b>
                </div>
            </div>
            """)

        # 3. Отправка запросов
        blocks.append(f"""
        <div style='padding-top: 14px;'>
            <table style='width: 100%; border-collapse: collapse;'>
                <tr>
                    <td style='vertical-align: middle;'>
                        <div style='font-size: 13px; font-weight: 700; color: #0F172A;'>{inq['title']}</div>
                    </td>
                    <td style='text-align: right; vertical-align: middle;'>
                        <span style='background-color: {inq['badge']['bg']}; color: {inq['badge']['color']}; padding: 3px 8px; border-radius: 12px; font-size: 11px; font-weight: 600;'>{inq['badge']['text']}</span>
                    </td>
                </tr>
            </table>
            <div style='margin-top: 5px; font-size: 12px; color: #334155;'>
                Доступно: с <b>{inq['date']}</b>
            </div>
        </div>
        """)

        stages_html = "\n".join(blocks)

        html = f"""
        <div style='font-family: Inter, Segoe UI, sans-serif; background-color: #FFFFFF; border: 1px solid #E5E7EB; border-radius: 8px; padding: 16px 18px; color: #1E293B;'>
            <!-- Верхняя строка: Дата решения суда -->
            <div style='padding-bottom: 12px; border-bottom: 1px solid #E5E7EB; font-size: 13px;'>
                <span style='color: #64748B;'>Дата решения суда:</span> <b style='color: #0F172A;'>{dl['decision_date']}</b>
            </div>

            {stages_html}
        </div>
        """
        self.deadlines_content.setText(html)

    def _rebuild_script_checkboxes(self):
        # Очищаем текущие чекбоксы
        while self.cb_grid_layout.count():
            item = self.cb_grid_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        self.script_checkboxes = []
        for key, label_text, default_checked in FIRST_CONTACT_DOCS:
            cb = QCheckBox(label_text)
            cb.setChecked(default_checked)
            cb.setStyleSheet("QCheckBox { font-size: 13px; color: #1E293B; spacing: 8px; }")
            cb.stateChanged.connect(self._update_script_message_text)
            self.script_checkboxes.append((cb, label_text))
            self.cb_grid_layout.addWidget(cb)

    def _update_script_message_text(self):
        if not self.selected_debtor:
            self.script_text_edit.clear()
            return

        fio = self.selected_debtor.get("full_name", "").strip()
        parts = fio.split()
        if len(parts) >= 2:
            first_name = parts[1]
        elif parts:
            first_name = parts[0]
        else:
            first_name = "Уважаемый клиент"

        needed_docs = []
        has_gosuslugi = False
        for cb, label_text in self.script_checkboxes:
            if cb.isChecked():
                if "госуслуг" in label_text.lower():
                    has_gosuslugi = True
                else:
                    needed_docs.append(label_text)

        lines = [
            f"{first_name}, здравствуйте! Меня зовут Валерия.\n",
            "Я буду писать заявление на ваше банкротство.\n",
            "Контакт передала Ксения.\n",
        ]

        if needed_docs or has_gosuslugi:
            lines.append("Для написания заявления отправьте пожалуйста фото или скан следующих документов:\n")
            for doc in needed_docs:
                lines.append(f"{doc}")
            lines.append("")

            if has_gosuslugi:
                lines.append("Логин и пароль от госуслуг")
                lines.append("Все остальные справки и документы будут скачиваться оттуда")
        else:
            lines.append("Все основные документы по списку уже получены. Спасибо!")

        self.script_text_edit.setPlainText("\n".join(lines))

    def _on_copy_script_clicked(self):
        text = self.script_text_edit.toPlainText().strip()
        if not text:
            return
        clipboard = QApplication.clipboard()
        clipboard.setText(text)

    def _generate_consent_doc(self):
        if not self.selected_debtor:
            return

        base_out = self.settings.output_dir
        if not os.path.exists(base_out):
            try:
                os.makedirs(base_out, exist_ok=True)
            except Exception:
                base_out = os.path.expanduser("~/Downloads")

        debtor_fio = self.selected_debtor.get("full_name", "").strip() or "Должник"
        mgr_fio = getattr(self.settings, "manager_fio", "") or "Гусарова Ксения Андреевна"

        short_mgr = format_short_fio(mgr_fio)
        short_debtor = format_short_fio(debtor_fio)

        # Файл: "Заявка АУ {Фамилия и инициалы фин управляющего}_{Фамилия и инициалы фин должника}.docx"
        filename = f"Заявка АУ {short_mgr}_{short_debtor}.docx"
        out_path = os.path.join(base_out, filename)
        pdf_path = os.path.splitext(out_path)[0] + ".pdf"

        try:
            generate_consent_doc(self.selected_debtor, self.settings, out_path)
            try:
                convert_word_to_pdf(out_path, pdf_path)
            except Exception as e_pdf:
                print(f"[Kartoteka] Ошибка конвертации согласия в PDF: {e_pdf}")

            count = 2 if os.path.exists(pdf_path) else 1
            dlg = InquirySuccessDialog(output_dir=base_out, inquiries_count=count, parent=self)
            dlg.setWindowTitle("Согласие сформировано - Арбитрум")
            dlg.exec()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка формирования", f"Не удалось создать заявление-согласие:\n{e}")

    def _generate_publications_docs(self):
        if not self.selected_debtor:
            return

        base_out = self.settings.output_dir
        if not os.path.exists(base_out):
            try:
                os.makedirs(base_out, exist_ok=True)
            except Exception:
                base_out = os.path.expanduser("~/Downloads")

        debtor_fio = self.selected_debtor.get("full_name", "").strip() or "Должник"
        safe_fio = debtor_fio.replace(" ", "_")
        target_dir = os.path.join(base_out, f"Публикации_{safe_fio}")
        os.makedirs(target_dir, exist_ok=True)

        kom_path = os.path.join(target_dir, f"Заявка_Коммерсантъ_{safe_fio}.docx")
        efrsb_path = os.path.join(target_dir, f"Сообщение_ЕФРСБ_{safe_fio}.docx")
        efrsb_pdf_path = os.path.join(target_dir, f"Сообщение_ЕФРСБ_{safe_fio}.pdf")

        try:
            generate_kommersant_doc(self.selected_debtor, self.settings, kom_path)
            generate_efrsb_doc(self.selected_debtor, self.settings, efrsb_path)
            try:
                convert_word_to_pdf(efrsb_path, efrsb_pdf_path)
            except Exception as e_pdf:
                print(f"[Kartoteka] Ошибка конвертации ЕФРСБ в PDF: {e_pdf}")

            count = 3 if os.path.exists(efrsb_pdf_path) else 2
            dlg = InquirySuccessDialog(output_dir=target_dir, inquiries_count=count, parent=self)
            dlg.setWindowTitle("Письма сформированы - Арбитрум")
            dlg.exec()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка формирования", f"Не удалось создать документы:\n{e}")

    def _on_table_double_clicked(self, item):
        self._edit_selected_debtor()

    def _on_add_manual(self):
        dlg = DebtorEditDialog(debtor_data={}, debtor_id=None, parent=self)
        dlg.debtor_saved.connect(self._save_new_debtor)
        dlg.exec()

    def _save_new_debtor(self, data: dict):
        new_id = self.db_manager.save_debtor_full(data, debtor_id=None)
        self.refresh_table(select_debtor_id=new_id)

    def _edit_selected_debtor(self):
        if not self.selected_debtor:
            return
        debtor_id = self.selected_debtor["id"]
        raw = self.selected_debtor.get("parsed_raw") or {}
        combined = dict(self.selected_debtor)
        combined.update(raw)

        dlg = DebtorEditDialog(debtor_data=combined, debtor_id=debtor_id, parent=self)
        dlg.debtor_saved.connect(lambda d: self._save_edited_debtor(d, debtor_id))
        dlg.exec()

    def _save_edited_debtor(self, data: dict, debtor_id: int):
        self.db_manager.save_debtor_full(data, debtor_id=debtor_id)
        self.refresh_table(select_debtor_id=debtor_id)

    def _delete_selected_debtor(self):
        if not self.selected_debtor:
            return
        debtor_id = self.selected_debtor["id"]
        name = self.selected_debtor.get("full_name", "должника")
        
        box = QMessageBox(self)
        box.setWindowTitle("Удаление должника")
        box.setIcon(QMessageBox.Question)
        box.setText(f"Вы уверены, что хотите удалить карточку:\n{name}?")
        btn_yes = box.addButton("Да", QMessageBox.YesRole)
        btn_no = box.addButton("Нет", QMessageBox.NoRole)
        box.setDefaultButton(btn_no)
        box.exec()

        if box.clickedButton() == btn_yes:
            self.db_manager.delete_debtor(debtor_id)
            self.refresh_table()

    def _open_court_file_dialog(self):
        fpath, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите судебный акт для картотеки",
            "",
            "Судебные акты (*.pdf *.docx *.doc);;Все файлы (*.*)"
        )
        if fpath:
            self._import_from_court_file(fpath)

    def _import_from_court_file(self, fpath: str):
        try:
            parsed = parse_court_decision(fpath)
            dlg = DebtorEditDialog(debtor_data=parsed, debtor_id=None, parent=self)
            dlg.debtor_saved.connect(self._save_new_debtor)
            dlg.exec()
        except Exception as e:
            QMessageBox.warning(self, "Ошибка разбора файла", f"Не удалось автоматически извлечь данные:\n{e}")

    def _on_export_clicked(self):
        if not self.selected_debtor:
            QMessageBox.information(self, "Экспорт", "Выберите должника в таблице для экспорта данных.")
            return

        debtor_fio = self.selected_debtor.get("full_name", "").strip() or "Без имени"
        box = QMessageBox(self)
        box.setWindowTitle("Экспорт данных")
        box.setIcon(QMessageBox.Question)
        box.setText(f"Экспортировать данные о должнике {debtor_fio}?")
        btn_yes = box.addButton("Да", QMessageBox.YesRole)
        btn_no = box.addButton("Нет", QMessageBox.NoRole)
        box.setDefaultButton(btn_yes)
        box.exec()

        if box.clickedButton() != btn_yes:
            return

        default_name = f"должник_{debtor_fio}.txt"
        fpath, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить данные должника",
            default_name,
            "Текстовые файлы (*.txt);;Все файлы (*.*)"
        )
        if not fpath:
            return

        try:
            text = export_debtor_to_text(self.selected_debtor)
            with open(fpath, "w", encoding="utf-8") as f:
                f.write(text)
            QMessageBox.information(self, "Экспорт", f"Данные успешно сохранены в файл:\n{fpath}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка экспорта", f"Не удалось сохранить файл:\n{e}")

    def _import_from_text_file(self):
        fpath, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите файл для импорта в картотеку",
            "",
            "Все поддерживаемые форматы (*.txt *.db *.sqlite *.zip);;Текстовые файлы (*.txt);;Базы данных и архивы (*.db *.sqlite *.zip);;Все файлы (*.*)"
        )
        if not fpath:
            return

        ext = os.path.splitext(fpath)[1].lower()

        # Если это файл базы данных SQLite или zip-архив с базой
        if ext in [".db", ".sqlite", ".zip"]:
            try:
                res = self.db_manager.import_from_archive_or_db(fpath)
                self.refresh_table()
                msg = (
                    f"Импорт и объединение данных завершены успешно!\n\n"
                    f"• Добавлено новых должников: {res['added']}\n"
                    f"• Дополнено существующих карточек: {res['updated']}\n"
                    f"• Пропущено полных дубликатов: {res['skipped']}\n"
                    f"• Всего обработано из файла: {res['total_source']}"
                )
                QMessageBox.information(self, "Импорт базы данных", msg)
            except Exception as e:
                QMessageBox.critical(self, "Ошибка импорта", f"Не удалось импортировать файл базы данных:\n{e}")
            return

        # Иначе текстовый файл
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()

            records = parse_debtor_from_text(content)
            if not records:
                QMessageBox.warning(self, "Импорт", "В файле не найдено корректных сведений о должниках.")
                return

            if len(records) == 1:
                dlg = DebtorEditDialog(debtor_data=records[0], debtor_id=None, parent=self)
                dlg.debtor_saved.connect(self._save_new_debtor)
                dlg.exec()
            else:
                added_count = 0
                for r in records:
                    self.db_manager.save_debtor_full(r, debtor_id=None)
                    added_count += 1
                self.refresh_table()
                QMessageBox.information(self, "Импорт", f"Успешно импортировано {added_count} записей в базу данных.")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка импорта", f"Не удалось прочитать файл:\n{e}")
