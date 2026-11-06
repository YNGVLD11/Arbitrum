import os
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
)
from PySide6.QtGui import QFont
from ui.themes import get_app_icon


class InquirySuccessDialog(QDialog):
    """
    Modal success dialog shown after inquiry documents are generated.
    Displays target directory and count of inquiries with 'Открыть папку' and 'Закрыть'.
    """
    def __init__(self, output_dir: str, inquiries_count: int, parent=None):
        super().__init__(parent)
        self.output_dir = output_dir
        self.inquiries_count = inquiries_count

        self.setWindowTitle("Запросы сформированы - Арбитум")
        self.setWindowIcon(get_app_icon())
        self.setFixedSize(500, 240)
        self.setModal(True)

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # Header with clean icon and title
        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)

        icon_lbl = QLabel("📁")
        icon_lbl.setStyleSheet("font-size: 32px;")
        header_layout.addWidget(icon_lbl)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)

        title_lbl = QLabel("Запросы успешно сформированы!")
        title_lbl.setObjectName("headerTitle")
        title_font = QFont("Segoe UI", 14, QFont.Bold)
        title_lbl.setFont(title_font)

        sub_lbl = QLabel("Пакет документов подготовлен и сохранен")
        sub_lbl.setObjectName("subTitle")

        title_col.addWidget(title_lbl)
        title_col.addWidget(sub_lbl)
        header_layout.addLayout(title_col)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Info Card
        card = QFrame()
        card.setObjectName("cardFrame")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(14, 12, 14, 12)
        card_layout.setSpacing(6)

        folder_name = os.path.basename(self.output_dir)
        folder_lbl = QLabel(folder_name)
        folder_lbl.setObjectName("headerTitle")
        card_layout.addWidget(folder_lbl)

        stats_lbl = QLabel(f"Сформировано файлов: {self.inquiries_count} ведомств")
        stats_lbl.setObjectName("successHighlight")
        card_layout.addWidget(stats_lbl)

        path_lbl = QLabel(f"Путь: {self.output_dir}")
        path_lbl.setStyleSheet("color: #94A3B8; font-size: 11px;")
        path_lbl.setWordWrap(True)
        card_layout.addWidget(path_lbl)

        layout.addWidget(card)

        # Bottom Buttons: ONLY "Открыть папку" and "Закрыть"
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        btn_layout.addStretch()

        self.btn_open_folder = QPushButton("Открыть папку")
        self.btn_open_folder.setObjectName("primaryButton")
        self.btn_open_folder.setCursor(Qt.PointingHandCursor)
        self.btn_open_folder.clicked.connect(self._open_folder)
        btn_layout.addWidget(self.btn_open_folder)

        self.btn_close = QPushButton("Закрыть")
        self.btn_close.setCursor(Qt.PointingHandCursor)
        self.btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(self.btn_close)

        layout.addLayout(btn_layout)

    def _open_folder(self):
        if os.path.exists(self.output_dir):
            try:
                os.startfile(self.output_dir)
            except Exception:
                pass
        self.accept()
