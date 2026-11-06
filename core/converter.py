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


def _transform_and_merge_page(sheet, page, is_right: bool = False):
    """
    Helper to scale and translate (and rotate if needed) a page onto a 2-up landscape sheet.
    """
    rot = getattr(page, 'rotation', 0) % 360
    orig_w = float(page.mediabox.width)
    orig_h = float(page.mediabox.height)
    if rot in (90, 270):
        pw, ph = orig_h, orig_w
    else:
        pw, ph = orig_w, orig_h

    scale = min(A4_HALF_W / pw, A4_LANDSCAPE_H / ph)
    offset_x = A4_HALF_W if is_right else 0.0
    tx = offset_x + (A4_HALF_W - pw * scale) / 2.0
    ty = (A4_LANDSCAPE_H - ph * scale) / 2.0

    t = pypdf.Transformation()
    if rot == 90:
        t = t.rotate(90).scale(scale, scale).translate(tx + pw * scale, ty)
    elif rot == 180:
        t = t.rotate(180).scale(scale, scale).translate(tx + pw * scale, ty + ph * scale)
    elif rot == 270:
        t = t.rotate(270).scale(scale, scale).translate(tx, ty + ph * scale)
    else:
        t = t.scale(scale, scale).translate(tx, ty)

    # Use a blank unrotated container to cleanly project the page
    page_copy = pypdf.PageObject.create_blank_page(width=orig_w, height=orig_h)
    page_copy.merge_page(page)
    sheet.merge_transformed_page(page_copy, t)


def add_sheet_2up(writer: pypdf.PdfWriter, left_page=None, right_page=None):
    """
    Adds a single A4 Landscape sheet with up to 2 pages (left and right).
    Calculates exact scale, centering, and rotation for both portrait and landscape pages.
    """
    sheet = writer.add_blank_page(width=A4_LANDSCAPE_W, height=A4_LANDSCAPE_H)

    if left_page is not None:
        _transform_and_merge_page(sheet, left_page, is_right=False)

    if right_page is not None:
        _transform_and_merge_page(sheet, right_page, is_right=True)

    return sheet


def build_docx_report(
    file_paths: list[str],
    output_path: str,
    progress_callback=None,
    is_cancelled=None,
    rotations: dict[str, int] = None
) -> dict:
    """
    Merges input documents (DOCX, DOC, PDF) into a single master .docx file using Word COM.
    """
    import pythoncom
    import win32com.client

    def report(percent: int, msg: str):
        if progress_callback:
            progress_callback(percent, msg)

    def check_cancel():
        if is_cancelled and is_cancelled():
            raise InterruptedError("Операция отменена пользователем.")

    total_files = len(file_paths)
    if total_files == 0:
        raise ValueError("Список файлов пуст.")

    rotations = rotations or {}
    temp_dir = tempfile.mkdtemp(prefix="arbitr_docx_merge_")

    with WORD_LOCK:
        pythoncom.CoInitialize()
        word = None
        master_doc = None
        try:
            report(5, "Инициализация Microsoft Word...")
            check_cancel()

            word = win32com.client.DispatchEx("Word.Application")
            word.Visible = False
            word.DisplayAlerts = 0
            try:
                word.ScreenUpdating = False
            except Exception:
                pass

            # Step 1: Pre-process PDF files to intermediate DOCX
            ready_docx_paths = []
            for i, path in enumerate(file_paths):
                check_cancel()
                pct = 10 + int((i / total_files) * 40)
                fname = os.path.basename(path)
                ext = os.path.splitext(path)[1].lower()

                if ext in [".doc", ".docx"]:
                    ready_docx_paths.append(os.path.abspath(path))
                elif ext == ".pdf":
                    report(pct, f"Преобразование PDF в Word: {fname}...")
                    tmp_docx = os.path.join(temp_dir, f"conv_pdf_{i}.docx")
                    pdf_doc = word.Documents.Open(
                        os.path.abspath(path),
                        ConfirmConversions=False,
                        ReadOnly=True,
                        Visible=False
                    )
                    pdf_doc.SaveAs2(tmp_docx, FileFormat=16)  # wdFormatXMLDocument
                    pdf_doc.Close(SaveChanges=0)
                    ready_docx_paths.append(tmp_docx)
                else:
                    raise ValueError(f"Неподдерживаемый формат файла: {path}")

            check_cancel()
            report(55, "Объединение документов Word...")

            # Step 2: Create master document and append all files
            master_doc = word.Documents.Add()
            sel = word.Selection

            for i, docx_path in enumerate(ready_docx_paths):
                check_cancel()
                pct = 60 + int((i / total_files) * 30)
                orig_path = file_paths[i]
                report(pct, f"Вставка документа ({i + 1} из {total_files}): {os.path.basename(orig_path)}...")

                rot = rotations.get(orig_path, 0) % 360
                is_landscape = (rot in (90, 270))

                if i > 0:
                    # 2 = wdSectionBreakNextPage
                    sel.InsertBreak(2)
                    sec = master_doc.Sections(master_doc.Sections.Count)
                    # 1 = wdOrientLandscape, 0 = wdOrientPortrait
                    sec.PageSetup.Orientation = 1 if is_landscape else 0
                else:
                    sec = master_doc.Sections(1)
                    sec.PageSetup.Orientation = 1 if is_landscape else 0

                sel.InsertFile(docx_path)

            check_cancel()
            report(95, "Сохранение итогового Word-документа...")

            abs_out = os.path.abspath(output_path)
            os.makedirs(os.path.dirname(abs_out), exist_ok=True)
            master_doc.SaveAs2(abs_out, FileFormat=16)

            pages_count = 0
            try:
                pages_count = master_doc.ComputeStatistics(2)  # 2 = wdStatisticPages
            except Exception:
                pass

            report(100, "Сборка отчёта Word успешно завершена!")

            return {
                "success": True,
                "output_path": abs_out,
                "total_input_files": total_files,
                "total_input_pages": pages_count or total_files,
                "total_sheets": pages_count or total_files,
                "file_size": os.path.getsize(abs_out),
                "layout_mode": "standard",
                "output_format": "docx"
            }

        finally:
            if master_doc is not None:
                try:
                    master_doc.Close(SaveChanges=0)
                except Exception:
                    pass
                del master_doc
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
            shutil.rmtree(temp_dir, ignore_errors=True)


def build_arbitr_report(
    file_paths: list[str],
    output_path: str,
    progress_callback=None,
    is_cancelled=None,
    layout_mode: str = "2up",
    output_format: str = "pdf",
    rotations: dict[str, int] = None,
    new_sheet_for_landscape: bool = True
) -> dict:
    """
    Combines input files in given order into a final report.
    - layout_mode: 'standard' (1-to-1 pages) or '2up' (compact A4 2-on-1 sheet).
    - output_format: 'pdf' or 'docx'.
    - rotations: dict {file_path: rotation_deg (0, 90, 180, 270)}.
    """
    if output_format.lower() == "docx":
        return build_docx_report(
            file_paths=file_paths,
            output_path=output_path,
            progress_callback=progress_callback,
            is_cancelled=is_cancelled,
            rotations=rotations
        )

    def report(percent: int, msg: str):
        if progress_callback:
            progress_callback(percent, msg)

    def check_cancel():
        if is_cancelled and is_cancelled():
            raise InterruptedError("Операция отменена пользователем.")

    total_files = len(file_paths)
    if total_files == 0:
        raise ValueError("Список файлов пуст.")

    rotations = rotations or {}
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
                intermediate_pdfs.append((path, out_pdf))
            elif ext == ".pdf":
                report(pct, f"Чтение PDF: {fname}...")
                intermediate_pdfs.append((path, path))
            else:
                raise ValueError(f"Неподдерживаемый формат файла: {path}")

        check_cancel()
        report(60, "Анализ страниц и применение ориентации...")

        # Step 2: Read all pages from intermediate PDFs and apply rotation
        collected_pages = []
        for orig_path, pdf_path in intermediate_pdfs:
            check_cancel()
            rot = rotations.get(orig_path, 0) % 360
            reader = pypdf.PdfReader(pdf_path)
            for page in reader.pages:
                if rot != 0:
                    page.rotate(rot)
                collected_pages.append(page)

        total_input_pages = len(collected_pages)
        if total_input_pages == 0:
            raise ValueError("Исходные документы не содержат страниц.")

        # Step 3: Layout pages
        writer = pypdf.PdfWriter()

        if layout_mode == "standard":
            # Ordinary PDF merge: keep pages as they are (1-to-1)
            report(65, "Объединение страниц в стандартном формате...")
            for idx, p in enumerate(collected_pages):
                check_cancel()
                pct = 65 + int((idx / total_input_pages) * 25)
                report(pct, f"Добавление страницы ({idx + 1} из {total_input_pages})...")
                writer.add_page(p)
            sheet_count = total_input_pages
        else:
            # 2-up compact A4 Landscape
            sheet_count = 0
            idx = 0
            while idx < total_input_pages:
                check_cancel()
                pct = 65 + int((idx / total_input_pages) * 25)
                report(pct, f"Размещение страниц на листах ({idx + 1} из {total_input_pages})...")

                page1 = collected_pages[idx]
                rot1 = getattr(page1, 'rotation', 0) % 360
                orig_w1 = float(page1.mediabox.width)
                orig_h1 = float(page1.mediabox.height)
                pw1, ph1 = (orig_h1, orig_w1) if rot1 in (90, 270) else (orig_w1, orig_h1)
                is_land1 = pw1 > ph1

                if is_land1:
                    add_sheet_2up(writer, left_page=page1, right_page=None)
                    sheet_count += 1
                    idx += 1
                else:
                    page2 = None
                    if idx + 1 < total_input_pages:
                        next_p = collected_pages[idx + 1]
                        rot2 = getattr(next_p, 'rotation', 0) % 360
                        orig_w2 = float(next_p.mediabox.width)
                        orig_h2 = float(next_p.mediabox.height)
                        pw2, ph2 = (orig_h2, orig_w2) if rot2 in (90, 270) else (orig_w2, orig_h2)
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
        abs_out = os.path.abspath(output_path)
        os.makedirs(os.path.dirname(abs_out), exist_ok=True)
        with open(abs_out, "wb") as f_out:
            writer.write(f_out)

        report(100, "Сборка отчёта успешно завершена!")

        return {
            "success": True,
            "output_path": abs_out,
            "total_input_files": total_files,
            "total_input_pages": total_input_pages,
            "total_sheets": sheet_count,
            "file_size": os.path.getsize(abs_out),
            "layout_mode": layout_mode,
            "output_format": "pdf"
        }

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
