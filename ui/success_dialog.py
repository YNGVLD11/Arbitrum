import os
import subprocess
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame
)
from core.validator import RussianPostValidator
from ui.file_list import format_file_size
from ui.themes import get_app_icon


class BuildSuccessDialog(QDialog):
    """
    Диалог успешного завершения сборки отчета с автоматической валидацией
    на соответствие требованиям сервиса zakaznoe.pochta.ru.
    """
    def __init__(self, result_meta: dict, parent=None):
        super().__init__(parent)
        self.result_meta = result_meta
        self.output_path = result_meta.get("output_path", "")

        self.setWindowTitle("Сборка отчёта завершена")
        self.setWindowIcon(get_app_icon())
        self.setFixedSize(500, 360)
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)

        self._init_ui()

    def closeEvent(self, event):
        self.accept()
        event.accept()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        # Заголовок
        title_layout = QVBoxLayout()
        title_layout.setSpacing(2)

        is_docx = self.output_path.lower().endswith(".docx")
        layout_mode = self.result_meta.get("layout_mode", "2up")

        if is_docx:
            t_txt = "Word-документ успешно собран"
            s_txt = "Документы объединены в единый файл Word (.docx)"
        elif layout_mode == "standard":
            t_txt = "PDF-документ успешно собран"
            s_txt = "Документы объединены по одной странице на лист"
        else:
            t_txt = "PDF-документ успешно собран"
            s_txt = "Файл скомпонован в формате A4 2 страницы на листе"

        title_lbl = QLabel(t_txt)
        title_lbl.setStyleSheet("font-size: 16px; font-weight: 700; color: #16A34A;")
        title_layout.addWidget(title_lbl)

        sub_lbl = QLabel(s_txt)
        sub_lbl.setStyleSheet("color: #64748B; font-size: 11px;")
        title_layout.addWidget(sub_lbl)
        layout.addLayout(title_layout)

        # Карточка сведений о файле
        card = QFrame()
        card.setObjectName("cardFrame")
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(4)

        fname = os.path.basename(self.output_path)
        name_lbl = QLabel(f"<b>{fname}</b>")
        card_layout.addWidget(name_lbl)

        sheets = self.result_meta.get("total_sheets", 0)
        pages = self.result_meta.get("total_input_pages", 0) or self.result_meta.get("total_source_pages", 0)
        size = format_file_size(self.result_meta.get("file_size", 0) or self.result_meta.get("output_size_bytes", 0))

        if is_docx or layout_mode == "standard":
            d_txt = f"Страниц: <b>{pages}</b>  •  Размер: <b>{size}</b>"
        else:
            d_txt = f"Листов A4 (2-up): <b>{sheets}</b>  •  Исходных страниц: <b>{pages}</b>  •  Размер: <b>{size}</b>"

        details_lbl = QLabel(d_txt)
        details_lbl.setStyleSheet("color: #475569; font-size: 12px;")
        card_layout.addWidget(details_lbl)

        path_lbl = QLabel(f"Путь: {self.output_path}")
        path_lbl.setStyleSheet("color: #94A3B8; font-size: 11px;")
        path_lbl.setWordWrap(True)
        card_layout.addWidget(path_lbl)

        layout.addWidget(card)

        # Блок валидации для сервиса zakaznoe.pochta.ru
        if not is_docx and os.path.isfile(self.output_path):
            val_res = RussianPostValidator.validate_pdf(self.output_path)
            val_card = QFrame()
            val_layout = QVBoxLayout(val_card)
            val_layout.setContentsMargins(12, 10, 12, 10)
            val_layout.setSpacing(4)

            if val_res.is_valid and not val_res.warnings:
                val_card.setStyleSheet(
                    "background: #F0FDF4; border: 1px solid #BBF7D0; border-radius: 8px;"
                )
                status_header = QLabel("Соответствие zakaznoe.pochta.ru: подтверждено")
                status_header.setStyleSheet("color: #15803D; font-weight: 700; font-size: 12px;")
                val_layout.addWidget(status_header)

                desc_text = (
                    f"Листов: {val_res.page_count} (лимит 19) • "
                    f"Размер: {val_res.file_size_mb:.2f} МБ (лимит 20 МБ) • "
                    f"Формат: А4 книжный (210 x 297 мм)"
                )
                desc_lbl = QLabel(desc_text)
                desc_lbl.setStyleSheet("color: #166534; font-size: 11px;")
                val_layout.addWidget(desc_lbl)
            elif val_res.is_valid and val_res.warnings:
                val_card.setStyleSheet(
                    "background: #FFFBEB; border: 1px solid #FDE68A; border-radius: 8px;"
                )
                status_header = QLabel("Соответствие zakaznoe.pochta.ru: предупреждение")
                status_header.setStyleSheet("color: #B45309; font-weight: 700; font-size: 12px;")
                val_layout.addWidget(status_header)

                for w in val_res.warnings:
                    w_lbl = QLabel(w)
                    w_lbl.setStyleSheet("color: #92400E; font-size: 11px;")
                    w_lbl.setWordWrap(True)
                    val_layout.addWidget(w_lbl)
            else:
                val_card.setStyleSheet(
                    "background: #FEF2F2; border: 1px solid #FECACA; border-radius: 8px;"
                )
                status_header = QLabel("Соответствие zakaznoe.pochta.ru: не пройдено")
                status_header.setStyleSheet("color: #B91C1C; font-weight: 700; font-size: 12px;")
                val_layout.addWidget(status_header)

                for err in val_res.errors[:3]:
                    err_lbl = QLabel(f"• {err}")
                    err_lbl.setStyleSheet("color: #991B1B; font-size: 11px;")
                    err_lbl.setWordWrap(True)
                    val_layout.addWidget(err_lbl)

            layout.addWidget(val_card)

        layout.addStretch()

        # Кнопки действий
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self.open_file_btn = QPushButton("Открыть файл")
        self.open_file_btn.setObjectName("primaryButton")
        self.open_file_btn.clicked.connect(self._open_file)
        btn_layout.addWidget(self.open_file_btn)

        self.show_folder_btn = QPushButton("Показать в папке")
        self.show_folder_btn.clicked.connect(self._show_in_folder)
        btn_layout.addWidget(self.show_folder_btn)

        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

    def _open_file(self):
        if os.path.exists(self.output_path):
            try:
                os.startfile(os.path.abspath(self.output_path))
            except Exception as e:
                print("Error opening file:", e)
        self.accept()

    def _show_in_folder(self):
        if os.path.exists(self.output_path):
            try:
                subprocess.Popen(f'explorer /select,"{os.path.abspath(self.output_path)}"')
            except Exception as e:
                print("Error opening explorer:", e)
        self.accept()
