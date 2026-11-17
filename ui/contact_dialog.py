from PySide6.QtCore import Qt, QPoint
from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QCheckBox, QTextEdit, QPushButton, QFrame, QApplication
)
from PySide6.QtGui import QIcon, QFont, QColor, QPainter, QPixmap

STANDARD_DOCS = [
    ("pass", "Паспорт гражданина РФ (все страницы со штампами)", True),
    ("snils_inn", "СНИЛС и свидетельство ИНН", True),
    ("marriage", "Свидетельство о заключении / расторжении брака", True),
    ("ndfl", "Справки о доходах (2-НДФЛ) за последние 3 года", True),
    ("work_book", "Копия трудовой книжки (или выписка СТД-ПФР/СФР)", True),
    ("bank_stmts", "Выписки по открытым счетам и картам за 3 года", False),
    ("credit_agrs", "Кредитные договоры и графики платежей", False),
    ("property", "Документы на имущество (квартира, дом, автомобиль)", False),
]


class FirstContactDialog(QDialog):
    """
    Модальное окно генерации первого сообщения должнику.
    Слева: чекбоксы со списком документов.
    Справа: поле с редактируемым текстом сообщения и кнопкой копирования.
    """
    def __init__(self, debtor_data: dict, manager_fio: str = "", parent=None):
        super().__init__(parent)
        self.debtor_data = debtor_data or {}
        self.manager_fio = manager_fio or "арбитражного управляющего"

        # Frameless with custom title bar or clean dialog
        self.setWindowTitle("Генератор сообщения клиенту")
        self.resize(740, 460)
        self.setMinimumSize(600, 380)

        self.checkboxes = []
        self._init_ui()
        self._update_text()

    def _init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(18, 14, 18, 16)
        root_layout.setSpacing(12)

        # Header bar
        header_bar = QHBoxLayout()
        title_lbl = QLabel("Генератор сообщения клиенту")
        title_lbl.setStyleSheet("font-size: 15px; font-weight: 700; color: #0F172A;")
        header_bar.addWidget(title_lbl)
        header_bar.addStretch()

        btn_close = QPushButton("✕", self)
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.setFixedSize(28, 28)
        btn_close.setStyleSheet(
            "QPushButton { border: none; background: transparent; color: #64748B; font-size: 15px; font-weight: bold; border-radius: 6px; } "
            "QPushButton:hover { background-color: #FEE2E2; color: #DC2626; }"
        )
        btn_close.clicked.connect(self.accept)
        header_bar.addWidget(btn_close)
        root_layout.addLayout(header_bar)

        # Content horizontal layout (Left checkboxes, Right text edit)
        content_layout = QHBoxLayout()
        content_layout.setSpacing(16)

        # Left: Checkboxes panel
        left_frame = QFrame()
        left_frame.setStyleSheet(
            "QFrame { background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 10px; }"
        )
        left_layout = QVBoxLayout(left_frame)
        left_layout.setContentsMargins(8, 8, 8, 8)
        left_layout.setSpacing(10)

        lbl_check_title = QLabel("Какие документы запросить:")
        lbl_check_title.setStyleSheet("font-size: 12px; font-weight: 700; color: #334155; border: none; background: transparent;")
        left_layout.addWidget(lbl_check_title)

        for key, label_text, default_checked in STANDARD_DOCS:
            cb = QCheckBox(label_text)
            cb.setChecked(default_checked)
            cb.setStyleSheet("QCheckBox { font-size: 12px; color: #1E293B; spacing: 6px; border: none; background: transparent; }")
            cb.stateChanged.connect(self._update_text)
            self.checkboxes.append((cb, label_text))
            left_layout.addWidget(cb)

        left_layout.addStretch()
        content_layout.addWidget(left_frame, stretch=1)

        # Right: Text container with copy icon at top-right
        right_container = QFrame()
        right_container.setStyleSheet(
            "QFrame { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; }"
        )
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(10, 8, 10, 10)
        right_layout.setSpacing(6)

        # Top bar of right container (Title + Copy Icon)
        right_top = QHBoxLayout()
        lbl_preview = QLabel("Текст сообщения:")
        lbl_preview.setStyleSheet("font-size: 12px; font-weight: 700; color: #334155; border: none;")
        right_top.addWidget(lbl_preview)
        right_top.addStretch()

        self.btn_copy = QPushButton("📋", right_container)
        self.btn_copy.setCursor(Qt.PointingHandCursor)
        self.btn_copy.setToolTip("Копировать в буфер обмена")
        self.btn_copy.setFixedSize(30, 30)
        self.btn_copy.setStyleSheet(
            "QPushButton { border: 1px solid #CBD5E1; background: #F8FAFC; border-radius: 6px; font-size: 14px; } "
            "QPushButton:hover { background-color: #E2E8F0; border-color: #94A3B8; }"
        )
        self.btn_copy.clicked.connect(self._copy_to_clipboard)
        right_top.addWidget(self.btn_copy)
        right_layout.addLayout(right_top)

        self.text_edit = QTextEdit()
        self.text_edit.setStyleSheet(
            "QTextEdit { border: none; font-size: 12px; color: #0F172A; line-height: 1.4; background: transparent; }"
        )
        right_layout.addWidget(self.text_edit, stretch=1)

        content_layout.addWidget(right_container, stretch=1)
        root_layout.addLayout(content_layout, stretch=1)

    def _update_text(self):
        fio = self.debtor_data.get("full_name", "").strip()
        parts = fio.split()
        if len(parts) >= 2:
            first_name = parts[1]
        elif parts:
            first_name = parts[0]
        else:
            first_name = "Уважаемый клиент"

        case_no = self.debtor_data.get("case_number", "").strip()
        case_part = f" по делу № {case_no}" if case_no else ""

        # Collect checked documents
        needed_docs = []
        for cb, label_text in self.checkboxes:
            if cb.isChecked():
                needed_docs.append(label_text)

        lines = [
            f"Здравствуйте, {first_name}!\n",
            f"Я помощник финансового управляющего ({self.manager_fio}). "
            f"Мы начинаем процедуру подготовки документов к вашему банкротству{case_part}.\n"
        ]

        if needed_docs:
            lines.append("Пожалуйста, направьте мне качественные фото или сканы следующих документов:")
            for i, doc in enumerate(needed_docs, 1):
                lines.append(f"{i}. {doc};")
            lines.append("")
        else:
            lines.append("Все основные документы по списку уже получены. Спасибо!\n")

        lines.append("Если у вас возникнут вопросы по списку документов — я на связи!")

        self.text_edit.setPlainText("\n".join(lines))

    def _copy_to_clipboard(self):
        text = self.text_edit.toPlainText()
        clipboard = QApplication.clipboard()
        clipboard.setText(text)

        # Temporary visual feedback on copy button
        self.btn_copy.setText("✓")
        self.btn_copy.setStyleSheet(
            "QPushButton { border: 1px solid #16A34A; background: #DCFCE7; color: #16A34A; border-radius: 6px; font-size: 14px; font-weight: bold; }"
        )
