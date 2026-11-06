import os
import tempfile
import hashlib
from PySide6.QtCore import QSize, Signal, QThread
from PySide6.QtGui import QPixmap
from PySide6.QtPdf import QPdfDocument
from core.converter import convert_word_to_pdf

# Cache folder for converted preview PDFs
CACHE_DIR = os.path.join(tempfile.gettempdir(), "arbitr_preview_cache")
os.makedirs(CACHE_DIR, exist_ok=True)


def get_file_cache_key(file_path: str) -> str:
    mtime = os.path.getmtime(file_path) if os.path.exists(file_path) else 0
    size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
    raw = f"{os.path.abspath(file_path)}_{mtime}_{size}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def get_cached_pdf_path(file_path: str) -> str:
    cache_key = get_file_cache_key(file_path)
    return os.path.join(CACHE_DIR, f"{cache_key}.pdf")


def is_cached_pdf_ready(file_path: str) -> bool:
    pdf_path = get_cached_pdf_path(file_path)
    return os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 0


class DocumentRenderer:
    """
    Renders PDF pages into QPixmap using PySide6 QtPdf.
    Supports on-demand Word-to-PDF conversion for preview.
    """
    def __init__(self):
        self._doc = QPdfDocument()
        self._current_pdf_path = None

    def load(self, file_path: str) -> bool:
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".pdf":
            pdf_path = file_path
        elif ext in [".doc", ".docx"]:
            cached_pdf = get_cached_pdf_path(file_path)
            if not os.path.exists(cached_pdf) or os.path.getsize(cached_pdf) == 0:
                convert_word_to_pdf(file_path, cached_pdf)
            pdf_path = cached_pdf
        else:
            return False

        if self._current_pdf_path != pdf_path or self._doc.pageCount() == 0:
            self._doc.load(pdf_path)
            self._current_pdf_path = pdf_path

        return self._doc.pageCount() > 0

    @property
    def page_count(self) -> int:
        return self._doc.pageCount()

    def get_page_size(self, page_index: int = 0) -> QSize:
        if 0 <= page_index < self._doc.pageCount():
            sz = self._doc.pagePointSize(page_index)
            return QSize(int(sz.width()), int(sz.height()))
        return QSize(0, 0)

    def render_page(self, page_index: int, target_size: QSize) -> QPixmap:
        if 0 <= page_index < self._doc.pageCount():
            qimg = self._doc.render(page_index, target_size)
            if not qimg.isNull():
                return QPixmap.fromImage(qimg)
        return QPixmap()


class ThumbnailWorker(QThread):
    """
    Background worker to convert Word documents to cached PDF without freezing the UI.
    Emits (file_path, page_count) when ready.
    """
    conversion_ready = Signal(str, int)  # file_path, page_count
    error = Signal(str, str)

    def __init__(self, file_path: str):
        super().__init__()
        self.file_path = file_path

    def run(self):
        try:
            renderer = DocumentRenderer()
            if renderer.load(self.file_path):
                self.conversion_ready.emit(self.file_path, renderer.page_count)
            else:
                self.error.emit(self.file_path, "Не удалось преобразовать документ")
        except Exception as e:
            self.error.emit(self.file_path, str(e))
