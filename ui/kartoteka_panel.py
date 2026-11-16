import os
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QFrame,
    QFileDialog, QMessageBox, QScrollArea, QSplitter
)
from core.database import DatabaseManager
from core.court_parser import parse_court_decision
from core.debtor_exporter import (
    export_debtor_to_text, export_all_debtors_to_text, parse_debtor_from_text
)
from ui.debtor_dialog import DebtorEditDialog


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
    """
    Модуль 3: Картотека должников.
    - Таблица: ID, ФИО, Номер дела, Адрес прописки.
    - Правая колонка: подробная информация о выбранном должнике списком.
    - Модалка редактирования/создания (двойной клик или кнопка).
    - Загрузка судебного акта (драгндроп или кнопка) с открытием модалки.
    - Экспорт/импорт в текстовые файлы 'поле: значение'.
    """
    debtor_selected_for_inquiry = Signal(dict)
    debtors_changed = Signal()

    def __init__(self, db_manager: DatabaseManager, settings, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.settings = settings
        self.current_debtors = []
        self.selected_debtor = None

        self._init_ui()
        self.refresh_table()

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

        # Слева: Кнопка "+ Добавить должника вручную" и под ней Импорт/Экспорт
        btn_col = QVBoxLayout()
        btn_col.setSpacing(6)

        self.btn_add_manual = QPushButton("+ Добавить должника вручную", self)
        self.btn_add_manual.setObjectName("mainBuildButton")
        self.btn_add_manual.setCursor(Qt.PointingHandCursor)
        self.btn_add_manual.clicked.connect(self._on_add_manual)
        btn_col.addWidget(self.btn_add_manual)

        exp_imp_layout = QHBoxLayout()
        exp_imp_layout.setSpacing(6)

        self.btn_import_txt = QPushButton("Импорт из TXT", self)
        self.btn_import_txt.setCursor(Qt.PointingHandCursor)
        self.btn_import_txt.clicked.connect(self._import_from_text_file)
        exp_imp_layout.addWidget(self.btn_import_txt)

        self.btn_export_txt = QPushButton("Экспорт", self)
        self.btn_export_txt.setCursor(Qt.PointingHandCursor)
        self.btn_export_txt.clicked.connect(self._on_export_clicked)
        exp_imp_layout.addWidget(self.btn_export_txt)

        btn_col.addLayout(exp_imp_layout)
        top_card_layout.addLayout(btn_col, stretch=2)

        # Справа: Блок "Перетащите решение суда..."
        self.drop_area = KartotekaDropArea(self)
        self.drop_area.file_dropped.connect(self._import_from_court_file)
        self.drop_area.clicked.connect(self._open_court_file_dialog)
        top_card_layout.addWidget(self.drop_area, stretch=3)

        main_layout.addWidget(top_card)

        # Центральный сплиттер: Слева таблица должников, справа подробная карточка
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(12)
        splitter.setChildrenCollapsible(False)

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
        self.btn_edit_selected = QPushButton("Редактировать")
        self.btn_edit_selected.clicked.connect(self._edit_selected_debtor)
        self.btn_edit_selected.setEnabled(False)
        tbl_actions.addWidget(self.btn_edit_selected)

        self.btn_delete_selected = QPushButton("Удалить")
        self.btn_delete_selected.setObjectName("dangerButton")
        self.btn_delete_selected.clicked.connect(self._delete_selected_debtor)
        self.btn_delete_selected.setEnabled(False)
        tbl_actions.addWidget(self.btn_delete_selected)

        tbl_actions.addStretch()
        table_layout.addLayout(tbl_actions)

        splitter.addWidget(table_frame)

        # Правая часть: Подробная информация списком
        info_frame = QFrame()
        info_frame.setObjectName("cardFrame")
        info_layout = QVBoxLayout(info_frame)
        info_layout.setContentsMargins(14, 12, 14, 12)
        info_layout.setSpacing(8)

        lbl_info_title = QLabel("Информация о должнике")
        lbl_info_title.setObjectName("cardTitle")
        info_layout.addWidget(lbl_info_title)

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
        info_scroll.setWidget(self.info_content)
        info_layout.addWidget(info_scroll, stretch=1)

        splitter.addWidget(info_frame)
        splitter.setSizes([620, 380])

        main_layout.addWidget(splitter, stretch=1)

    def refresh_table(self, select_debtor_id: int = None):
        """Перезагружает список должников из базы данных в таблицу и при необходимости выбирает запись."""
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
            self.table.scrollToItem(self.table.item(target_row, 1))
        else:
            self._on_table_selection_changed()

        self.debtors_changed.emit()

    def _on_table_selection_changed(self):
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            self.selected_debtor = None
            self.info_content.setText("Выберите должника из списка слева\nдля просмотра информации")
            self.btn_edit_selected.setEnabled(False)
            self.btn_delete_selected.setEnabled(False)
            return

        row = selected_rows[0].row()
        if 0 <= row < len(self.current_debtors):
            self.selected_debtor = self.current_debtors[row]
            self.btn_edit_selected.setEnabled(True)
            self.btn_delete_selected.setEnabled(True)
            self._render_debtor_info(self.selected_debtor)

    def _render_debtor_info(self, debtor: dict):
        text = export_debtor_to_text(debtor)
        self.info_content.setText(text)

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
        ans = QMessageBox.question(
            self,
            "Удаление должника",
            f"Вы уверены, что хотите удалить карточку:\n{name} (ID {debtor_id})?",
            QMessageBox.Yes | QMessageBox.No
        )
        if ans == QMessageBox.Yes:
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
        ans = QMessageBox.question(
            self,
            "Экспорт данных",
            f"Экспортировать данные о должнике {debtor_fio}?",
            QMessageBox.Yes | QMessageBox.No
        )
        if ans != QMessageBox.Yes:
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
            "Выберите текстовый файл для импорта",
            "",
            "Текстовые файлы (*.txt);;Все файлы (*.*)"
        )
        if not fpath:
            return

        try:
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()

            records = parse_debtor_from_text(content)
            if not records:
                QMessageBox.warning(self, "Импорт", "В файле не найдено корректных сведений о должниках.")
                return

            if len(records) == 1:
                # Открываем модалку для подтверждения/редактирования
                dlg = DebtorEditDialog(debtor_data=records[0], debtor_id=None, parent=self)
                dlg.debtor_saved.connect(self._save_new_debtor)
                dlg.exec()
            else:
                # Пакетное добавление
                added_count = 0
                for r in records:
                    self.db_manager.save_debtor_full(r, debtor_id=None)
                    added_count += 1
                self.refresh_table()
                QMessageBox.information(self, "Импорт", f"Успешно импортировано {added_count} записей в базу данных.")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка импорта", f"Не удалось прочитать файл:\n{e}")
