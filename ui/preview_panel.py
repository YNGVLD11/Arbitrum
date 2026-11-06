import os
from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QGraphicsDropShadowEffect
)
from PySide6.QtGui import QPixmap, QColor, QTransform
from core.preview import DocumentRenderer, PreviewWorker, is_cached_pdf_ready
from ui.themes import THEME_FEMININE


class DocumentPreviewPanel(QFrame):
    """
    Page-by-page preview of the currently selected document.
    Top: Document name only.
    Center: Scroll area rendering the document page with drop-shadow and border.
    Bottom Left: Orientation and Zoom only (no pt values).
    Bottom Right: Page counter and [◀] [▶] [−] [+] buttons.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("cardFrame")
        self.theme = "light"
        self.renderer = DocumentRenderer()
        self.current_file_path = None
        self.current_page = 0
        self.total_pages = 0
        self.zoom_factor = 1.0
        self.rotation = 0

        # Persistent background worker for preview conversions
        self.preview_worker = PreviewWorker(self)
        self.preview_worker.conversion_ready.connect(self._on_conversion_ready)
        self.preview_worker.error.connect(self._on_worker_error)
        self.preview_worker.start()

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # 1. Top Header bar: Title only
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)

        self.title_lbl = QLabel("Предпросмотр документа")
        self.title_lbl.setObjectName("headerTitle")
        self.title_lbl.setFixedHeight(24)
        header_layout.addWidget(self.title_lbl, stretch=1)
        layout.addLayout(header_layout)

        # 2. Scroll Area for Page Display
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setAlignment(Qt.AlignCenter)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: #F8FAFC;
                border: 1px solid #CBD5E1;
                border-radius: 8px;
            }
            QScrollArea > QWidget > QWidget {
                background-color: #F8FAFC;
            }
        """)

        # Container inside scroll area
        self.page_container = QWidget()
        self.page_container.setStyleSheet("background-color: transparent;")
        container_layout = QVBoxLayout(self.page_container)
        container_layout.setAlignment(Qt.AlignCenter)
        container_layout.setContentsMargins(16, 16, 16, 16)

        # Paper Sheet Display (Image / Placeholder label)
        self.image_lbl = QLabel("Перетащите файлы или выберите документ для предпросмотра")
        self.image_lbl.setAlignment(Qt.AlignCenter)
        self.image_lbl.setWordWrap(True)

        # Soft drop-shadow for document page
        self.shadow_effect = QGraphicsDropShadowEffect(self.image_lbl)
        self.shadow_effect.setBlurRadius(18)
        self.shadow_effect.setXOffset(0)
        self.shadow_effect.setYOffset(4)
        self.shadow_effect.setColor(QColor(0, 0, 0, 50))
        self.shadow_effect.setEnabled(False)
        self.image_lbl.setGraphicsEffect(self.shadow_effect)

        container_layout.addWidget(self.image_lbl)
        self._update_placeholder_font()

        self.scroll_area.setWidget(self.page_container)
        layout.addWidget(self.scroll_area, stretch=1)

        # 3. Bottom Footer Controls
        bottom_layout = QHBoxLayout()
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(8)

        # Left metadata: Orientation and Zoom only (NO pt values)
        self.meta_lbl = QLabel("Нет открытого документа")
        self.meta_lbl.setFixedHeight(34)
        self.meta_lbl.setStyleSheet("color: #64748B; font-size: 12px; font-weight: 500;")
        bottom_layout.addWidget(self.meta_lbl)
        bottom_layout.addStretch(1)

        # Right: Page count + Controls in bottom right
        self.page_lbl = QLabel("0 / 0")
        self.page_lbl.setFixedHeight(34)
        self.page_lbl.setStyleSheet("font-weight: 600; color: #475569; font-size: 12px; padding-right: 4px;")
        bottom_layout.addWidget(self.page_lbl)

        # Prev button
        self.prev_btn = QPushButton("◀")
        self.prev_btn.setObjectName("previewNavBtn")
        self.prev_btn.setFixedSize(36, 34)
        self.prev_btn.setToolTip("Предыдущая страница")
        self.prev_btn.clicked.connect(self._prev_page)
        bottom_layout.addWidget(self.prev_btn)

        # Next button
        self.next_btn = QPushButton("▶")
        self.next_btn.setObjectName("previewNavBtn")
        self.next_btn.setFixedSize(36, 34)
        self.next_btn.setToolTip("Следующая страница")
        self.next_btn.clicked.connect(self._next_page)
        bottom_layout.addWidget(self.next_btn)

        # Zoom out button
        self.zoom_out_btn = QPushButton("−")
        self.zoom_out_btn.setObjectName("previewNavBtn")
        self.zoom_out_btn.setFixedSize(36, 34)
        self.zoom_out_btn.setToolTip("Уменьшить масштаб")
        self.zoom_out_btn.clicked.connect(self._zoom_out)
        bottom_layout.addWidget(self.zoom_out_btn)

        # Zoom in button
        self.zoom_in_btn = QPushButton("+")
        self.zoom_in_btn.setObjectName("previewNavBtn")
        self.zoom_in_btn.setFixedSize(36, 34)
        self.zoom_in_btn.setToolTip("Увеличить масштаб")
        self.zoom_in_btn.clicked.connect(self._zoom_in)
        bottom_layout.addWidget(self.zoom_in_btn)

        layout.addLayout(bottom_layout)

        self._update_nav_buttons()

    def set_theme(self, theme: str):
        self.theme = theme
        if theme == THEME_FEMININE:
            self.scroll_area.setStyleSheet("""
                QScrollArea {
                    background-color: #FFF5F7;
                    border: 1px solid #FFCCD5;
                    border-radius: 8px;
                }
                QScrollArea > QWidget > QWidget {
                    background-color: #FFF5F7;
                }
            """)
            self.page_lbl.setStyleSheet("font-weight: 600; color: #831843; font-size: 12px; padding-right: 4px;")
            self.meta_lbl.setStyleSheet("color: #9D174D; font-size: 12px; font-weight: 500;")
        else:
            self.scroll_area.setStyleSheet("""
                QScrollArea {
                    background-color: #F8FAFC;
                    border: 1px solid #CBD5E1;
                    border-radius: 8px;
                }
                QScrollArea > QWidget > QWidget {
                    background-color: #F8FAFC;
                }
            """)
            self.page_lbl.setStyleSheet("font-weight: 600; color: #475569; font-size: 12px; padding-right: 4px;")
            self.meta_lbl.setStyleSheet("color: #64748B; font-size: 12px; font-weight: 500;")

        self._update_placeholder_font()
        if self.total_pages > 0:
            self._render_current_page()

    def set_document(self, file_path: str, rotation: int = 0):
        if not file_path or not os.path.exists(file_path):
            self.clear_preview()
            return

        self.rotation = rotation % 360

        if self.current_file_path == file_path and self.total_pages > 0:
            self._render_current_page()
            return

        self.current_file_path = file_path
        self.current_page = 0
        self.title_lbl.setText(os.path.basename(file_path))

        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".pdf":
            if self.renderer.load(file_path):
                self.total_pages = self.renderer.page_count
                self._render_current_page()
            else:
                self._show_error("Ошибка загрузки PDF-файла")
        else:
            # Word file: Check if cached PDF already exists for instant loading
            if is_cached_pdf_ready(file_path):
                if self.renderer.load(file_path):
                    self.total_pages = self.renderer.page_count
                    self._render_current_page()
                    return

            # If not yet cached, post request to persistent background worker
            self._show_loading("⏳ Подготовка предпросмотра Word...")
            self.preview_worker.request_conversion(file_path)

    def _show_loading(self, text: str):
        self.total_pages = 0
        self.image_lbl.setWordWrap(True)
        self.image_lbl.setMinimumSize(0, 0)
        self.image_lbl.setMaximumSize(16777215, 16777215)
        self.image_lbl.setPixmap(QPixmap())
        self.image_lbl.setText(text)
        self.shadow_effect.setEnabled(False)
        self.meta_lbl.setText("Конвертация документа...")
        self.page_lbl.setText("0 / 0")
        self._update_placeholder_font()
        self._update_nav_buttons()

    def _show_error(self, text: str):
        self.total_pages = 0
        self.image_lbl.setWordWrap(True)
        self.image_lbl.setMinimumSize(0, 0)
        self.image_lbl.setMaximumSize(16777215, 16777215)
        self.image_lbl.setPixmap(QPixmap())
        self.image_lbl.setText(text)
        self.shadow_effect.setEnabled(False)
        self.meta_lbl.setText("Ошибка")
        self.page_lbl.setText("0 / 0")
        self._update_placeholder_font()
        self._update_nav_buttons()

    def _on_conversion_ready(self, file_path: str, page_count: int):
        if self.current_file_path == file_path:
            self.total_pages = page_count
            if self.renderer.load(file_path):
                self._render_current_page()
            else:
                self._show_error("Не удалось отобразить документ")

    def _on_worker_error(self, file_path: str, err: str):
        if self.current_file_path == file_path:
            self._show_error(f"Предпросмотр недоступен: {err}")

    def set_rotation(self, rotation: int):
        self.rotation = rotation % 360
        if self.total_pages > 0:
            self._render_current_page()

    def _render_current_page(self):
        if self.total_pages <= 0:
            return

        page_sz = self.renderer.get_page_size(self.current_page)
        orig_pw = max(1, page_sz.width())
        orig_ph = max(1, page_sz.height())

        rot = getattr(self, "rotation", 0) % 360
        if rot in (90, 270):
            pw, ph = orig_ph, orig_pw
        else:
            pw, ph = orig_pw, orig_ph

        is_land = pw > ph
        orient_str = "Альбомная" if is_land else "Книжная"
        rot_suffix = f" (поворот {rot}°)" if rot != 0 else ""

        # Fit inside viewport with margins
        vp_w = max(180, self.scroll_area.viewport().width() - 36, self.scroll_area.width() - 40)
        vp_h = max(240, self.scroll_area.viewport().height() - 36, self.scroll_area.height() - 40)

        scale_w = vp_w / pw
        scale_h = vp_h / ph
        base_scale = min(scale_w, scale_h)
        target_scale = base_scale * self.zoom_factor

        target_w = max(80, int(pw * target_scale))
        target_h = max(80, int(ph * target_scale))

        if rot in (90, 270):
            render_size = QSize(target_h, target_w)
        else:
            render_size = QSize(target_w, target_h)

        pixmap = self.renderer.render_page(self.current_page, render_size)
        if not pixmap.isNull():
            if rot != 0:
                transform = QTransform().rotate(rot)
                pixmap = pixmap.transformed(transform, Qt.SmoothTransformation)

            self.image_lbl.setWordWrap(False)
            self.image_lbl.setText("")
            self.image_lbl.setPixmap(pixmap)
            self.image_lbl.setFixedSize(target_w, target_h)
            self.image_lbl.setScaledContents(True)
            self.image_lbl.setStyleSheet("""
                QLabel {
                    background-color: #FFFFFF;
                    border: 1px solid #94A3B8;
                    border-radius: 3px;
                }
            """)
            self.shadow_effect.setEnabled(True)
        else:
            self._show_error("Ошибка рендеринга страницы")

        self.page_lbl.setText(f"{self.current_page + 1} / {self.total_pages}")
        self.meta_lbl.setText(f"{orient_str}{rot_suffix} • {int(self.zoom_factor * 100)}%")
        self._update_nav_buttons()

    def _update_nav_buttons(self):
        self.prev_btn.setEnabled(self.current_page > 0)
        self.next_btn.setEnabled(self.current_page < self.total_pages - 1)
        self.zoom_in_btn.setEnabled(self.total_pages > 0 and self.zoom_factor < 2.5)
        self.zoom_out_btn.setEnabled(self.total_pages > 0 and self.zoom_factor > 0.4)

    def _prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self._render_current_page()

    def _next_page(self):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self._render_current_page()

    def _zoom_in(self):
        if self.zoom_factor < 2.5:
            self.zoom_factor += 0.15
            self._render_current_page()

    def _zoom_out(self):
        if self.zoom_factor > 0.4:
            self.zoom_factor -= 0.15
            self._render_current_page()

    def _update_placeholder_font(self):
        if self.current_file_path is None or self.total_pages == 0:
            w = max(200, self.width())
            font_size = max(11, min(17, int(w / 28)))
            padding = max(16, min(50, int(w / 14)))
            if self.theme == THEME_FEMININE:
                txt_color = "#FB7185"
                border_color = "#FFCCD5"
            else:
                txt_color = "#94A3B8"
                border_color = "#CBD5E1"

            self.image_lbl.setStyleSheet(f"""
                QLabel {{
                    color: {txt_color};
                    font-size: {font_size}px;
                    font-weight: 500;
                    line-height: 1.5;
                    padding: {padding}px 20px;
                    background-color: #FFFFFF;
                    border: 1px dashed {border_color};
                    border-radius: 10px;
                }}
            """)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_placeholder_font()
        if self.total_pages > 0:
            self._render_current_page()

    def mousePressEvent(self, event):
        main_win = self.window()
        if hasattr(main_win, "file_list_panel"):
            main_win.file_list_panel.clear_selection()
        super().mousePressEvent(event)

    def closeEvent(self, event):
        if hasattr(self, "preview_worker"):
            self.preview_worker.stop()
        super().closeEvent(event)

    def clear_preview(self):
        self.current_file_path = None
        self.total_pages = 0
        self.current_page = 0
        self.title_lbl.setText("Предпросмотр документа")
        self.page_lbl.setText("0 / 0")
        self.meta_lbl.setText("Нет открытого документа")

        # Reset image_lbl to flexible placeholder
        self.image_lbl.setWordWrap(True)
        self.image_lbl.setMinimumSize(0, 0)
        self.image_lbl.setMaximumSize(16777215, 16777215)
        self.image_lbl.setPixmap(QPixmap())
        self.image_lbl.setText("Перетащите файлы или выберите документ для предпросмотра")
        self.shadow_effect.setEnabled(False)
        self._update_placeholder_font()
        self._update_nav_buttons()
