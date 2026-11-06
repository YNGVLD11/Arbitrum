from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar,
    QPushButton, QFrame
)
from ui.themes import get_app_icon


class BuildProgressDialog(QDialog):
    """
    Modal progress window that blocks the main interface during PDF compilation.
    """
    cancel_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Сборка отчёта...")
        self.setWindowIcon(get_app_icon())
        self.setWindowModality(Qt.ApplicationModal)
        self.setFixedSize(460, 200)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint & ~Qt.WindowCloseButtonHint)

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        # Title with gear/document icon
        header_layout = QHBoxLayout()
        icon_lbl = QLabel("⚙️")
        icon_lbl.setStyleSheet("font-size: 22px;")
        header_layout.addWidget(icon_lbl)

        self.title_lbl = QLabel("Формирование единого PDF-документа")
        self.title_lbl.setStyleSheet("font-size: 15px; font-weight: 700;")
        header_layout.addWidget(self.title_lbl, stretch=1)
        layout.addLayout(header_layout)

        # Sub-status description
        self.status_lbl = QLabel("Инициализация сборки...")
        self.status_lbl.setStyleSheet("color: #64748B; font-size: 12px;")
        self.status_lbl.setWordWrap(True)
        layout.addWidget(self.status_lbl)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(18)
        layout.addWidget(self.progress_bar)

        # Bottom row with cancel button
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()

        self.cancel_btn = QPushButton("Отмена")
        self.cancel_btn.clicked.connect(self._on_cancel)
        bottom_layout.addWidget(self.cancel_btn)

        layout.addLayout(bottom_layout)

    def set_progress(self, percent: int, message: str):
        self.progress_bar.setValue(percent)
        self.status_lbl.setText(message)

    def _on_cancel(self):
        self.cancel_btn.setEnabled(False)
        self.status_lbl.setText("Отмена операции, пожалуйста подождите...")
        self.cancel_requested.emit()
