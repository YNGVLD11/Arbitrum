import os
from PySide6.QtCore import Qt, Signal, QSize, QMimeData, QPoint
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QFileDialog, QFrame, QApplication
)
from PySide6.QtGui import QDrag, QPixmap
from ui.themes import THEME_FEMININE


def format_file_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} Б"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} КБ"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} МБ"


class FileItemWidget(QFrame):
    """
    Card representation of a document in the list.
    Supports clicking anywhere to select, or dragging to reorder with a live visual preview.
    All labels are non-interactive; only the ✕ button responds to clicks.
    """
    delete_clicked = Signal(str)

    def __init__(self, file_path: str, index: int, theme: str = "light", list_widget=None, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.index = index
        self.theme = theme
        self.list_widget = list_widget
        self.is_selected = False
        self.setFixedHeight(56)

        self._update_card_style()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignVCenter)

        # 1. Order Badge (Circle) - Non-interactive
        self.badge_lbl = QLabel(str(index))
        self.badge_lbl.setAlignment(Qt.AlignCenter)
        self.badge_lbl.setFixedSize(26, 26)
        self.badge_lbl.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self._update_badge_style()
        layout.addWidget(self.badge_lbl)

        # 2. File Format Badge - Non-interactive
        ext = os.path.splitext(file_path)[1].lower()
        self.icon_lbl = QLabel()
        self.icon_lbl.setAlignment(Qt.AlignCenter)
        self.icon_lbl.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        if ext == ".pdf":
            self.icon_lbl.setText("PDF")
            self.icon_lbl.setStyleSheet("""
                QLabel {
                    background-color: #FEE2E2;
                    color: #DC2626;
                    font-weight: bold;
                    font-size: 10px;
                    border-radius: 5px;
                    padding: 3px 6px;
                }
            """)
        elif ext in [".doc", ".docx"]:
            self.icon_lbl.setText("DOCX" if ext == ".docx" else "DOC")
            self.icon_lbl.setStyleSheet("""
                QLabel {
                    background-color: #DBEAFE;
                    color: #2563EB;
                    font-weight: bold;
                    font-size: 10px;
                    border-radius: 5px;
                    padding: 3px 6px;
                }
            """)
        else:
            self.icon_lbl.setText("ФАЙЛ")
            self.icon_lbl.setStyleSheet("""
                QLabel {
                    background-color: #F1F5F9;
                    color: #64748B;
                    font-weight: bold;
                    font-size: 10px;
                    border-radius: 5px;
                    padding: 3px 6px;
                }
            """)
        layout.addWidget(self.icon_lbl)

        # 3. File Info (Name + Path/Size) - Non-interactive
        info_layout = QVBoxLayout()
        info_layout.setSpacing(1)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setAlignment(Qt.AlignVCenter)

        fname = os.path.basename(file_path)
        self.name_lbl = QLabel(fname)
        self.name_lbl.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self._update_text_style()
        info_layout.addWidget(self.name_lbl)

        size_str = format_file_size(os.path.getsize(file_path)) if os.path.exists(file_path) else "0 Б"
        self.sub_lbl = QLabel(f"{size_str}  •  {file_path}")
        self.sub_lbl.setStyleSheet("color: #64748B; font-size: 11px;")
        self.sub_lbl.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        info_layout.addWidget(self.sub_lbl)

        layout.addLayout(info_layout, stretch=1)

        # 4. Remove button (✕)
        self.del_btn = QPushButton("✕")
        self.del_btn.setFixedSize(26, 26)
        self.del_btn.setToolTip("Удалить файл из списка")
        self.del_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #94A3B8;
                font-weight: bold;
                font-size: 13px;
                border-radius: 13px;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: #FEE2E2;
                color: #EF4444;
            }
        """)
        self.del_btn.clicked.connect(lambda: self.delete_clicked.emit(self.file_path))
        layout.addWidget(self.del_btn)

    def _update_card_style(self):
        if self.theme == THEME_FEMININE:
            if self.is_selected:
                self.setStyleSheet("""
                    FileItemWidget {
                        background-color: #FFF0F3;
                        border: 2px solid #FF4D6D;
                        border-radius: 10px;
                    }
                """)
            else:
                self.setStyleSheet("""
                    FileItemWidget {
                        background-color: rgba(255, 255, 255, 0.95);
                        border: 1px solid #FFCCD5;
                        border-radius: 10px;
                    }
                    FileItemWidget:hover {
                        border: 1px solid #FF758F;
                        background-color: #FFF5F7;
                    }
                """)
        else:
            if self.is_selected:
                self.setStyleSheet("""
                    FileItemWidget {
                        background-color: #EFF6FF;
                        border: 2px solid #2563EB;
                        border-radius: 10px;
                    }
                """)
            else:
                self.setStyleSheet("""
                    FileItemWidget {
                        background-color: #FFFFFF;
                        border: 1px solid #BAE6FD;
                        border-radius: 10px;
                    }
                    FileItemWidget:hover {
                        border: 1px solid #38BDF8;
                        background-color: #F8FAFC;
                    }
                """)

    def set_selected(self, val: bool):
        if self.is_selected != val:
            self.is_selected = val
            self._update_card_style()

    def _update_badge_style(self):
        if self.theme == THEME_FEMININE:
            self.badge_lbl.setStyleSheet("""
                QLabel {
                    background-color: #FF758F;
                    color: white;
                    font-weight: bold;
                    border-radius: 13px;
                    font-size: 11px;
                }
            """)
        else:
            self.badge_lbl.setStyleSheet("""
                QLabel {
                    background-color: #3B82F6;
                    color: white;
                    font-weight: bold;
                    border-radius: 13px;
                    font-size: 11px;
                }
            """)

    def _update_text_style(self):
        text_color = "#38272F" if self.theme == THEME_FEMININE else "#0F172A"
        self.name_lbl.setStyleSheet(f"font-weight: 600; font-size: 13px; color: {text_color};")

    def update_theme(self, theme: str):
        self.theme = theme
        self._update_card_style()
        self._update_badge_style()
        self._update_text_style()

    def update_index(self, index: int):
        self.index = index
        self.badge_lbl.setText(str(index))

    # Mouse & Drag Reordering
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_start_pos = event.pos()
            # Select row in list widget
            if self.list_widget:
                for r in range(self.list_widget.count()):
                    it = self.list_widget.item(r)
                    if self.list_widget.itemWidget(it) is self:
                        self.list_widget.setCurrentRow(r)
                        break
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton):
            return
        if not hasattr(self, "_drag_start_pos"):
            return
        if (event.pos() - self._drag_start_pos).manhattanLength() < QApplication.startDragDistance():
            return

        # Start dragging with visible floating card preview
        drag = QDrag(self)
        mime_data = QMimeData()
        mime_data.setData("application/x-arbitr-file-item", str(self.index - 1).encode("utf-8"))
        mime_data.setText(self.file_path)
        drag.setMimeData(mime_data)

        pixmap = self.grab()
        drag.setPixmap(pixmap)
        drag.setHotSpot(event.pos())
        drag.exec(Qt.MoveAction)


class FileDropListWidget(QListWidget):
    """
    List widget with drag-and-drop file import from Windows Explorer
    and card reordering with visual previews.
    """
    files_dropped = Signal(list)
    item_reordered = Signal(int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragEnabled(False)  # We handle QDrag in FileItemWidget
        self.setDropIndicatorShown(True)

        # Centered placeholder label when list is empty
        self.placeholder_lbl = QLabel(
            "📁 Перетащите файлы сюда\nили нажмите кнопку «Добавить»",
            self
        )
        self.placeholder_lbl.setAlignment(Qt.AlignCenter)
        self.placeholder_lbl.setStyleSheet("""
            QLabel {
                color: #94A3B8;
                font-size: 13px;
                font-weight: 500;
                line-height: 1.6;
                background: transparent;
                border: none;
            }
        """)
        self.placeholder_lbl.setAttribute(Qt.WA_TransparentForMouseEvents, True)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.placeholder_lbl.setGeometry(self.rect())

    def mousePressEvent(self, event):
        pos = event.position().toPoint()
        item = self.itemAt(pos)
        if not item:
            self.setCurrentRow(-1)
            self.clearSelection()
        super().mousePressEvent(event)

    def update_placeholder(self):
        self.placeholder_lbl.setVisible(self.count() == 0)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() or event.mimeData().hasFormat("application/x-arbitr-file-item"):
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls() or event.mimeData().hasFormat("application/x-arbitr-file-item"):
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):
        # 1. External files dropped from Windows Explorer
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            paths = []
            for u in urls:
                p = u.toLocalFile()
                if os.path.isfile(p):
                    if os.path.basename(p).startswith("~$"):
                        continue
                    ext = os.path.splitext(p)[1].lower()
                    if ext in [".doc", ".docx", ".pdf"]:
                        paths.append(p)
                elif os.path.isdir(p):
                    for root, _, files in os.walk(p):
                        for f in files:
                            if f.startswith("~$"):
                                continue
                            ext = os.path.splitext(f)[1].lower()
                            if ext in [".doc", ".docx", ".pdf"]:
                                paths.append(os.path.join(root, f))
            if paths:
                self.files_dropped.emit(paths)
                event.acceptProposedAction()
                return

        # 2. Internal card reordering
        if event.mimeData().hasFormat("application/x-arbitr-file-item"):
            src_row = int(bytes(event.mimeData().data("application/x-arbitr-file-item")).decode("utf-8"))
            drop_pos = event.position().toPoint()
            target_item = self.itemAt(drop_pos)
            if target_item:
                target_row = self.row(target_item)
            else:
                target_row = self.count() - 1

            if target_row < 0:
                target_row = 0

            self.item_reordered.emit(src_row, target_row)
            event.acceptProposedAction()
            return

        super().dropEvent(event)


class FileListPanel(QFrame):
    """
    Complete file management component: list + buttons.
    Maintains clean data state and ensures widgets never collapse or disappear.
    """
    file_selected = Signal(str)
    file_list_changed = Signal()

    def __init__(self, theme: str = "light", parent=None):
        super().__init__(parent)
        self.theme = theme
        self.file_paths = []
        self.setObjectName("cardFrame")
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # Header bar
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel("Список документов")
        title.setObjectName("headerTitle")
        title.setFixedHeight(24)
        header_layout.addWidget(title)

        header_layout.addStretch()

        self.count_lbl = QLabel("0 файлов")
        self.count_lbl.setObjectName("subTitle")
        self.count_lbl.setFixedHeight(24)
        header_layout.addWidget(self.count_lbl)

        layout.addLayout(header_layout)

        # Drag-and-drop list (placeholder is built into list widget)
        self.list_widget = FileDropListWidget(self)
        self.list_widget.files_dropped.connect(self.add_files)
        self.list_widget.item_reordered.connect(self._on_item_reordered)
        self.list_widget.currentRowChanged.connect(self._on_selection_changed)
        layout.addWidget(self.list_widget, stretch=1)

        # Action Buttons Toolbar
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        btn_layout.setContentsMargins(0, 0, 0, 0)

        # "Добавить"
        self.add_btn = QPushButton("➕ Добавить")
        self.add_btn.setFixedHeight(34)
        self.add_btn.clicked.connect(self._open_file_dialog)
        btn_layout.addWidget(self.add_btn)

        # Compact Up / Down buttons
        self.up_btn = QPushButton("▲")
        self.up_btn.setObjectName("toolIconBtn")
        self.up_btn.setFixedSize(36, 34)
        self.up_btn.setToolTip("Переместить выбранный файл выше")
        self.up_btn.clicked.connect(self.move_current_up)
        btn_layout.addWidget(self.up_btn)

        self.down_btn = QPushButton("▼")
        self.down_btn.setObjectName("toolIconBtn")
        self.down_btn.setFixedSize(36, 34)
        self.down_btn.setToolTip("Переместить выбранный файл ниже")
        self.down_btn.clicked.connect(self.move_current_down)
        btn_layout.addWidget(self.down_btn)

        btn_layout.addStretch()

        # Clear All
        self.clear_btn = QPushButton("Очистить")
        self.clear_btn.setObjectName("dangerButton")
        self.clear_btn.setFixedHeight(34)
        self.clear_btn.clicked.connect(self.clear_files)
        btn_layout.addWidget(self.clear_btn)

        layout.addLayout(btn_layout)
        self.list_widget.update_placeholder()

    def set_theme(self, theme: str):
        self.theme = theme
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            w = self.list_widget.itemWidget(item)
            if isinstance(w, FileItemWidget):
                w.update_theme(theme)
        self._refresh_card_highlights()

    def _refresh_card_highlights(self):
        cur_row = self.list_widget.currentRow()
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            w = self.list_widget.itemWidget(item)
            if isinstance(w, FileItemWidget):
                w.set_selected(i == cur_row)

    def clear_selection(self):
        self.list_widget.setCurrentRow(-1)
        self.list_widget.clearSelection()
        self._refresh_card_highlights()

    def _sync_items(self, selected_path: str = None):
        """
        Reconstructs item widgets from self.file_paths.
        Guarantees that widgets are never lost and indices are always 1, 2, 3...
        """
        self.list_widget.blockSignals(True)
        self.list_widget.clear()
        for idx, path in enumerate(self.file_paths, start=1):
            item = QListWidgetItem()
            item.setSizeHint(QSize(200, 62))
            self.list_widget.addItem(item)

            widget = FileItemWidget(path, idx, theme=self.theme, list_widget=self.list_widget)
            widget.delete_clicked.connect(self.remove_by_path)
            self.list_widget.setItemWidget(item, widget)

        count = len(self.file_paths)
        if count == 1:
            cnt_str = "1 файл"
        elif 2 <= count <= 4:
            cnt_str = f"{count} файла"
        else:
            cnt_str = f"{count} файлов"
        self.count_lbl.setText(cnt_str)
        self.list_widget.update_placeholder()

        # Restore selection
        target_row = -1
        if selected_path:
            norm_sel = os.path.normpath(selected_path)
            if norm_sel in self.file_paths:
                target_row = self.file_paths.index(norm_sel)

        if target_row == -1 and self.file_paths:
            target_row = 0

        self.list_widget.setCurrentRow(target_row)
        self.list_widget.blockSignals(False)
        self._refresh_card_highlights()

        if target_row >= 0 and target_row < len(self.file_paths):
            self.file_selected.emit(self.file_paths[target_row])

    def add_files(self, paths: list[str]):
        added = False
        newly_added = []
        for p in paths:
            if os.path.basename(p).startswith("~$"):
                continue
            norm_p = os.path.normpath(p)
            if norm_p not in self.file_paths:
                self.file_paths.append(norm_p)
                newly_added.append(norm_p)
                added = True

        if added:
            sel = newly_added[0] if newly_added else None
            self._sync_items(selected_path=sel)
            self.file_list_changed.emit()

    def _open_file_dialog(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Выберите файлы для отчёта",
            "",
            "Документы (*.docx *.doc *.pdf);;Word документы (*.docx *.doc);;PDF файлы (*.pdf)"
        )
        if files:
            self.add_files(files)

    def _on_item_reordered(self, src_row: int, target_row: int):
        if 0 <= src_row < len(self.file_paths):
            if target_row < 0:
                target_row = 0
            if target_row >= len(self.file_paths):
                target_row = len(self.file_paths) - 1
            if src_row == target_row:
                return

            moved_path = self.file_paths.pop(src_row)
            self.file_paths.insert(target_row, moved_path)
            self._sync_items(selected_path=moved_path)
            self.file_list_changed.emit()

    def _on_selection_changed(self, row: int):
        self._refresh_card_highlights()
        if 0 <= row < len(self.file_paths):
            self.file_selected.emit(self.file_paths[row])

    def get_file_paths(self) -> list[str]:
        return list(self.file_paths)

    def move_current_up(self):
        row = self.list_widget.currentRow()
        if row > 0 and row < len(self.file_paths):
            moved_path = self.file_paths.pop(row)
            self.file_paths.insert(row - 1, moved_path)
            self._sync_items(selected_path=moved_path)
            self.file_list_changed.emit()

    def move_current_down(self):
        row = self.list_widget.currentRow()
        if 0 <= row < len(self.file_paths) - 1:
            moved_path = self.file_paths.pop(row)
            self.file_paths.insert(row + 1, moved_path)
            self._sync_items(selected_path=moved_path)
            self.file_list_changed.emit()

    def remove_by_path(self, path: str):
        if path in self.file_paths:
            cur_row = self.list_widget.currentRow()
            self.file_paths.remove(path)
            new_sel = None
            if self.file_paths:
                new_idx = min(cur_row, len(self.file_paths) - 1)
                new_sel = self.file_paths[new_idx]
            self._sync_items(selected_path=new_sel)
            self.file_list_changed.emit()

    def clear_files(self):
        self.file_paths.clear()
        self._sync_items()
        self.file_list_changed.emit()
