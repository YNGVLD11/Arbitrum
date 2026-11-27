import os
import re
import json
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
import docx
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

TEMPLATES_CONFIG = [
    {"id": "banks", "name": "Банки", "file": "_Запрос в банки.docx"},
    {"id": "creditors_notify", "name": "Уведомление кредиторам", "file": "Уведомление_кредиторам_РИ.docx"},
    {"id": "employer", "name": "Работодателю", "file": "Запрос_работодателю_РИ.docx"},
    {"id": "administration", "name": "Администрация", "file": "в_Администрацию_должник_супруг_РИ.docx"},
    {"id": "bti", "name": "БТИ", "file": "в_БТИ_РИ.docx"},
    {"id": "gibdd", "name": "ГИБДД", "file": "в_ГИБДД_должник_РИ.docx"},
    {"id": "gims", "name": "ГИМС", "file": "в_ГИМС_должник_супруг_РИ.docx"},
    {"id": "gostekhnadzor", "name": "Гостехнадзор", "file": "в_Гостехнадзор_должник_супруг_РИ.docx"},
    {"id": "egrn", "name": "ЕГРН", "file": "в_ЕГРН_(сокращенный)_должник_супруг_РИ.docx"},
    {"id": "zags", "name": "ЗАГС", "file": "в_ЗАГС_РИ.docx"},
    {"id": "ifns", "name": "ИФНС", "file": "в_ИФНС_должник_супруг_РИ.docx"},
    {"id": "rosaviation", "name": "Росавиация", "file": "в_Росавиацию_должник_супруг_РИ.docx"},
    {"id": "rosgvardiya", "name": "Росгвардия", "file": "в_Росгвардию_должник_супруг_РИ.docx"},
    {"id": "rosimushchestvo", "name": "Росимущество", "file": "в_Росимущество_РИ.docx"},
    {"id": "rospatent", "name": "Роспатент", "file": "в_Роспатент_должник_супруг_РИ.docx"},
    {"id": "rosreestr", "name": "Росреестр", "file": "в_Росреестр_должник_супруг_РИ.docx"},
    {"id": "fssp", "name": "ФССП", "file": "в_ССП_РИ.docx"},
    {"id": "sfr", "name": "СФР", "file": "в_СФР_РИ.docx"},
    {"id": "debtor_spouse", "name": "Должнику / Супругу", "file": "Должнику_супругу_РИ.docx"},
    {"id": "uvm", "name": "УВМ", "file": "запрос в УВМ.docx"},
    {"id": "dzio", "name": "ДЗИО", "file": "в_ДЗИО_РИ.docx"},
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
    """e.g. 'Гусарова Ксения Андреевна' or 'Гусарова К.А.' -> 'К. А. Гусарова'"""
    s = fio_str.strip()
    if not s:
        return ""
    m = re.match(r'^([А-ЯЁа-яё]+)\s+([А-ЯЁа-яё])\.?\s*([А-ЯЁа-яё])\.?$', s)
    if m:
        return f"{m.group(2).upper()}. {m.group(3).upper()}. {m.group(1).capitalize()}"
    m = re.match(r'^([А-ЯЁа-яё])\.?\s*([А-ЯЁа-яё])\.?\s+([А-ЯЁа-яё]+)$', s)
    if m:
        return f"{m.group(1).upper()}. {m.group(2).upper()}. {m.group(3).capitalize()}"
    parts = s.split()
    if len(parts) >= 3:
        if len(parts[0]) == 1 or parts[0].endswith("."):
            return s
        return f"{parts[1][0].upper()}. {parts[2][0].upper()}. {parts[0].capitalize()}"
    elif len(parts) == 2:
        return f"{parts[1][0].upper()}. {parts[0].capitalize()}"
    return s


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


def replace_tokens_in_paragraph(p, tag_map: Dict[str, str], font_name: str = "Times New Roman"):
    """
    Replaces {{TAG}} tokens in paragraph text without adding bold (bold=False),
    pure black RGB(0, 0, 0), matching original non-bold style requirements.
    """
    text = p.text
    if "{{" not in text:
        return

    pattern = re.compile(r'(\{\{[A-Z0-9_]+\}\})')
    tokens = pattern.split(text)

    p.text = ""
    for token in tokens:
        if not token:
            continue
        if token in tag_map:
            val = tag_map[token]
            if val:
                run = p.add_run(val)
                run.bold = False
                run.font.name = font_name
                run.font.color.rgb = RGBColor(0, 0, 0)
        else:
            run = p.add_run(token)
            run.bold = False
            run.font.name = font_name
            run.font.color.rgb = RGBColor(0, 0, 0)


def replace_tokens_in_cell(cell, tag_map: Dict[str, str], font_name: str = "Times New Roman"):
    for p in cell.paragraphs:
        replace_tokens_in_paragraph(p, tag_map, font_name)


_REGIONS_CACHE = None

def get_regions_dict() -> dict:
    """Loads and caches the regions database from assets/regions.json."""
    global _REGIONS_CACHE
    if _REGIONS_CACHE is not None:
        return _REGIONS_CACHE

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    json_path = os.path.join(base_dir, "assets", "regions.json")
    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                _REGIONS_CACHE = json.load(f)
                return _REGIONS_CACHE
        except Exception:
            pass
    _REGIONS_CACHE = {}
    return _REGIONS_CACHE


def detect_region_info(address: str, court_name: str) -> dict:
    """
    Detects regional agency names based on debtor address and court name
    using assets/regions.json.
    """
    regions = get_regions_dict()
    txt = f"{address} {court_name}".lower()

    # Search for matching region by keywords
    for reg_id, reg_data in regions.items():
        keywords = reg_data.get("keywords", [])
        for kw in keywords:
            if kw.lower() in txt:
                agencies = reg_data.get("agencies", {})
                res = {
                    "name": reg_data.get("name", ""),
                    "region_adj": reg_data.get("region_adj", ""),
                }
                res.update(agencies)
                return res

    # Fallback to Novosibirsk if available, or first region
    if "novosibirsk" in regions:
        nov_data = regions["novosibirsk"]
        res = {
            "name": nov_data.get("name", ""),
            "region_adj": nov_data.get("region_adj", ""),
        }
        res.update(nov_data.get("agencies", {}))
        return res

    return {}


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
    petition_date = data.get("petition_date", "").strip()

    # Three years ago calculated from petition_date if provided, else decision_date
    ref_date_for_3_years = petition_date or decision_date
    three_years_ago_date = calc_3_years_ago(ref_date_for_3_years)

    # Employer inquiry 2-NDFL date requirement: exactly 01.01.{ref_year - 3}
    employer_year = datetime.now().year
    if ref_date_for_3_years:
        match_y = re.search(r'(\d{4})', ref_date_for_3_years)
        if match_y:
            employer_year = int(match_y.group(1))
    employer_three_years_ago_date = f"01.01.{employer_year - 3}"

    # Header date in outgoing inquiry ("Исх. № ... от ..."): always current system date
    inquiry_date_str = format_russian_date_words("")

    # Debtor
    debtor_fio = data.get("debtor_fio", "").strip()
    debtor_fio_gen = data.get("debtor_fio_gen", "").strip()
    if not debtor_fio_gen and debtor_fio:
        try:
            from core.court_parser import inflect_fio
            debtor_fio_gen = inflect_fio(debtor_fio, 'gent')
        except Exception:
            debtor_fio_gen = debtor_fio

    debtor_fio_instr = data.get("debtor_fio_instr", "").strip()
    if not debtor_fio_instr and debtor_fio:
        try:
            from core.court_parser import inflect_fio
            debtor_fio_instr = inflect_fio(debtor_fio, 'ablt')
        except Exception:
            debtor_fio_instr = debtor_fio
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
    manager_short_fio = to_manager_short_fio(manager_fio) or "К. А. Гусарова"
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

    # Employer Info
    employer_name = data.get("employer_name", "").strip()
    employer_addr = data.get("employer_address", "").strip()
    employer_inn = data.get("employer_inn", "").strip()
    employer_lines = []
    if employer_name:
        employer_lines.append(employer_name)
    if employer_addr:
        employer_lines.append(f"Адрес: {employer_addr}")
    if employer_inn:
        employer_lines.append(f"ИНН: {employer_inn}")
    employer_info_str = "\n".join(employer_lines) if employer_lines else "Работодателю"

    # Creditors Info
    creditors_list = data.get("creditors", [])
    creditors_blocks = []
    for c in creditors_list:
        c_name = c.get("name", "").strip()
        c_addr = c.get("address", "").strip()
        c_inn = c.get("inn", "").strip()
        if not c_name and not c_addr:
            continue
        blk = []
        if c_name:
            blk.append(c_name)
        if c_addr:
            blk.append(f"Адрес: {c_addr}")
        if c_inn:
            blk.append(f"ИНН: {c_inn}")
        creditors_blocks.append("\n".join(blk))

    creditors_info_str = "\n\n".join(creditors_blocks) if creditors_blocks else "Кредиторам"

    base_name = os.path.basename(template_path)
    region_info = detect_region_info(debtor_address, court_name)

    # 1. Template-specific structural adjustments
    # Dynamic agency recipient replacement based on debtor's region
    agency_key_map = {
        "Администрацию": "admin",
        "БТИ": "bti",
        "ГИБДД": "gibdd",
        "ГИМС": "gims",
        "Гостехнадзор": "gostekhnadzor",
        "ЗАГС": "zags",
        "ИФНС": "ifns",
        "Росгвардию": "rosgvardiya",
        "Росимущество": "rosimushchestvo",
        "Росреестр": "rosreestr",
        "ССП": "fssp",
        "СФР": "sfr",
        "УВМ": "uvm",
    }

    for keyword, reg_key in agency_key_map.items():
        if keyword in base_name and len(doc.tables) > 0:
            t0 = doc.tables[0]
            if len(t0.rows) > 1 and len(t0.rows[1].cells) > 1:
                t0.rows[1].cells[1].text = region_info.get(reg_key, "")

    # A) Должнику_супругу_РИ.docx
    if "Должнику_супругу" in base_name and len(doc.tables) > 0:
        table0 = doc.tables[0]
        if len(table0.rows) > 1 and len(table0.rows[1].cells) > 1:
            c = table0.rows[1].cells[1]
            if has_spouse:
                c.text = f"{debtor_fio}\n{debtor_address}\n{spouse_fio}\n{spouse_address}"
            else:
                c.text = f"{debtor_fio}\n{debtor_address}"

    # B) в_ЕГРН_(сокращенный)_должник_супруг_РИ.docx
    if "ЕГРН" in base_name and not has_spouse:
        while len(doc.tables) > 3:
            t = doc.tables[3]
            t_elem = t._tbl
            t_elem.getparent().remove(t_elem)
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

    # 4. Replacement Map (regular text, no bold)
    tag_map = {
        "{{CASE_NUMBER}}": case_no,
        "{{COURT_NAME}}": court_name,
        "{{COURT_NAME_GEN}}": court_dec_str,
        "{{DECISION_DATE}}": decision_date,
        "{{PETITION_DATE}}": petition_date,
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
        "{{THREE_YEARS_AGO_DATE}}": employer_three_years_ago_date if "работодател" in base_name.lower() else three_years_ago_date,
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
        "{{EMPLOYER_INFO}}": employer_info_str,
        "{{CREDITORS_INFO}}": creditors_info_str,
        "{{DZIO_NAME_AND_ADDRESS}}": region_info.get("dzio", "Департамент имущества и земельных отношений Новосибирской области\n630007, Новосибирская область, г. Новосибирск, Красный пр-кт, д. 18"),
    }

    # 5. Process all Document Paragraphs
    for p in doc.paragraphs:
        replace_tokens_in_paragraph(p, tag_map)

    # 5.5 Replace Manager Contact details if customized
    default_addr = "630007, г. Новосибирск, а/я 1"
    default_phone = "+7 (913) 989-01-63"
    default_email = "kseniya_gusarova@mail.ru"

    for p in doc.paragraphs:
        if manager_corr_address and manager_corr_address != default_addr and default_addr in p.text:
            p.text = p.text.replace(default_addr, manager_corr_address)
        if manager_phone and manager_phone != default_phone and default_phone in p.text:
            p.text = p.text.replace(default_phone, manager_phone)
        if manager_email and manager_email != default_email and default_email in p.text:
            p.text = p.text.replace(default_email, manager_email)

    # 6. Process all Tables and Cells
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                replace_tokens_in_cell(cell, tag_map)
                for cp in cell.paragraphs:
                    if manager_corr_address and manager_corr_address != default_addr and default_addr in cp.text:
                        cp.text = cp.text.replace(default_addr, manager_corr_address)
                    if manager_phone and manager_phone != default_phone and default_phone in cp.text:
                        cp.text = cp.text.replace(default_phone, manager_phone)
                    if manager_email and manager_email != default_email and default_email in cp.text:
                        cp.text = cp.text.replace(default_email, manager_email)

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

    # 8. Ensure font sizes: P0 is 8pt, rest is 10pt
    if 'Normal' in doc.styles:
        doc.styles['Normal'].font.size = Pt(10)
        doc.styles['Normal'].font.name = 'Times New Roman'

    for i, p in enumerate(doc.paragraphs):
        if i == 0 and "финансовый управляющий" in p.text.lower():
            for r in p.runs:
                r.font.size = Pt(8)
                r.font.name = 'Times New Roman'
        else:
            for r in p.runs:
                if r.font.size and r.font.size.pt > 10.0:
                    r.font.size = Pt(10)

    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for cp in cell.paragraphs:
                    for cr in cp.runs:
                        if cr.font.size and cr.font.size.pt > 10.0:
                            cr.font.size = Pt(10)

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
