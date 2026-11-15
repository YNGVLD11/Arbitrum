import os
import tempfile
import shutil
import threading
import pypdf

# Dimensions for A4 in points (210 mm x 297 mm)
A4_PORTRAIT_W = 595.28
A4_PORTRAIT_H = 841.89
A4_HALF_H = A4_PORTRAIT_H / 2.0
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


def _place_page_in_slot(sheet: pypdf.PageObject, page: pypdf.PageObject, slot_index: int):
    """
    Places an input page into one of two half-page slots on an A4 portrait sheet.
    slot_index 0: bottom half (Y in [0, A4_HALF_H]), corresponds to left page when rotated.
    slot_index 1: top half (Y in [A4_HALF_H, A4_PORTRAIT_H]), corresponds to right page when rotated.
    """
    orig_w = float(page.mediabox.width)
    orig_h = float(page.mediabox.height)
    rot = getattr(page, 'rotation', 0) % 360

    pw, ph = (orig_h, orig_w) if rot in (90, 270) else (orig_w, orig_h)
    is_portrait = (ph >= pw)

    page_copy = pypdf.PageObject.create_blank_page(width=orig_w, height=orig_h)
    page_copy.merge_page(page)

    y_offset = slot_index * A4_HALF_H

    if is_portrait:
        # Rotate 90 deg CCW so text flows horizontally across the vertical sheet
        scale = min(A4_PORTRAIT_W / ph, A4_HALF_H / pw)
        fitted_w = ph * scale
        fitted_h = pw * scale
        tx = (A4_PORTRAIT_W - fitted_w) / 2.0 + fitted_w
        ty = y_offset + (A4_HALF_H - fitted_h) / 2.0
        t = pypdf.Transformation().rotate(90).scale(scale, scale).translate(tx, ty)
        sheet.merge_transformed_page(page_copy, t)
    else:
        # Page is already landscape: fits directly into slot
        scale = min(A4_PORTRAIT_W / pw, A4_HALF_H / ph)
        fitted_w = pw * scale
        fitted_h = ph * scale
        tx = (A4_PORTRAIT_W - fitted_w) / 2.0
        ty = y_offset + (A4_HALF_H - fitted_h) / 2.0
        t = pypdf.Transformation().scale(scale, scale).translate(tx, ty)
        sheet.merge_transformed_page(page_copy, t)


def add_sheet_2up(writer: pypdf.PdfWriter, left_page=None, right_page=None):
    """
    Adds a single A4 Portrait sheet (210 x 297 mm, 595.28 x 841.89 pt) containing
    up to 2 pages (bottom and top halves, corresponding to left and right in reading orientation).
    Complies strictly with Russian Post electronic registered letter requirements (A4, 210 x 297 mm).
    """
    sheet = writer.add_blank_page(width=A4_PORTRAIT_W, height=A4_PORTRAIT_H)

    if left_page is not None:
        _place_page_in_slot(sheet, left_page, slot_index=0)

    if right_page is not None:
        _place_page_in_slot(sheet, right_page, slot_index=1)

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
            # 2-up compact A4 Portrait (2 pages per sheet)
            sheet_count = 0
            idx = 0
            while idx < total_input_pages:
                check_cancel()
                pct = 65 + int((idx / total_input_pages) * 25)
                report(pct, f"Размещение страниц на листах ({idx + 1} из {total_input_pages})...")

                page1 = collected_pages[idx]
                page2 = collected_pages[idx + 1] if (idx + 1 < total_input_pages) else None

                add_sheet_2up(writer, left_page=page1, right_page=page2)
                sheet_count += 1
                idx += 2 if page2 is not None else 1

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
