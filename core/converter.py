import os
import tempfile
import shutil
import pypdf

# Dimensions for A4 in points (297 mm x 210 mm)
A4_LANDSCAPE_W = 841.89
A4_LANDSCAPE_H = 595.28
A4_HALF_W = A4_LANDSCAPE_W / 2.0


def convert_word_to_pdf(doc_path: str, output_pdf_path: str):
    """
    Converts .doc or .docx to PDF using Microsoft Word COM automation.
    Thread-safe with pythoncom initialization.
    """
    import pythoncom
    import win32com.client

    pythoncom.CoInitialize()
    word = None
    doc = None
    try:
        word = win32com.client.DispatchEx("Word.Application")
        word.Visible = False
        word.DisplayAlerts = 0  # wdAlertsNone

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
        pythoncom.CoUninitialize()


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

    temp_dir = tempfile.mkdtemp(prefix="arbitr_build_")
    try:
        total_files = len(file_paths)
        if total_files == 0:
            raise ValueError("Список файлов для сборки пуст.")

        # Step 1: Convert all non-PDF files to PDF
        pdf_docs = []
        for idx, fpath in enumerate(file_paths):
            if is_cancelled and is_cancelled():
                raise InterruptedError("Операция отменена пользователем.")

            fname = os.path.basename(fpath)
            pct = int((idx / total_files) * 50)
            report(pct, f"Подготовка файла {idx + 1} из {total_files}: {fname}")

            ext = os.path.splitext(fpath)[1].lower()
            if ext == ".pdf":
                pdf_docs.append(fpath)
            elif ext in [".doc", ".docx"]:
                report(pct, f"Конвертация Word в PDF: {fname}...")
                temp_pdf = os.path.join(temp_dir, f"converted_{idx}_{fname}.pdf")
                convert_word_to_pdf(fpath, temp_pdf)
                pdf_docs.append(temp_pdf)
            else:
                raise ValueError(f"Неподдерживаемый формат файла: {fname} ({ext})")

        report(55, "Чтение страниц и определение ориентации...")

        # Step 2: Read pages from all PDFs and separate/group by orientation
        # We preserve the user's document sequence
        doc_pages_list = []
        total_source_pages = 0
        for p_pdf in pdf_docs:
            reader = pypdf.PdfReader(p_pdf)
            pages = list(reader.pages)
            doc_pages_list.append(pages)
            total_source_pages += len(pages)

        report(65, "Компоновка страниц в макет 2-на-лист (A4 Альбомный)...")

        writer = pypdf.PdfWriter()

        if new_sheet_for_landscape:
            # Group contiguous pages by orientation (portrait vs landscape)
            # within the specified document order
            all_groups = []
            current_group = []
            current_is_landscape = None

            for doc_pages in doc_pages_list:
                for page in doc_pages:
                    w = float(page.mediabox.width)
                    h = float(page.mediabox.height)
                    is_land = w > h

                    if current_is_landscape is None:
                        current_is_landscape = is_land
                        current_group.append(page)
                    elif current_is_landscape == is_land:
                        current_group.append(page)
                    else:
                        all_groups.append((current_is_landscape, current_group))
                        current_group = [page]
                        current_is_landscape = is_land

            if current_group:
                all_groups.append((current_is_landscape, current_group))

            total_groups = len(all_groups)
            for g_idx, (is_land, group_pages) in enumerate(all_groups):
                if is_cancelled and is_cancelled():
                    raise InterruptedError("Операция отменена пользователем.")

                group_type = "альбомного" if is_land else "книжного"
                report(70 + int((g_idx / total_groups) * 20), f"Сборка секции {group_type} формата...")

                for i in range(0, len(group_pages), 2):
                    p_left = group_pages[i]
                    p_right = group_pages[i + 1] if i + 1 < len(group_pages) else None
                    add_sheet_2up(writer, p_left, p_right)
        else:
            # Flat 2-up without section breaks
            all_pages = [page for doc_pages in doc_pages_list for page in doc_pages]
            for i in range(0, len(all_pages), 2):
                if is_cancelled and is_cancelled():
                    raise InterruptedError("Операция отменена пользователем.")
                p_left = all_pages[i]
                p_right = all_pages[i + 1] if i + 1 < len(all_pages) else None
                add_sheet_2up(writer, p_left, p_right)

        report(92, "Запись итогового PDF-документа...")
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "wb") as f_out:
            writer.write(f_out)

        report(100, "Сборка успешно завершена!")

        return {
            "output_path": output_path,
            "total_sheets": len(writer.pages),
            "total_source_pages": total_source_pages,
            "file_size": os.path.getsize(output_path)
        }
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
