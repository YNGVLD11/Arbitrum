import os
import re
from datetime import datetime
import docx
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import parse_xml, OxmlElement
from docx.oxml.ns import nsdecls, qn

from core.court_parser import inflect_fio


def set_cell_borders(cell, top="single", bottom="single", left="single", right="single",
                     color="000000", sz="4"):
    """Устанавливает тонкие рамки таблицы."""
    tcPr = cell._tc.get_or_add_tcPr()
    tcBorders = parse_xml(
        f'<w:tcBorders {nsdecls("w")}>\n'
        f'  <w:top w:val="{top}" w:sz="{sz}" w:space="0" w:color="{color}"/>\n'
        f'  <w:left w:val="{left}" w:sz="{sz}" w:space="0" w:color="{color}"/>\n'
        f'  <w:bottom w:val="{bottom}" w:sz="{sz}" w:space="0" w:color="{color}"/>\n'
        f'  <w:right w:val="{right}" w:sz="{sz}" w:space="0" w:color="{color}"/>\n'
        f'</w:tcBorders>'
    )
    tcPr.append(tcBorders)


def set_cell_margins(cell, top=20, bottom=20, left=60, right=60):
    """Сверхкомпактные внутренние отступы ячейки таблицы."""
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(
        f'<w:tcMar {nsdecls("w")}>\n'
        f'  <w:top w:w="{top}" w:type="dxa"/>\n'
        f'  <w:bottom w:w="{bottom}" w:type="dxa"/>\n'
        f'  <w:left w:w="{left}" w:type="dxa"/>\n'
        f'  <w:right w:w="{right}" w:type="dxa"/>\n'
        f'</w:tcMar>'
    )
    tcPr.append(tcMar)


def clean_address(addr: str) -> str:
    """Удаляет 6-значный почтовый индекс и начальные запятые."""
    if not addr:
        return ""
    res = re.sub(r"^\s*\d{6}\s*,\s*", "", addr.strip())
    res = re.sub(r"^\s*\d{6}\s*", "", res)
    return res.strip()


def clean_snils_digits(snils: str) -> str:
    """Удаляет тире и пробелы из СНИЛС (только цифры)."""
    if not snils:
        return ""
    return re.sub(r"[^\d]", "", snils)


def abbreviate_court(court_name: str) -> str:
    """Сокращает 'Арбитражный суд ...' до 'АС ...'."""
    if not court_name:
        return ""
    c = court_name.strip()
    c = re.sub(r"^Арбитражный\s+суд\s+", "АС ", c, flags=re.IGNORECASE)
    return c


def format_short_fio(full_name: str) -> str:
    """Иванов Иван Иванович -> Иванов И. И. или Гусарова К. А."""
    if not full_name:
        return ""
    parts = full_name.strip().split()
    if len(parts) == 1:
        return parts[0]
    elif len(parts) == 2:
        return f"{parts[0]} {parts[1][0]}."
    else:
        return f"{parts[0]} {parts[1][0]}. {parts[2][0]}."


def generate_kommersant_doc(debtor_data: dict, manager_settings, output_path: str):
    """
    Генерирует Заявку-Договор в АО «Коммерсантъ» шрифтом Arial,
    с компактной таблицей, сокращенным текстом и подписью в правой колонке.
    """
    doc = docx.Document()

    # Задаем шрифт по умолчанию Arial
    style_normal = doc.styles["Normal"]
    style_normal.font.name = "Arial"
    style_normal.font.size = Pt(8.5)

    # Поля страницы
    for section in doc.sections:
        section.top_margin = Inches(0.4)
        section.bottom_margin = Inches(0.4)
        section.left_margin = Inches(0.5)
        section.right_margin = Inches(0.5)

    today_str = datetime.now().strftime("%d.%m.%Y")

    raw = debtor_data.get("parsed_raw") or {}
    debtor_fio = debtor_data.get("full_name") or raw.get("debtor_fio") or ""
    debtor_fio_gen = raw.get("debtor_fio_gen") or inflect_fio(debtor_fio, "gent") or debtor_fio

    birth_date = debtor_data.get("birth_date") or raw.get("debtor_birth_date") or ""
    birth_place = debtor_data.get("birth_place") or raw.get("debtor_birth_place") or ""
    address = debtor_data.get("address") or raw.get("debtor_address") or ""
    inn = debtor_data.get("inn") or raw.get("debtor_inn") or ""
    snils = debtor_data.get("snils") or raw.get("debtor_snils") or ""
    court_name = debtor_data.get("court_name") or raw.get("court_name") or ""
    case_number = debtor_data.get("case_number") or raw.get("case_number") or ""
    decision_date = debtor_data.get("decision_date") or raw.get("decision_date") or ""

    mgr_fio = getattr(manager_settings, "manager_fio", "") or "Гусарова Ксения Алексеевна"
    mgr_phone = getattr(manager_settings, "manager_phone", "") or "+79139890163"
    mgr_email = getattr(manager_settings, "manager_email", "") or "kseniya_gusarova@mail.ru"
    mgr_inn = getattr(manager_settings, "manager_inn", "") or "380470431942"
    mgr_snils = getattr(manager_settings, "manager_snils", "") or "136-556-599 95"
    mgr_addr = getattr(manager_settings, "manager_corr_address", "") or "630007, г. Новосибирск, а/я 1"
    mgr_sro = "САМРО \"АССОЦИАЦИЯ АНТИКРИЗИСНЫХ УПРАВЛЯЮЩИХ\""

    # Шапка
    p_head = doc.add_paragraph()
    p_head.paragraph_format.space_before = Pt(0)
    p_head.paragraph_format.space_after = Pt(2)
    p_head.paragraph_format.line_spacing = 1.0

    run_org = p_head.add_run("В АКЦИОНЕРНОЕ ОБЩЕСТВО «КОММЕРСАНТЪ»")
    run_org.bold = True
    run_org.font.size = Pt(9.5)
    run_org.font.name = "Arial"

    r_date = p_head.add_run(f"    Дата заполнения: {today_str}\n")
    r_date.font.size = Pt(9)
    r_date.font.name = "Arial"

    # 1. Таблица данных
    table_data = [
        ("1", "Данные об арбитражном управляющем:", ""),
        ("", "ФИО а/у", mgr_fio),
        ("", "СРО а/у", mgr_sro),
        ("", "Адрес а/у", mgr_addr),
        ("", "СНИЛС а/у", mgr_snils),
        ("", "ИНН а/у", mgr_inn),
        ("", "Тел., факс, e-mail", f"тел.: {mgr_phone}, e-mail: {mgr_email}"),
        ("2", "Данные о должнике-банкроте:", ""),
        ("", "ФИО Гражданина", debtor_fio),
        ("", "ФИО Гражданина (если менялось)", ""),
        ("", "Дата рождения", birth_date),
        ("", "Место рождения", birth_place),
        ("", "Место жительства согласно документам о регистрации", address),
        ("", "Место фактического жительства", ""),
        ("", "ИНН (при наличии)", inn),
        ("", "СНИЛС", snils),
        ("", "Тел., факс, e-mail", ""),
        ("", "Наименование суда", court_name),
        ("", "Дело о банкротстве №", case_number),
        ("", "Дата вынесенного судебного акта", decision_date),
    ]

    tbl = doc.add_table(rows=len(table_data), cols=3)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl.autofit = False

    col_widths = [Inches(0.35), Inches(2.6), Inches(4.3)]

    for row_idx, row_vals in enumerate(table_data):
        row = tbl.rows[row_idx]
        is_header_row = (row_vals[0] in ["1", "2"])

        # Col 0 (Номер 1 или 2)
        cell0 = row.cells[0]
        cell0.width = col_widths[0]
        set_cell_borders(cell0)
        set_cell_margins(cell0, top=15, bottom=15, left=40, right=40)
        cell0.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        p0 = cell0.paragraphs[0]
        p0.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p0.paragraph_format.space_before = Pt(0)
        p0.paragraph_format.space_after = Pt(0)
        p0.paragraph_format.line_spacing = 1.0
        r0 = p0.add_run(row_vals[0])
        r0.font.name = "Arial"
        r0.font.size = Pt(8)
        r0.bold = True

        # Col 1 (Название поля)
        cell1 = row.cells[1]
        cell1.width = col_widths[1]
        set_cell_borders(cell1)
        set_cell_margins(cell1, top=15, bottom=15, left=50, right=50)
        cell1.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        p1 = cell1.paragraphs[0]
        p1.paragraph_format.space_before = Pt(0)
        p1.paragraph_format.space_after = Pt(0)
        p1.paragraph_format.line_spacing = 1.0
        r1 = p1.add_run(row_vals[1])
        r1.font.name = "Arial"
        r1.font.size = Pt(8)
        if is_header_row:
            r1.bold = True

        # Col 2 (Значение поля)
        cell2 = row.cells[2]
        cell2.width = col_widths[2]
        set_cell_borders(cell2)
        set_cell_margins(cell2, top=15, bottom=15, left=50, right=50)
        cell2.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        p2 = cell2.paragraphs[0]
        p2.paragraph_format.space_before = Pt(0)
        p2.paragraph_format.space_after = Pt(0)
        p2.paragraph_format.line_spacing = 1.0
        r2 = p2.add_run(row_vals[2])
        r2.font.name = "Arial"
        r2.font.size = Pt(8)

    # Заявка-договор
    p_mid = doc.add_paragraph()
    p_mid.paragraph_format.space_before = Pt(3)
    p_mid.paragraph_format.space_after = Pt(2)
    p_mid.paragraph_format.line_spacing = 1.05

    r_buh = p_mid.add_run("Отчетные бухгалтерские документы за публикацию оформить на (нужное отметить): 1 ☒    или    2 ☐\n")
    r_buh.font.name = "Arial"
    r_buh.font.size = Pt(8)

    r_title = p_mid.add_run("Заявка-Договор на публикацию сообщений о банкротстве\n")
    r_title.bold = True
    r_title.font.name = "Arial"
    r_title.font.size = Pt(9)

    r_check = p_mid.add_run(
        "Просим разместить в газете «Коммерсантъ» на условиях предоплаты сообщение (отметить):\n"
        "☐  о признании обоснованным заявления о признании гражданина банкротом и введении реструктуризации его долгов\n"
        "☒  о признании гражданина банкротом и введении реализации имущества гражданина."
    )
    r_check.font.name = "Arial"
    r_check.font.size = Pt(8)

    # Блок: Содержание сообщения (МАКСИМАЛЬНО СОКРАЩЕННОЕ)
    court_short = abbreviate_court(court_name)
    clean_addr = clean_address(address)
    snils_no_dash = clean_snils_digits(snils)
    mgr_snils_no_dash = clean_snils_digits(mgr_snils)

    reduced_text = (
        f"{court_short} реш. {decision_date} по делу {case_number} признал банкротом "
        f"{debtor_fio_gen} (СНИЛС {snils_no_dash}, ИНН {inn}, {clean_addr}) "
        f"и ввел реализацию имущества сроком на 6 мес. "
        f"ФУ {mgr_fio} (ИНН {mgr_inn}, СНИЛС {mgr_snils_no_dash}), "
        f"член Саморегулируемая межрегиональная общественная организация «Ассоциация антикризисных управляющих» "
        f"(ОГРН 1026300003751, ИНН 6315944042, г. Самара, Московское ш., 18 км). "
        f"Требования - 2 мес. с публикации: {mgr_addr}. С/з не назначено."
    )

    p_msg_hdr = doc.add_paragraph()
    p_msg_hdr.paragraph_format.space_before = Pt(3)
    p_msg_hdr.paragraph_format.space_after = Pt(1)
    r_mh = p_msg_hdr.add_run("Содержание сообщения:")
    r_mh.bold = True
    r_mh.font.name = "Arial"
    r_mh.font.size = Pt(8.5)

    p_msg = doc.add_paragraph()
    p_msg.paragraph_format.space_before = Pt(0)
    p_msg.paragraph_format.space_after = Pt(3)
    p_msg.paragraph_format.line_spacing = 1.05
    r_m = p_msg.add_run(reduced_text)
    r_m.font.name = "Arial"
    r_m.font.size = Pt(8)

    # Правила и реквизиты
    p_rules = doc.add_paragraph()
    p_rules.paragraph_format.space_before = Pt(0)
    p_rules.paragraph_format.space_after = Pt(3)
    p_rules.paragraph_format.line_spacing = 1.0
    rules_text = (
        "Согласно п. 5 ст. 213.7 ФЗ «О несостоятельности (банкротстве)» подлежащие опубликованию сведения должны содержать идентифицирующие физическое лицо сведения, указанные выше в данных о должнике.\n"
        "К заявке прилагаются подтверждающие документы в противном случае заявка не обрабатывается.\n"
        "Гарантирую оплату по реквизитам:\n"
        "ПОЛУЧАТЕЛЬ: АО «КОММЕРСАНТЪ» ОГРН 1027700204751 ИНН 7707120552 КПП 770301001; р/с № 40702810302090005433 в АО \"АЛЬФА-БАНК\" Г. МОСКВА к/с № 30101810200000000593 БИК 044525593\n"
        "• Публикация объявлений производится в срок не более 10 дней с даты получения Заявки при условии поступления средств не позднее среды 13:00 мск.\n"
        "• Подписывая настоящую заявку, выражаю согласие на получение всех отчетных документов через систему «Диадок» (diadoc.ru)."
    )
    r_r = p_rules.add_run(rules_text)
    r_r.font.name = "Arial"
    r_r.font.size = Pt(6.5)
    r_r.font.color.rgb = RGBColor(80, 80, 80)

    # Блок подписи: колонка 0 текст (Заказчик: Гусарова К. А. финансовый управляющий),
    # колонка 1 - факсимиле подписи ровно на месте подписи
    sig_table = doc.add_table(rows=1, cols=2)
    sig_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    sig_table.autofit = False
    sig_table.rows[0].cells[0].width = Inches(4.8)
    sig_table.rows[0].cells[1].width = Inches(2.4)

    c_sig_txt = sig_table.rows[0].cells[0]
    set_cell_borders(c_sig_txt, top="none", bottom="none", left="none", right="none")
    p_st = c_sig_txt.paragraphs[0]
    p_st.paragraph_format.space_before = Pt(4)
    p_st.paragraph_format.space_after = Pt(0)
    mgr_short = format_short_fio(mgr_fio)
    r_st = p_st.add_run(f"Заказчик:  {mgr_short} финансовый управляющий")
    r_st.font.name = "Arial"
    r_st.font.size = Pt(9)
    r_st.bold = True

    c_sig_img = sig_table.rows[0].cells[1]
    set_cell_borders(c_sig_img, top="none", bottom="none", left="none", right="none")
    p_si = c_sig_img.paragraphs[0]
    p_si.paragraph_format.space_before = Pt(0)
    p_si.paragraph_format.space_after = Pt(0)
    p_si.alignment = WD_ALIGN_PARAGRAPH.LEFT

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sig_path = os.path.join(base_dir, "assets", "signature.png")
    if os.path.exists(sig_path):
        run_sig = p_si.add_run()
        run_sig.add_picture(sig_path, width=Inches(1.1))

    doc.save(output_path)


def generate_efrsb_doc(debtor_data: dict, manager_settings, output_path: str):
    """
    Генерирует текст сообщения для ЕФРСБ (Word-документ) с чистыми абзацами (Enter)
    без символов разрыва строки Shift+Enter.
    """
    doc = docx.Document()

    for section in doc.sections:
        section.top_margin = Inches(0.8)
        section.bottom_margin = Inches(0.8)
        section.left_margin = Inches(0.8)
        section.right_margin = Inches(0.8)

    raw = debtor_data.get("parsed_raw") or {}
    debtor_fio = debtor_data.get("full_name") or raw.get("debtor_fio") or ""
    debtor_fio_gen = raw.get("debtor_fio_gen") or inflect_fio(debtor_fio, "gent") or debtor_fio

    birth_date = debtor_data.get("birth_date") or raw.get("debtor_birth_date") or ""
    birth_place = debtor_data.get("birth_place") or raw.get("debtor_birth_place") or ""
    address = debtor_data.get("address") or raw.get("debtor_address") or ""
    inn = debtor_data.get("inn") or raw.get("debtor_inn") or ""
    snils = debtor_data.get("snils") or raw.get("debtor_snils") or ""
    court_name = debtor_data.get("court_name") or raw.get("court_name") or ""
    case_number = debtor_data.get("case_number") or raw.get("case_number") or ""
    decision_date = debtor_data.get("decision_date") or raw.get("decision_date") or ""

    mgr_fio = getattr(manager_settings, "manager_fio", "") or "Гусарова Ксения Алексеевна"
    mgr_phone = getattr(manager_settings, "manager_phone", "") or "+79139890163"
    mgr_email = getattr(manager_settings, "manager_email", "") or "kseniya_gusarova@mail.ru"
    mgr_inn = getattr(manager_settings, "manager_inn", "") or "380470431942"
    mgr_snils = getattr(manager_settings, "manager_snils", "") or "136-556-599 95"
    mgr_addr = getattr(manager_settings, "manager_corr_address", "") or "630007, г. Новосибирск, а/я 1"
    mgr_sro = "Саморегулируемая межрегиональная общественная организация \"Ассоциация антикризисных управляющих\" (ОГРН 1026300003751, ИНН 6315944042, адрес: 443072, г. Самара, Московское шоссе, 18-й км)"

    # Заголовок
    p_title = doc.add_paragraph()
    p_title.paragraph_format.space_before = Pt(0)
    p_title.paragraph_format.space_after = Pt(14)
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_t = p_title.add_run("СООБЩЕНИЕ О ВВЕДЕНИИ РЕАЛИЗАЦИИ ИМУЩЕСТВА (ДЛЯ ЕФРСБ)")
    r_t.bold = True
    r_t.font.name = "Times New Roman"
    r_t.font.size = Pt(12)

    paragraphs_text = [
        f"Решением {court_name} от {decision_date} г. по делу № {case_number} "
        f"{debtor_fio} (дата рождения: {birth_date} г., место рождения: {birth_place}, "
        f"СНИЛС: {snils}, ИНН: {inn}, адрес регистрации по месту жительства: {address}) "
        f"признан(а) несостоятельным(ой) (банкротом) и введена процедура реализации имущества гражданина.",

        f"Финансовым управляющим утверждена {mgr_fio} (ИНН {mgr_inn}, СНИЛС {mgr_snils}, "
        f"телефон: {mgr_phone}, эл. почта: {mgr_email}) — член {mgr_sro}.",

        f"Реестр требований кредиторов подлежит закрытию по истечении двух месяцев с даты опубликования "
        f"сообщения о введении реализации имущества {debtor_fio_gen} в газете «Коммерсантъ».",

        f"Адрес для заявления кредиторами требований и направления корреспонденции финансовому управляющему: "
        f"{mgr_addr}."
    ]

    for p_txt in paragraphs_text:
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(8)
        p.paragraph_format.line_spacing = 1.15
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        run = p.add_run(p_txt)
        run.font.name = "Times New Roman"
        run.font.size = Pt(11)

    doc.save(output_path)


def generate_consent_doc(debtor_data: dict, manager_settings, output_path: str):
    """
    Генерирует Заявление-согласие арбитражного управляющего в суд и СРО
    на базе оригинального шаблона с сохранением всех стилей, отступов и росписи.
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    template_path = os.path.join(base_dir, "assets", "templates", "Шаблон_Согласие_АУ.docx")

    if not os.path.exists(template_path):
        raise FileNotFoundError(f"Файл шаблона заявления-согласия не найден: {template_path}")

    doc = docx.Document(template_path)

    raw = debtor_data.get("parsed_raw") or {}
    debtor_fio = debtor_data.get("full_name") or raw.get("debtor_fio") or ""
    birth_date = debtor_data.get("birth_date") or raw.get("debtor_birth_date") or ""

    court_name = debtor_data.get("court_name") or raw.get("court_name") or "АРБИТРАЖНЫЙ СУД НОВОСИБИРСКОЙ ОБЛАСТИ"
    case_number = debtor_data.get("case_number") or raw.get("case_number") or ""

    mgr_fio = getattr(manager_settings, "manager_fio", "") or "Гусарова Ксения Андреевна"
    mgr_addr = getattr(manager_settings, "manager_corr_address", "") or "630007, г. Новосибирск, а/я 1"

    # Падеж управляющего в шапке (от кого): Гусаровой Ксении Андреевны
    mgr_gent = inflect_fio(mgr_fio, "gent") or mgr_fio
    # Падеж должника (в отношении кого): Аршикова Михаила Викторовича
    debtor_gent = raw.get("debtor_fio_gen") or inflect_fio(debtor_fio, "gent") or debtor_fio

    short_mgr = format_short_fio(mgr_fio)
    today_str = datetime.now().strftime("%d.%m.%Y")

    def set_clean_text(paragraph, text: str):
        """Оставляет первый run со стилями шаблона и удаляет остальные."""
        if not paragraph.runs:
            paragraph.add_run(text)
            return
        for r in paragraph.runs[1:]:
            paragraph._p.remove(r._r)
        paragraph.runs[0].text = text

    # P0: Суд (заглавными буквами)
    set_clean_text(doc.paragraphs[0], court_name.upper())

    # P3: ФИО арбитражного управляющего (в родительном падеже)
    set_clean_text(doc.paragraphs[3], mgr_gent)

    # P4: Адрес для корреспонденции
    set_clean_text(doc.paragraphs[4], f"Адрес для корреспонденции: {mgr_addr}")

    # P5: Номер дела
    set_clean_text(doc.paragraphs[5], f"ДЕЛО {case_number}")

    # P9: Я, Гусарова Ксения Андреевна, являющаяся членом...
    p9_text = (
        f"Я, {mgr_fio}, являющаяся членом САМРО «Ассоциация антикризисных управляющих», "
        f"заявляю о своем согласии исполнять обязанности арбитражного "
        f"(временного административного, внешнего, конкурсного) управляющего при проведении процедуры, "
        f"применяемой в деле о банкротстве в отношении"
    )
    set_clean_text(doc.paragraphs[9], p9_text)

    # P10: Должник и дата рождения
    birth_part = f" дата рождения: {birth_date}" if birth_date else ""
    p10_text = f"{debtor_gent}{birth_part}"
    set_clean_text(doc.paragraphs[10], p10_text)

    # P18: Дата (текущая)
    set_clean_text(doc.paragraphs[18], f"{today_str} г.")

    # Таблица с подписью: t.rows[0].cells[1] -> Фамилия И. О. управляющего
    if doc.tables:
        t = doc.tables[0]
        if len(t.rows) > 0 and len(t.rows[0].cells) > 1:
            p_cell = t.rows[0].cells[1].paragraphs[0]
            set_clean_text(p_cell, short_mgr)

    doc.save(output_path)
