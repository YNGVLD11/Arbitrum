import os
import datetime
from PySide6.QtCore import Qt, QThread, Signal, QRectF
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QSplitter, QMessageBox, QApplication
)
from PySide6.QtGui import QPainter

from ui.themes import (
    THEME_LIGHT, THEME_FEMININE, LIGHT_QSS, FEMININE_QSS,
    FeminineBackgroundPainter, SkyBackgroundPainter, get_app_icon
)
from ui.file_list import FileListPanel
from ui.preview_panel import DocumentPreviewPanel
from ui.settings_dialog import SettingsDialog, AppSettings
from ui.progress_dialog import BuildProgressDialog
from ui.success_dialog import BuildSuccessDialog
from core.converter import build_arbitr_report


class BuildWorker(QThread):
    """
    Background worker thread for PDF compilation and Word conversion.
    """
    progress = Signal(int, str)
    finished = Signal(dict)
    failed = Signal(str)

    def __init__(self, file_paths: list[str], output_path: str, new_sheet_for_landscape: bool):
        super().__init__()
        self.file_paths = file_paths
        self.output_path = output_path
        self.new_sheet_for_landscape = new_sheet_for_landscape
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        try:
            res = build_arbitr_report(
                file_paths=self.file_paths,
                output_path=self.output_path,
                progress_callback=self._on_progress,
                is_cancelled=lambda: self._is_cancelled,
                new_sheet_for_landscape=self.new_sheet_for_landscape
            )
            self.finished.emit(res)
        except Exception as e:
            self.failed.emit(str(e))

    def _on_progress(self, percent: int, message: str):
        self.progress.emit(percent, message)


class MainWindow(QMainWindow):
    """
    Main Application Window.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Мастер сборки отчета АУ")
        self.resize(1100, 720)
        self.setMinimumSize(920, 580)
        self.setWindowIcon(get_app_icon())

        self.app_settings = AppSettings()
        self.feminine_painter = FeminineBackgroundPainter()
        self.sky_painter = SkyBackgroundPainter()
        self.current_theme = self.app_settings.theme
        self.worker = None

        self._init_ui()
        self._apply_theme(self.current_theme)

    def _init_ui(self):
        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)

        root_layout = QVBoxLayout(self.central_widget)
        root_layout.setContentsMargins(18, 12, 18, 16)
        root_layout.setSpacing(10)

        # 1. Minimal Top Bar: No title text, only gear ⚙️ button aligned to the right (Big & Easy to click)
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(0, 0, 0, 0)
        top_bar.addStretch()

        self.settings_btn = QPushButton("⚙️")
        self.settings_btn.setObjectName("settingsButton")
        self.settings_btn.setFixedSize(48, 44)
        self.settings_btn.setToolTip("Настройки")
        self.settings_btn.clicked.connect(self._open_settings)
        top_bar.addWidget(self.settings_btn)

        root_layout.addLayout(top_bar)

        # 2. Central Splitter (List 2/3 on Left, Preview 1/3 on Right)
        # Extra-wide gap between cards (22px)
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setHandleWidth(22)
        self.splitter.setChildrenCollapsible(False)

        # Left: File List Panel (2/3 of width)
        self.file_list_panel = FileListPanel(theme=self.current_theme, parent=self)
        self.file_list_panel.file_selected.connect(self._on_file_selected)
        self.file_list_panel.file_list_changed.connect(self._update_build_button_state)
        self.splitter.addWidget(self.file_list_panel)

        # Right: Document Preview Panel (1/3 of width)
        self.preview_panel = DocumentPreviewPanel(self)
        self.splitter.addWidget(self.preview_panel)

        # Splitter proportion: 2/3 (list) to 1/3 (preview)
        self.splitter.setSizes([720, 360])
        root_layout.addWidget(self.splitter, stretch=1)

        # 3. Bottom Action Bar: Centered "Собрать pdf-файл" button
        bottom_layout = QHBoxLayout()
        bottom_layout.setContentsMargins(0, 6, 0, 0)

        bottom_layout.addStretch()

        self.build_btn = QPushButton("Собрать pdf-файл")
        self.build_btn.setObjectName("mainBuildButton")
        self.build_btn.clicked.connect(self._start_build)
        bottom_layout.addWidget(self.build_btn)

        bottom_layout.addStretch()

        root_layout.addLayout(bottom_layout)

        self._update_build_button_state()

    def closeEvent(self, event):
        if hasattr(self, "preview_panel") and hasattr(self.preview_panel, "preview_worker"):
            self.preview_panel.preview_worker.stop()
        super().closeEvent(event)

    def mousePressEvent(self, event):
        pos = event.position().toPoint()
        child = self.childAt(pos)
        # Click anywhere outside the list cards to clear card selection
        if child is None or not self.file_list_panel.list_widget.isAncestorOf(child):
            self.file_list_panel.clear_selection()
        super().mousePressEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        if self.current_theme == THEME_FEMININE:
            self.feminine_painter.draw(painter, QRectF(self.rect()))
        else:
            self.sky_painter.draw(painter, QRectF(self.rect()))
        painter.end()

    def _apply_theme(self, theme_name: str):
        self.current_theme = theme_name
        app = QApplication.instance()
        if theme_name == THEME_FEMININE:
            app.setStyleSheet(FEMININE_QSS)
        else:
            app.setStyleSheet(LIGHT_QSS)

        self.file_list_panel.set_theme(theme_name)
        if hasattr(self, "preview_panel"):
            self.preview_panel.set_theme(theme_name)
        self.update()

    def _open_settings(self):
        dlg = SettingsDialog(self)
        dlg.settings_saved.connect(self._on_settings_saved)
        dlg.exec()

    def _on_settings_saved(self):
        new_theme = self.app_settings.theme
        if new_theme != self.current_theme:
            self._apply_theme(new_theme)

    def _on_file_selected(self, file_path: str):
        self.preview_panel.set_document(file_path)

    def _update_build_button_state(self):
        paths = self.file_list_panel.get_file_paths()
        count = len(paths)
        self.build_btn.setEnabled(count > 0)
        if count == 0:
            self.preview_panel.clear_preview()
        elif self.file_list_panel.list_widget.currentRow() < 0:
            self.file_list_panel.list_widget.setCurrentRow(0)

    def _start_build(self):
        paths = self.file_list_panel.get_file_paths()
        if not paths:
            QMessageBox.warning(self, "Внимание", "Добавьте хотя бы один файл для сборки отчета.")
            return

        out_dir = self.app_settings.output_dir
        if not os.path.exists(out_dir):
            try:
                os.makedirs(out_dir, exist_ok=True)
            except Exception as e:
                QMessageBox.critical(self, "Ошибка папки", f"Не удалось создать папку:\n{out_dir}\n{e}")
                return

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        out_filename = f"Отчет_АУ_{timestamp}.pdf"
        out_path = os.path.join(out_dir, out_filename)

        # Modal progress dialog
        self.progress_dlg = BuildProgressDialog(self)
        self.worker = BuildWorker(
            file_paths=paths,
            output_path=out_path,
            new_sheet_for_landscape=self.app_settings.new_sheet_for_landscape
        )

        self.progress_dlg.cancel_requested.connect(self.worker.cancel)
        self.worker.progress.connect(self.progress_dlg.set_progress)
        self.worker.finished.connect(self._on_build_finished)
        self.worker.failed.connect(self._on_build_failed)

        self.worker.start()
        self.progress_dlg.exec()

    def _on_build_finished(self, result_meta: dict):
        if hasattr(self, "progress_dlg") and self.progress_dlg.isVisible():
            self.progress_dlg.accept()

        success_dlg = BuildSuccessDialog(result_meta, self)
        success_dlg.exec()

        if self.app_settings.auto_open_file:
            out_p = result_meta.get("output_path", "")
            if os.path.exists(out_p):
                try:
                    os.startfile(out_p)
                except Exception:
                    pass

    def _on_build_failed(self, err_msg: str):
        if hasattr(self, "progress_dlg") and self.progress_dlg.isVisible():
            self.progress_dlg.reject()

        QMessageBox.critical(
            self,
            "Ошибка при сборке отчета",
            f"Произошла ошибка при формировании документа:\n\n{err_msg}"
        )
