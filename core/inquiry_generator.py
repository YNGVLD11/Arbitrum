import os
import re
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
import docx
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

TEMPLATES_CONFIG = [
    {"id": "banks", "name": "Банки (уведомление-запрос)", "file": "_Запрос в банки.docx"},
    {"id": "administration", "name": "Администрация", "file": "в_Администрацию_должник_супруг_РИ.docx"},
    {"id": "bti", "name": "БТИ", "file": "в_БТИ_РИ.docx"},
    {"id": "gibdd", "name": "ГИБДД", "file": "в_ГИБДД_должник_РИ.docx"},
    {"id": "gims", "name": "ГИМС", "file": "в_ГИМС_должник_супруг_РИ.docx"},
    {"id": "gostekhnadzor", "name": "Гостехнадзор", "file": "в_Гостехнадзор_должник_супруг_РИ.docx"},
    {"id": "egrn", "name": "ЕГРН (Росреестр сокращенный)", "file": "в_ЕГРН_(сокращенный)_должник_супруг_РИ.docx"},
    {"id": "zags", "name": "ЗАГС", "file": "в_ЗАГС_РИ.docx"},
    {"id": "ifns", "name": "ИФНС", "file": "в_ИФНС_должник_супруг_РИ.docx"},
    {"id": "rosaviation", "name": "Росавиация", "file": "в_Росавиацию_должник_супруг_РИ.docx"},
    {"id": "rosgvardiya", "name": "Росгвардия", "file": "в_Росгвардию_должник_супруг_РИ.docx"},
    {"id": "rosimushchestvo", "name": "Росимущество", "file": "в_Росимущество_РИ.docx"},
    {"id": "rospatent", "name": "Роспатент", "file": "в_Роспатент_должник_супруг_РИ.docx"},
    {"id": "rosreestr", "name": "Росреестр", "file": "в_Росреестр_должник_супруг_РИ.docx"},
    {"id": "fssp", "name": "ФССП (Служба судебных приставов)", "file": "в_ССП_РИ.docx"},
    {"id": "sfr", "name": "СФР (Социальный фонд)", "file": "в_СФР_РИ.docx"},
    {"id": "debtor_spouse", "name": "Должнику / Супругу", "file": "Должнику_супругу_РИ.docx"},
    {"id": "uvm", "name": "УВМ (МВД по вопросам миграции)", "file": "запрос в УВМ.docx"},
]

MONTHS_RU = {
    1: "января", 2: "февраля", 3: "марта", 4: "апреля", 5: "мая", 6: "июня",
    7: "июля", 8: "августа", 9: "сентября", 10: "октября", 11: "ноября", 12: "декабря"
}


def to_short_fio(fio_str: str) -> str:
    """e.g. 'Базаров Николай Николаевич' -> 'Базаров Н. Н.'"""
    parts = fio_str.strip().split()
    if len(parts) >= 3:
        return f"{parts[0]} {parts[1][0]}. {parts[2][0]}."
    elif len(parts) == 2:
        return f"{parts[0]} {parts[1][0]}."
    return fio_str


def to_manager_short_fio(fio_str: str) -> str:
    """e.g. 'Гусарова Ксения Андреевна' -> 'К. А. Гусарова'"""
    parts = fio_str.strip().split()
    if len(parts) >= 3:
        # Check if already initials
        if len(parts[0]) == 1 or parts[0].endswith("."):
            return fio_str
        return f"{parts[1][0]}. {parts[2][0]}. {parts[0]}"
    elif len(parts) == 2:
        return f"{parts[1][0]}. {parts[0]}"
    return fio_str


def calc_3_years_ago(date_str: str) -> str:
    """
    Given DD.MM.YYYY, returns DD.MM.(YYYY-3).
    If invalid or empty, uses current date - 3 years.
    """
    if date_str:
        m = re.search(r'(\d{1,2})\.(\d{1,2})\.(\d{4})', date_str)
        if m:
            d, mth, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
            try:
                dt = datetime(y - 3, mth, d)
                return dt.strftime("%d.%m.%Y")
            except ValueError:
                return f"{d:02d}.{mth:02d}.{y-3}"
    now = datetime.now()
    try:
        dt = datetime(now.year - 3, now.month, now.day)
        return dt.strftime("%d.%m.%Y")
    except ValueError:
        return f"{now.day:02d}.{now.month:02d}.{now.year-3}"


def format_russian_date_words(date_str: str = "") -> str:
    """Returns '«07» мая 2026 г.' based on date_str or current date."""
    now = datetime.now()
    d, m, y = now.day, now.month, now.year
    if date_str:
        match = re.search(r'(\d{1,2})\.(\d{1,2})\.(\d{4})', date_str)
        if match:
            d, m, y = int(match.group(1)), int(match.group(2)), int(match.group(3))
    mon = MONTHS_RU.get(m, "")
    return f"«{d:02d}» {mon} {y} г."


def delete_paragraph(paragraph):
    p_elem = paragraph._p
    p_elem.getparent().remove(p_elem)


def replace_tokens_in_paragraph(p, bold_map: Dict[str, str], font_name: str = "Times New Roman"):
    """
    Replaces {{TAG}} tokens in paragraph text.
    Inserted fields are rendered in BOLD (bold=True), pure black RGB(0, 0, 0),
    while boilerplate text is rendered regular (bold=False).
    """
    text = p.text
    if "{{" not in text:
        return

    # Check if the entire paragraph was previously bold
    all_was_bold = all(r.bold for r in p.runs) if p.runs else False

    pattern = re.compile(r'(\{\{[A-Z0-9_]+\}\})')
    tokens = pattern.split(text)

    p.text = ""
    for token in tokens:
        if not token:
            continue
        if token in bold_map:
            val = bold_map[token]
            if val:
                run = p.add_run(val)
                run.bold = True
                run.font.name = font_name
                run.font.color.rgb = RGBColor(0, 0, 0)
        else:
            run = p.add_run(token)
            run.bold = all_was_bold
            run.font.name = font_name
            run.font.color.rgb = RGBColor(0, 0, 0)


def replace_tokens_in_cell(cell, bold_map: Dict[str, str], font_name: str = "Times New Roman"):
    for p in cell.paragraphs:
        replace_tokens_in_paragraph(p, bold_map, font_name)


def generate_single_inquiry(
    template_path: str,
    output_path: str,
    data: Dict[str, Any]
):
    doc = docx.Document(template_path)

    court_name = data.get("court_name", "").strip() or "Арбитражный суд"
    if court_name.startswith("Арбитражный суд"):
        court_dec_str = "Арбитражного суда" + court_name[15:]
    else:
        court_dec_str = court_name

    case_no = data.get("case_number", "").strip()
    decision_date = data.get("decision_date", "").strip()
    three_years_ago_date = calc_3_years_ago(decision_date)
    inquiry_date_str = format_russian_date_words(decision_date)

    # Debtor
    debtor_fio = data.get("debtor_fio", "").strip()
    debtor_fio_gen = data.get("debtor_fio_gen", "").strip() or debtor_fio
    debtor_fio_instr = data.get("debtor_fio_instr", "").strip() or debtor_fio
    debtor_short_fio = to_short_fio(debtor_fio)
    debtor_birth = data.get("debtor_birth_date", "").strip()
    debtor_place = data.get("debtor_birth_place", "").strip()
    debtor_snils = data.get("debtor_snils", "").strip()
    debtor_inn = data.get("debtor_inn", "").strip()
    debtor_address = data.get("debtor_address", "").strip()

    pass_series = data.get("debtor_passport_series", "").strip()
    pass_num = data.get("debtor_passport_number", "").strip()
    pass_by = data.get("debtor_passport_issued_by", "").strip()
    pass_date = data.get("debtor_passport_date", "").strip()
    pass_code = data.get("debtor_passport_code", "").strip()

    # Manager (fixed Gusarova Ksenia Andreevna)
    manager_fio = data.get("manager_fio", "").strip() or "Гусарова Ксения Андреевна"
    manager_short_fio = to_manager_short_fio(manager_fio)
    manager_inn = data.get("manager_inn", "").strip() or "380470431942"
    manager_snils = data.get("manager_snils", "").strip() or "136-556-599 95"
    manager_corr_address = data.get("manager_corr_address", "").strip() or "630007, г. Новосибирск, а/я 1"
    manager_phone = data.get("manager_phone", "").strip() or "+7 (913) 989-01-63"
    manager_email = data.get("manager_email", "").strip() or "kseniya_gusarova@mail.ru"

    # Spouse
    spouse_status = data.get("spouse_status", "not_married")  # 'married', 'divorced', 'not_married'
    spouse_fio = data.get("spouse_fio", "").strip()
    spouse_fio_gen = data.get("spouse_fio_gen", "").strip() or spouse_fio
    spouse_fio_instr = data.get("spouse_fio_instr", "").strip() or spouse_fio
    spouse_birth = data.get("spouse_birth_date", "").strip()
    spouse_place = data.get("spouse_birth_place", "").strip()
    spouse_address = data.get("spouse_address", "").strip() or debtor_address
    spouse_snils = data.get("spouse_snils", "").strip()
    spouse_inn = data.get("spouse_inn", "").strip()
    marriage_date = data.get("marriage_date", "").strip()

    spouse_pass_s = data.get("spouse_passport_series", "").strip()
    spouse_pass_n = data.get("spouse_passport_number", "").strip()
    spouse_pass_b = data.get("spouse_passport_issued_by", "").strip()
    spouse_pass_d = data.get("spouse_passport_date", "").strip()
    spouse_pass_c = data.get("spouse_passport_code", "").strip()

    has_spouse = (spouse_status in ("married", "divorced")) and bool(spouse_fio)

    base_name = os.path.basename(template_path)

    # 1. Template-specific structural adjustments
    # A) Должнику_супругу_РИ.docx
    if "Должнику_супругу" in base_name and len(doc.tables) > 0:
        table0 = doc.tables[0]
        if len(table0.rows) > 1 and len(table0.rows[1].cells) > 1:
            c = table0.rows[1].cells[1]
            if has_spouse:
                c.text = f"{debtor_fio}\n{debtor_address}\n{spouse_fio}\n{spouse_address}"
            else:
                c.text = f"{debtor_fio}\n{debtor_address}"
            for cp in c.paragraphs:
                for cr in cp.runs:
                    cr.font.name = "Times New Roman"

    # B) в_ЕГРН_(сокращенный)_должник_супруг_РИ.docx
    if "ЕГРН" in base_name and not has_spouse:
        # Tables 3, 4, 5 are for spouse - remove them if single
        while len(doc.tables) > 3:
            t = doc.tables[3]
            t_elem = t._tbl
            t_elem.getparent().remove(t_elem)
        # Remove subsequent paragraphs 3+
        while len(doc.paragraphs) > 3:
            delete_paragraph(doc.paragraphs[3])

    # C) в_ССП_РИ.docx
    if "в_ССП" in base_name:
        for p in doc.paragraphs:
            if "переданных " in p.text and "для исполнения" in p.text:
                debtor_instr = debtor_fio_instr or debtor_fio
                p.text = re.sub(r'переданных [^для]+? для исполнения', f'переданных {debtor_instr} для исполнения', p.text)
            if "в отношении " in p.text and "и направить" in p.text:
                p.text = re.sub(r'в отношении [^и]+?, и направить', f'в отношении {debtor_fio_gen}, и направить', p.text)

    # D) запрос в УВМ.docx
    if "в УВМ" in base_name:
        for p in doc.paragraphs:
            if "являются кредиторами" in p.text:
                p.text = re.sub(r'являются кредиторами [^\.]*?\.', f'являются кредиторами {debtor_fio_gen}.', p.text)
                p.text = re.sub(r'в отношении [^\.]*?$', f'в отношении {debtor_short_fio}', p.text)

    # 2. Spouse logic & Paragraph filtering
    if has_spouse:
        if spouse_status == "divorced":
            for p in doc.paragraphs:
                if "состоит в браке с" in p.text:
                    p.text = p.text.replace("состоит в браке с", "состоял в браке с")
                    p.text = p.text.replace("супруг должника", "бывший супруг должника")
                    p.text = p.text.replace("Брак зарегистрирован", "Брак расторгнут")
                if "Копия свидетельства о заключении брака" in p.text:
                    p.text = p.text.replace("Копия свидетельства о заключении брака", "Копия свидетельства о расторжении брака")
    else:
        # Debtor is single: remove paragraphs purely dedicated to spouse
        to_delete = []
        delete_subsequent_bullets = False
        for p in doc.paragraphs:
            txt = p.text.strip()
            if txt.startswith("В рамках дела о банкротстве установлено, что должник состо"):
                to_delete.append(p)
            elif txt.startswith("В соответствии с п. 1 ст. 34 Семейного кодекса"):
                to_delete.append(p)
            elif txt.startswith("Копия свидетельства о заключении брака") or txt.startswith("Копия свидетельства о расторжении брака"):
                to_delete.append(p)
            elif txt.startswith(("- в отношении супруга", "– в отношении супруга")):
                to_delete.append(p)
                delete_subsequent_bullets = True
            elif delete_subsequent_bullets:
                if txt.startswith(("•", "о ", "сведения об ", "Приложении")) and not txt.startswith(("В целях", "Обращаю", "При отсутствии", "Ч.", "Согласно", "Напоминаю", "Документы")):
                    to_delete.append(p)
                else:
                    delete_subsequent_bullets = False
            elif "маломерных судах, зарегистрированных за супругом" in txt:
                to_delete.append(p)
            elif "находящееся в совместной собственности должника и его супруга" in txt:
                to_delete.append(p)
            elif "заключенных с супругой должника" in txt:
                p.text = p.text.replace(", а также о договорах аренды имущества, заключенных с супругой должника", "")

        for p in to_delete:
            try:
                delete_paragraph(p)
            except Exception:
                pass

    # 3. Handle Debtor Passport omission if passport fields empty
    if not (pass_series and pass_num):
        pass_pattern = re.compile(r',\s*паспорт\s*\{\{DEBTOR_PASS_SERIES\}\}\s*\{\{DEBTOR_PASS_NUMBER\}\}[^)]*?\)')
        for p in doc.paragraphs:
            if "{{DEBTOR_PASS_SERIES}}" in p.text:
                p.text = pass_pattern.sub(")", p.text)

    # 4. Comprehensive Bold Replacement Map
    bold_map = {
        "{{CASE_NUMBER}}": case_no,
        "{{COURT_NAME_GEN}}": court_dec_str,
        "{{DECISION_DATE}}": decision_date,
        "{{DEBTOR_FIO}}": debtor_fio,
        "{{DEBTOR_FIO_GEN}}": debtor_fio_gen,
        "{{DEBTOR_FIO_INSTR}}": debtor_fio_instr,
        "{{DEBTOR_SHORT_FIO}}": debtor_short_fio,
        "{{DEBTOR_BIRTH_DATE}}": debtor_birth,
        "{{DEBTOR_BIRTH_PLACE}}": debtor_place,
        "{{DEBTOR_SNILS}}": debtor_snils,
        "{{DEBTOR_INN}}": debtor_inn,
        "{{DEBTOR_ADDRESS}}": debtor_address,
        "{{DEBTOR_PASS_SERIES}}": pass_series,
        "{{DEBTOR_PASS_NUMBER}}": pass_num,
        "{{DEBTOR_PASS_ISSUED_BY}}": pass_by,
        "{{DEBTOR_PASS_DATE}}": pass_date,
        "{{DEBTOR_PASS_CODE}}": pass_code,
        "{{MANAGER_FIO}}": manager_fio,
        "{{MANAGER_SHORT_FIO}}": manager_short_fio,
        "{{MANAGER_INN}}": manager_inn,
        "{{MANAGER_SNILS}}": manager_snils,
        "{{THREE_YEARS_AGO_DATE}}": three_years_ago_date,
        "{{INQUIRY_DATE_STR}}": inquiry_date_str,
        "{{MARRIAGE_DATE}}": marriage_date,
        "{{SPOUSE_FIO}}": spouse_fio,
        "{{SPOUSE_FIO_GEN}}": spouse_fio_gen,
        "{{SPOUSE_FIO_INSTR}}": spouse_fio_instr,
        "{{SPOUSE_BIRTH_DATE}}": spouse_birth,
        "{{SPOUSE_BIRTH_PLACE}}": spouse_place,
        "{{SPOUSE_ADDRESS}}": spouse_address,
        "{{SPOUSE_SNILS}}": spouse_snils,
        "{{SPOUSE_INN}}": spouse_inn,
        "{{SPOUSE_PASS_SERIES}}": spouse_pass_s,
        "{{SPOUSE_PASS_NUMBER}}": spouse_pass_n,
        "{{SPOUSE_PASS_ISSUED_BY}}": spouse_pass_b,
        "{{SPOUSE_PASS_DATE}}": spouse_pass_d,
        "{{SPOUSE_PASS_CODE}}": spouse_pass_c,
    }

    # 5. Process all Document Paragraphs
    for p in doc.paragraphs:
        replace_tokens_in_paragraph(p, bold_map)

    # 6. Process all Tables and Cells
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                replace_tokens_in_cell(cell, bold_map)

    # 7. Final safety clean: remove any accidental remaining {{...}} tags
    for p in doc.paragraphs:
        if "{{" in p.text:
            p.text = re.sub(r'\{\{[A-Z0-9_]+\}\}', '', p.text)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                if "{{" in cell.text:
                    for cp in cell.paragraphs:
                        if "{{" in cp.text:
                            cp.text = re.sub(r'\{\{[A-Z0-9_]+\}\}', '', cp.text)

    out_dir = os.path.dirname(output_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    doc.save(output_path)


def generate_inquiries(
    data: Dict[str, Any],
    selected_template_ids: List[str],
    output_base_dir: str,
    templates_dir: str,
    progress_callback: Optional[Callable[[int, str], None]] = None
) -> Dict[str, Any]:
    """
    Generates customized inquiry documents for all selected templates.
    """
    debtor_fio = data.get("debtor_fio", "Должник").strip()
    safe_name = re.sub(r'[^\w\s\-]', '', debtor_fio).replace(' ', '_')
    folder_name = f"Запросы_{safe_name}"
    target_dir = os.path.join(output_base_dir, folder_name)
    os.makedirs(target_dir, exist_ok=True)

    selected_configs = [t for t in TEMPLATES_CONFIG if t["id"] in selected_template_ids]
    total = len(selected_configs)
    generated_files = []

    for i, cfg in enumerate(selected_configs):
        if progress_callback:
            percent = int((i / total) * 100)
            progress_callback(percent, f"Формирование: {cfg['name']}...")

        tmpl_file = cfg["file"]
        tmpl_path = os.path.join(templates_dir, tmpl_file)
        if not os.path.exists(tmpl_path):
            continue

        out_name = f"{safe_name}_{tmpl_file}"
        out_path = os.path.join(target_dir, out_name)

        generate_single_inquiry(tmpl_path, out_path, data)
        generated_files.append(out_path)

    if progress_callback:
        progress_callback(100, "Формирование запросов завершено!")

    return {
        "output_dir": target_dir,
        "files_count": len(generated_files),
        "files": generated_files
    }
