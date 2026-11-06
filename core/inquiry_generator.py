import os
import re
from typing import Dict, Any, List, Optional, Callable
import docx
from docx.shared import Pt
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

def to_short_fio(fio_str: str) -> str:
    parts = fio_str.strip().split()
    if len(parts) == 3:
        return f"{parts[0]} {parts[1][0]}. {parts[2][0]}."
    return fio_str

def set_paragraph_formatted(p, segments: List[tuple], font_name="Times New Roman", font_size_pt=10, align=WD_ALIGN_PARAGRAPH.JUSTIFY):
    p.text = ""
    p.alignment = align
    for text_val, is_bold in segments:
        if not text_val:
            continue
        run = p.add_run(text_val)
        run.font.name = font_name
        run.font.size = Pt(font_size_pt)
        run.font.bold = is_bold

def replace_in_cell(cell, replacements: Dict[str, str]):
    for p in cell.paragraphs:
        full_text = p.text
        modified = False
        for k, v in replacements.items():
            if k in full_text:
                full_text = full_text.replace(k, v)
                modified = True
        if modified:
            p.text = full_text
            for run in p.runs:
                run.font.name = "Times New Roman"

def delete_paragraph(paragraph):
    p_elem = paragraph._p
    p_elem.getparent().remove(p_elem)

def generate_single_inquiry(
    template_path: str,
    output_path: str,
    data: Dict[str, Any]
):
    doc = docx.Document(template_path)

    court_name = data.get("court_name", "").strip() or "Арбитражного суда"
    # Ensure genitive form of court if needed: "Решением Арбитражного суда Новосибирской области"
    if court_name.startswith("Арбитражный суд"):
        court_dec_str = "Арбитражного суда" + court_name[15:]
    else:
        court_dec_str = court_name

    case_no = data.get("case_number", "").strip()
    decision_date = data.get("decision_date", "").strip()
    debtor_fio = data.get("debtor_fio", "").strip()
    debtor_fio_gen = data.get("debtor_fio_gen", "").strip() or debtor_fio
    debtor_birth = data.get("debtor_birth_date", "").strip()
    debtor_place = data.get("debtor_birth_place", "").strip()
    debtor_snils = data.get("debtor_snils", "").strip()
    debtor_inn = data.get("debtor_inn", "").strip()
    debtor_address = data.get("debtor_address", "").strip()

    # Debtor passport block
    pass_series = data.get("debtor_passport_series", "").strip()
    pass_num = data.get("debtor_passport_number", "").strip()
    pass_by = data.get("debtor_passport_issued_by", "").strip()
    pass_date = data.get("debtor_passport_date", "").strip()
    pass_code = data.get("debtor_passport_code", "").strip()

    if pass_series and pass_num:
        pass_block = f", паспорт {pass_series} {pass_num}"
        if pass_by:
            pass_block += f", выдан {pass_by}"
        if pass_date:
            pass_block += f" {pass_date}"
        if pass_code:
            pass_block += f", код подразделения {pass_code}"
    else:
        pass_block = ""

    # Manager
    manager_fio = data.get("manager_fio", "Гусарова Ксения Андреевна").strip()
    manager_inn = data.get("manager_inn", "380470431942").strip()
    manager_snils = data.get("manager_snils", "136-556-599 95").strip()
    manager_sro = data.get("manager_sro", 'САМРО "Ассоциация антикризисных управляющих"').strip()
    manager_sro_ogrn = data.get("manager_sro_ogrn", "1026300003751").strip()
    manager_sro_inn = data.get("manager_sro_inn", "6315944042").strip()
    manager_sro_address = data.get("manager_sro_address", "443072, г. Самара, Московское шоссе, 18-й км").strip()
    manager_corr_address = data.get("manager_corr_address", "630007, г. Новосибирск, а/я 1").strip()
    manager_phone = data.get("manager_phone", "+7 (913) 989-01-63").strip()
    manager_email = data.get("manager_email", "kseniya_gusarova@mail.ru").strip()

    # Spouse
    spouse_status = data.get("spouse_status", "not_married")  # 'married', 'divorced', 'not_married'
    spouse_fio = data.get("spouse_fio", "").strip()
    spouse_fio_instr = data.get("spouse_fio_instr", "").strip() or spouse_fio
    spouse_birth = data.get("spouse_birth_date", "").strip()
    spouse_place = data.get("spouse_birth_place", "").strip()
    spouse_address = data.get("spouse_address", "").strip() or debtor_address
    spouse_snils = data.get("spouse_snils", "").strip()
    spouse_inn = data.get("spouse_inn", "").strip()
    marriage_date = data.get("marriage_date", "").strip()

    has_spouse = (spouse_status in ("married", "divorced")) and bool(spouse_fio)

    # 1. Header (P0, P2)
    if len(doc.paragraphs) > 0:
        p0 = doc.paragraphs[0]
        if "финансовый управляющий" in p0.text.lower():
            set_paragraph_formatted(p0, [
                (f"Финансовый управляющий {debtor_fio_gen} {manager_fio} ", False)
            ], font_size_pt=8, align=WD_ALIGN_PARAGRAPH.LEFT)

    if len(doc.paragraphs) > 2:
        p2 = doc.paragraphs[2]
        if "контактный телефон" in p2.text.lower():
            set_paragraph_formatted(p2, [
                (f"{manager_corr_address}. Контактный телефон: {manager_phone}, эл.почта: {manager_email}", False)
            ], font_size_pt=8, align=WD_ALIGN_PARAGRAPH.LEFT)

    # 2. Decision Paragraph & Manager Paragraph
    idx_decision = -1
    idx_manager = -1
    idx_spouse = -1

    for idx, p in enumerate(doc.paragraphs):
        txt = p.text.strip()
        if txt.startswith("Решением") and "признан несостоятельным" in txt:
            idx_decision = idx
        elif txt.startswith("Финансовым управляющим утвержден"):
            idx_manager = idx
        elif "в рамках дела о банкротстве установлено, что должник состо" in txt.lower():
            idx_spouse = idx

    # Format Decision Paragraph
    if idx_decision != -1:
        p_dec = doc.paragraphs[idx_decision]
        set_paragraph_formatted(p_dec, [
            (f"Решением {court_dec_str} от {decision_date} г. по делу № ", False),
            (f"{case_no} ", True),
            (f"{debtor_fio} ", True),
            (f"(дата рождения: {debtor_birth}, место рождения: {debtor_place}, СНИЛС {debtor_snils}, ИНН {debtor_inn}, регистрация по месту жительства: {debtor_address}{pass_block}) (далее по тексту – должник) признан несостоятельным (банкротом) и введена процедура реализации имущества гражданина.", False)
        ], font_size_pt=10, align=WD_ALIGN_PARAGRAPH.JUSTIFY)

    # Format Manager Paragraph
    if idx_manager != -1:
        p_mgr = doc.paragraphs[idx_manager]
        set_paragraph_formatted(p_mgr, [
            ("Финансовым управляющим утверждена ", False),
            (f"{manager_fio} ", True),
            (f"(ИНН {manager_inn}, СНИЛС {manager_snils}) - член {manager_sro} (ОГРН {manager_sro_ogrn}, ИНН {manager_sro_inn}, адрес: {manager_sro_address}).", False)
        ], font_size_pt=10, align=WD_ALIGN_PARAGRAPH.JUSTIFY)

    # Format Spouse Paragraph
    if has_spouse:
        status_word = "состоит в браке" if spouse_status == "married" else "состоял в браке"
        status_label = "супруг должника" if spouse_status == "married" else "бывший супруг должника"
        action_word = "Брак зарегистрирован" if spouse_status == "married" else "Брак расторгнут"
        date_suffix = f" {action_word} {marriage_date} г." if marriage_date else ""

        spouse_segments = [
            (f"В рамках дела о банкротстве установлено, что должник {status_word} с ", False),
            (f"{spouse_fio_instr} ", True),
            (f"(дата рождения: {spouse_birth}, место рождения: {spouse_place}, СНИЛС: {spouse_snils} ИНН: {spouse_inn}, регистрация по месту жительства: {spouse_address}) (далее по тексту – {status_label}).{date_suffix}", False)
        ]

        if idx_spouse != -1:
            # Replace existing spouse paragraph
            p_sp = doc.paragraphs[idx_spouse]
            set_paragraph_formatted(p_sp, spouse_segments, font_size_pt=10, align=WD_ALIGN_PARAGRAPH.JUSTIFY)
        else:
            # Insert new paragraph right after manager paragraph
            if idx_manager != -1 and idx_manager + 1 < len(doc.paragraphs):
                p_sp = doc.paragraphs[idx_manager + 1].insert_paragraph_before()
            else:
                p_sp = doc.add_paragraph()
            set_paragraph_formatted(p_sp, spouse_segments, font_size_pt=10, align=WD_ALIGN_PARAGRAPH.JUSTIFY)
    else:
        # Not married: if spouse paragraph existed, remove it
        if idx_spouse != -1:
            delete_paragraph(doc.paragraphs[idx_spouse])

    # 3. Handle Bullet points in requests ("- в отношении должника", "- в отношении супруга должника")
    to_delete = []
    for p in doc.paragraphs:
        txt = p.text.strip()
        if txt.startswith(("- в отношении должника", "– в отношении должника")):
            set_paragraph_formatted(p, [
                ("- в отношении должника: ", True),
                (f"{debtor_fio} ", True),
                (f"(дата рождения: {debtor_birth}, место рождения: {debtor_place}, СНИЛС: {debtor_snils}, ИНН: {debtor_inn}, регистрация по месту жительства: {debtor_address}):", False)
            ], font_size_pt=10, align=WD_ALIGN_PARAGRAPH.JUSTIFY)
        elif txt.startswith(("- в отношении супруга", "– в отношении супруга")):
            if has_spouse:
                set_paragraph_formatted(p, [
                    ("- в отношении супруга должника: ", True),
                    (f"{spouse_fio} ", True),
                    (f"(дата рождения: {spouse_birth}, место рождения: {spouse_place}, СНИЛС: {spouse_snils}, ИНН: {spouse_inn}, регистрация по месту жительства: {spouse_address}):", False)
                ], font_size_pt=10, align=WD_ALIGN_PARAGRAPH.JUSTIFY)
            else:
                to_delete.append(p)

    for p in to_delete:
        delete_paragraph(p)

    # 4. Handle Specific Templates logic
    base_name = os.path.basename(template_path)

    # A) Должнику_супругу_РИ.docx
    if "Должнику_супругу" in base_name and len(doc.tables) > 0:
        table0 = doc.tables[0]
        if len(table0.rows) > 1 and len(table0.rows[1].cells) > 1:
            c = table0.rows[1].cells[1]
            if has_spouse:
                c.text = f"{debtor_fio}\n{debtor_address}\n{spouse_fio}\n{spouse_address}"
            else:
                c.text = f"{debtor_fio}\n{debtor_address}"
            for p in c.paragraphs:
                for r in p.runs:
                    r.font.name = "Times New Roman"

    # B) в_ССП_РИ.docx
    if "в_ССП" in base_name:
        for p in doc.paragraphs:
            if "переданных Бурлаковой" in p.text or "переданных Базаровым" in p.text:
                debtor_instr = data.get("debtor_fio_instr", "") or debtor_fio
                p.text = re.sub(r'переданных [А-Яа-яЁё\s]+? для исполнения', f'переданных {debtor_instr} для исполнения', p.text)
            if "в отношении Бурлаковой" in p.text or "в отношении Базарова" in p.text:
                p.text = re.sub(r'в отношении [А-Яа-яЁё\s]+?, и направить', f'в отношении {debtor_fio_gen}, и направить', p.text)

    # C) запрос в УВМ.docx
    if "в УВМ" in base_name:
        for p in doc.paragraphs:
            if "являются кредиторами" in p.text:
                short_fio = to_short_fio(debtor_fio)
                p.text = re.sub(r'являются кредиторами [А-Яа-яЁё\s]+?\.', f'являются кредиторами {debtor_fio_gen}.', p.text)
                p.text = re.sub(r'в отношении [А-Яа-яЁё\.\s]+?$', f'в отношении {short_fio}', p.text)

    # D) в_ЕГРН_(сокращенный)_должник_супруг_РИ.docx
    if "ЕГРН" in base_name:
        debtor_egrn_block = (
            f"физическое лицо:\n"
            f"фамилия, имя, отчество (при наличии) {debtor_fio}\n"
            f"дата рождения {debtor_birth}; документ, удостоверяющий личность, паспорт, "
            f"серия {pass_series} № {pass_num}, дата выдачи: {pass_date} г., "
            f"кем выдан документ, удостоверяющий личность, {pass_by}, код подразделения {pass_code},\n"
            f"СНИЛС {debtor_snils}\n"
            f"адрес места жительства или места пребывания: {debtor_address}"
        )
        spouse_pass_s = data.get("spouse_passport_series", "")
        spouse_pass_n = data.get("spouse_passport_number", "")
        spouse_pass_b = data.get("spouse_passport_issued_by", "")
        spouse_pass_d = data.get("spouse_passport_date", "")
        spouse_pass_c = data.get("spouse_passport_code", "")

        spouse_egrn_block = (
            f"физическое лицо:\n"
            f"фамилия, имя, отчество (при наличии) {spouse_fio}\n"
            f"дата рождения {spouse_birth}; документ, удостоверяющий личность, паспорт, "
            f"серия {spouse_pass_s} № {spouse_pass_n}, дата выдачи: {spouse_pass_d} г., "
            f"кем выдан документ, удостоверяющий личность, {spouse_pass_b}, код подразделения {spouse_pass_c},\n"
            f"СНИЛС {spouse_snils}\n"
            f"адрес места жительства или места пребывания: {spouse_address}"
        )

        court_ref_str = f"Решение {court_name} от {decision_date} № {case_no}. Копия в количестве ____ экз., на ____ л."

        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    ct = cell.text
                    if "Бурлакова Ирина Сергеевна" in ct or "Базаров Николай Николаевич" in ct:
                        cell.text = debtor_egrn_block
                    elif "Бурлаков Сергей Михайлович" in ct or "Базарова Татьяна Алексеевна" in ct:
                        cell.text = spouse_egrn_block
                    elif "Решение Арбитражного суда" in ct:
                        cell.text = court_ref_str

    # 5. Update signatures and generic names in all tables
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                ct = cell.text
                if any(k in ct for k in ["Бурлаковой Ирины Сергеевны", "Базарова Николая Николаевича", "Бурлакова Ирина", "Базаров Николай"]):
                    replace_in_cell(cell, {
                        "Бурлаковой Ирины Сергеевны": debtor_fio_gen,
                        "Базарова Николая Николаевича": debtor_fio_gen,
                        "Бурлакова Ирина Сергеевна": debtor_fio,
                        "Базаров Николай Николаевич": debtor_fio,
                    })

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
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
