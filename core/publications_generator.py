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
    Генерирует Заявку-Договор в АО «Коммерсантъ» на базе оригинального шаблона
    assets/templates/Шаблон_Коммерсантъ_Заявка.docx с сохранением всех рамок,
    гарантийных реквизитов и подписи.
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    template_path = os.path.join(base_dir, "assets", "templates", "Шаблон_Коммерсантъ_Заявка.docx")

    if not os.path.exists(template_path):
        raise FileNotFoundError(f"Файл шаблона заявки Коммерсантъ не найден: {template_path}")

    doc = docx.Document(template_path)

    today_str = datetime.now().strftime("%d.%m.%Y")

    raw = debtor_data.get("parsed_raw") or {}
    debtor_fio = debtor_data.get("full_name") or raw.get("debtor_fio") or ""
    debtor_fio_gen = raw.get("debtor_fio_gen") or inflect_fio(debtor_fio, "gent") or debtor_fio
    debtor_fio_accs = inflect_fio(debtor_fio, "accs") or debtor_fio

    birth_date = debtor_data.get("birth_date") or raw.get("debtor_birth_date") or ""
    birth_place = debtor_data.get("birth_place") or raw.get("debtor_birth_place") or ""
    address = debtor_data.get("address") or raw.get("debtor_address") or ""
    inn = debtor_data.get("inn") or raw.get("debtor_inn") or ""
    snils = debtor_data.get("snils") or raw.get("debtor_snils") or ""
    court_name = debtor_data.get("court_name") or raw.get("court_name") or ""
    case_number = debtor_data.get("case_number") or raw.get("case_number") or ""
    decision_date = debtor_data.get("decision_date") or raw.get("decision_date") or ""

    mgr_fio = getattr(manager_settings, "manager_fio", "") or "Гусарова Ксения Андреевна"
    mgr_phone = getattr(manager_settings, "manager_phone", "") or "+79139890163"
    mgr_email = getattr(manager_settings, "manager_email", "") or "kseniya_gusarova@mail.ru"
    mgr_inn = getattr(manager_settings, "manager_inn", "") or "380470431942"
    mgr_snils = getattr(manager_settings, "manager_snils", "") or "136-556-599 95"
    mgr_addr = getattr(manager_settings, "manager_corr_address", "") or "630007, г. Новосибирск, а/я 1"
    mgr_sro = "САМРО \"АССОЦИАЦИЯ АНТИКРИЗИСНЫХ УПРАВЛЯЮЩИХ\""

    def set_clean_text(paragraph, text: str):
        """Сохраняет форматирование первого run и заменяет текст."""
        if not paragraph.runs:
            paragraph.add_run(text)
            return
        for r in paragraph.runs[1:]:
            paragraph._p.remove(r._r)
        paragraph.runs[0].text = text

    # P0: В АКЦИОНЕРНОЕ ОБЩЕСТВО «КОММЕРСАНТЪ» Дата заполнения {today_str}
    if doc.paragraphs:
        set_clean_text(doc.paragraphs[0], f"В АКЦИОНЕРНОЕ ОБЩЕСТВО «КОММЕРСАНТЪ» Дата заполнения {today_str}")

    # Заполнение таблицы Table 0
    if doc.tables:
        t0 = doc.tables[0]
        # Маппинг строк таблицы 0 -> значения
        row_values = {
            1: mgr_fio,
            2: mgr_sro,
            3: mgr_addr,
            4: mgr_snils,
            5: mgr_inn,
            6: f"тел.: {mgr_phone}, e-mail: {mgr_email}",
            8: debtor_fio,
            9: "",  # ФИО (если менялось)
            10: birth_date,
            11: birth_place,
            12: address,
            13: "", # Фактическое место
            14: inn,
            15: snils,
            16: "", # Тел. должника
            17: court_name,
            18: case_number,
            19: decision_date,
        }

        for r_idx, val in row_values.items():
            if r_idx < len(t0.rows) and len(t0.rows[r_idx].cells) > 2:
                c2 = t0.rows[r_idx].cells[2]
                if c2.paragraphs:
                    set_clean_text(c2.paragraphs[0], val)

    # Содержимое сообщения (P7)
    court_short = abbreviate_court(court_name)
    clean_addr = clean_address(address)
    snils_no_dash = clean_snils_digits(snils)
    mgr_snils_no_dash = clean_snils_digits(mgr_snils)

    birth_part = f"{birth_date}, " if birth_date else ""
    place_part = f"{birth_place}, " if birth_place else ""

    reduced_text = (
        f"{court_short} реш. {decision_date} по делу {case_number} признал банкротом "
        f"{debtor_fio_accs} ({birth_part}{place_part}СНИЛС {snils_no_dash}, ИНН {inn}, {clean_addr}) "
        f"и ввел реализацию имущества сроком на 6 мес. "
        f"ФУ {mgr_fio} (ИНН {mgr_inn}, СНИЛС {mgr_snils_no_dash}), "
        f"член Саморегулируемая межрегиональная общественная организация «Ассоциация антикризисных управляющих» "
        f"(ОГРН 1026300003751, ИНН 6315944042, г. Самара, Московское ш., 18 км). "
        f"Требования - 2 мес. с публикации: {mgr_addr}. С/з не назначено."
    )

    if len(doc.paragraphs) > 7:
        set_clean_text(doc.paragraphs[7], reduced_text)

    # 4. Блок подписи: убираем Table 1 и лишние пустые абзацы, чтобы Word не создавал вторую страницу
    short_mgr = format_short_fio(mgr_fio)
    drawing_el = None
    if len(doc.tables) > 1:
        t1 = doc.tables[1]
        if len(t1.rows) > 0 and len(t1.rows[0].cells) > 1:
            drawings = t1.rows[0].cells[1].paragraphs[0]._p.xpath('.//w:drawing')
            if drawings:
                drawing_el = drawings[0]

        # Удаляем Table 1 и соседние пустые абзацы из тела документа
        body = doc._body._element
        tbl1_el = t1._tbl
        prev = tbl1_el.getprevious()
        nxt = tbl1_el.getnext()
        if prev is not None and prev.tag.endswith('p') and not prev.xpath('.//w:t'):
            body.remove(prev)
        if nxt is not None and nxt.tag.endswith('p') and not nxt.xpath('.//w:t'):
            body.remove(nxt)
        body.remove(tbl1_el)

    # Добавляем чистый абзац подписи с рисунком на той же строке
    p_sig = doc.add_paragraph()
    p_sig.paragraph_format.space_before = Pt(4)
    p_sig.paragraph_format.space_after = Pt(0)
    p_sig.paragraph_format.line_spacing = 1.0

    r_sig_txt = p_sig.add_run(f"Заказчик:  {short_mgr} финансовый управляющий    ")
    r_sig_txt.font.name = "Arial"
    r_sig_txt.font.size = Pt(8.5)
    r_sig_txt.bold = True

    if drawing_el is not None:
        # Корректируем размеры рисунка для идеальной компактности
        wp_inline = drawing_el.xpath('.//wp:inline')
        if wp_inline:
            ext_list = wp_inline[0].xpath('.//wp:extent')
            if ext_list:
                ext_list[0].set('cx', '520000')
                ext_list[0].set('cy', '520000')
        xfrm_list = drawing_el.xpath('.//a:xfrm/a:ext')
        if xfrm_list:
            xfrm_list[0].set('cx', '520000')
            xfrm_list[0].set('cy', '520000')

        # Опускаем картинку на базовую линию текста через w:position, чтобы она была на одном вертикальном уровне
        r_sig_img = OxmlElement('w:r')
        rPr = OxmlElement('w:rPr')
        pos = OxmlElement('w:position')
        pos.set(qn('w:val'), '-18')
        rPr.append(pos)
        r_sig_img.append(rPr)
        r_sig_img.append(drawing_el)
        p_sig._p.append(r_sig_img)

    # Устанавливаем комфортные отступы документа, чтобы весь контент гарантированно умещался на 1 листе
    for section in doc.sections:
        section.top_margin = Pt(28)
        section.bottom_margin = Pt(28)

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
    debtor_fio_accs = inflect_fio(debtor_fio, "accs") or debtor_fio

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
