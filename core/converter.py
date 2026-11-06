import os
import tempfile
import shutil
import threading
import pypdf

# Dimensions for A4 in points (297 mm x 210 mm)
A4_LANDSCAPE_W = 841.89
A4_LANDSCAPE_H = 595.28
A4_HALF_W = A4_LANDSCAPE_W / 2.0

# Global lock to serialize Microsoft Word COM automation across all threads
WORD_LOCK = threading.RLock()


def convert_word_to_pdf(doc_path: str, output_pdf_path: str):
    """
    Converts .doc or .docx to PDF using Microsoft Word COM automation.
    Thread-safe with global lock and pythoncom initialization.
    Guarantees clean process termination even on errors.
    """
    import pythoncom
    import win32com.client

    with WORD_LOCK:
        pythoncom.CoInitialize()
        word = None
        doc = None
        try:
            word = win32com.client.DispatchEx("Word.Application")
            word.Visible = False
            word.DisplayAlerts = 0  # wdAlertsNone
            try:
                word.ScreenUpdating = False
            except Exception:
                pass

            abs_doc_path = os.path.abspath(doc_path)
            abs_pdf_path = os.path.abspath(output_pdf_path)

            doc = word.Documents.Open(
                abs_doc_path,
                ReadOnly=True,
                ConfirmConversions=False,
                Visible=False,
                AddToRecentFiles=False
            )
            # 17 = wdFormatPDF
            doc.SaveAs2(abs_pdf_path, FileFormat=17)
        finally:
            if doc is not None:
                try:
                    doc.Close(SaveChanges=0)  # wdDoNotSaveChanges
                except Exception:
                    pass
                del doc
            if word is not None:
                try:
                    word.Quit(SaveChanges=0)
                except Exception:
                    pass
                del word
            try:
                pythoncom.CoUninitialize()
            except Exception:
                pass


def add_sheet_2up(writer: pypdf.PdfWriter, left_page=None, right_page=None):
    """
    Adds a single A4 Landscape sheet with up to 2 pages (left and right).
    Calculates exact scale and centering for both portrait and landscape pages.
    """
    sheet = writer.add_blank_page(width=A4_LANDSCAPE_W, height=A4_LANDSCAPE_H)

    if left_page is not None:
        pw = float(left_page.mediabox.width)
        ph = float(left_page.mediabox.height)
        scale = min(A4_HALF_W / pw, A4_LANDSCAPE_H / ph)
        tx = (A4_HALF_W - pw * scale) / 2.0
        ty = (A4_LANDSCAPE_H - ph * scale) / 2.0
        t = pypdf.Transformation().scale(scale, scale).translate(tx, ty)
        sheet.merge_transformed_page(left_page, t)

    if right_page is not None:
        pw = float(right_page.mediabox.width)
        ph = float(right_page.mediabox.height)
        scale = min(A4_HALF_W / pw, A4_LANDSCAPE_H / ph)
        tx = A4_HALF_W + (A4_HALF_W - pw * scale) / 2.0
        ty = (A4_LANDSCAPE_H - ph * scale) / 2.0
        t = pypdf.Transformation().scale(scale, scale).translate(tx, ty)
        sheet.merge_transformed_page(right_page, t)

    return sheet


def build_arbitr_report(
    file_paths: list[str],
    output_path: str,
    progress_callback=None,
    is_cancelled=None,
    new_sheet_for_landscape=True
) -> dict:
    """
    Combines the input files in the given order into an A4 2-up PDF report.
    - file_paths: list of paths to .doc, .docx, or .pdf files.
    - output_path: destination .pdf path.
    - progress_callback: func(percent: int, message: str).
    - is_cancelled: callable returning bool to abort operation.
    """
    def report(percent: int, msg: str):
        if progress_callback:
            progress_callback(percent, msg)

    def check_cancel():
        if is_cancelled and is_cancelled():
            raise InterruptedError("Операция отменена пользователем.")

    total_files = len(file_paths)
    if total_files == 0:
        raise ValueError("Список файлов пуст.")

    temp_dir = tempfile.mkdtemp(prefix="arbitr_build_")
    try:
        report(5, "Подготовка к конвертации документов...")
        check_cancel()

        # Step 1: Convert Word documents to intermediate PDF
        intermediate_pdfs = []
        for i, path in enumerate(file_paths):
            check_cancel()
            ext = os.path.splitext(path)[1].lower()
            fname = os.path.basename(path)

            pct = 10 + int((i / total_files) * 45)
            if ext in [".doc", ".docx"]:
                report(pct, f"Конвертация Word в PDF: {fname}...")
                out_pdf = os.path.join(temp_dir, f"converted_{i}.pdf")
                convert_word_to_pdf(path, out_pdf)
                intermediate_pdfs.append(out_pdf)
            elif ext == ".pdf":
                report(pct, f"Чтение PDF: {fname}...")
                intermediate_pdfs.append(path)
            else:
                raise ValueError(f"Неподдерживаемый формат файла: {path}")

        check_cancel()
        report(60, "Анализ страниц и компоновка формата A4...")

        # Step 2: Read all pages from intermediate PDFs
        collected_pages = []
        for pdf_path in intermediate_pdfs:
            check_cancel()
            reader = pypdf.PdfReader(pdf_path)
            for page in reader.pages:
                collected_pages.append(page)

        total_input_pages = len(collected_pages)
        if total_input_pages == 0:
            raise ValueError("Исходные документы не содержат страниц.")

        # Step 3: Layout pages 2-up into A4 Landscape writer
        writer = pypdf.PdfWriter()
        sheet_count = 0
        idx = 0

        while idx < total_input_pages:
            check_cancel()
            pct = 65 + int((idx / total_input_pages) * 25)
            report(pct, f"Размещение страниц на листах ({idx + 1} из {total_input_pages})...")

            page1 = collected_pages[idx]
            pw1 = float(page1.mediabox.width)
            ph1 = float(page1.mediabox.height)
            is_land1 = pw1 > ph1

            if is_land1:
                # Landscape page: Center alone on a full A4 landscape sheet
                add_sheet_2up(writer, left_page=page1, right_page=None)
                sheet_count += 1
                idx += 1
            else:
                # Portrait page: Pair with next page if next page is also portrait
                page2 = None
                if idx + 1 < total_input_pages:
                    next_p = collected_pages[idx + 1]
                    pw2 = float(next_p.mediabox.width)
                    ph2 = float(next_p.mediabox.height)
                    is_land2 = pw2 > ph2

                    if not is_land2 or not new_sheet_for_landscape:
                        page2 = next_p
                        idx += 1

                add_sheet_2up(writer, left_page=page1, right_page=page2)
                sheet_count += 1
                idx += 1

        check_cancel()
        report(95, "Сохранение итогового PDF-файла...")

        # Step 4: Write to output destination
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "wb") as f_out:
            writer.write(f_out)

        report(100, "Сборка отчёта успешно завершена!")

        return {
            "success": True,
            "output_path": output_path,
            "total_input_files": total_files,
            "total_input_pages": total_input_pages,
            "total_sheets": sheet_count,
            "output_size_bytes": os.path.getsize(output_path)
        }

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
