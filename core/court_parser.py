import re
import os
from typing import Dict, Any, Optional
from PySide6.QtCore import QThread, Signal
import pypdf
import pymorphy3

morph = pymorphy3.MorphAnalyzer()

MONTHS = {
    'января': '01', 'февраля': '02', 'марта': '03', 'апреля': '04',
    'мая': '05', 'июня': '06', 'июля': '07', 'августа': '08',
    'сентября': '09', 'октября': '10', 'ноября': '11', 'декабря': '12'
}

def parse_russian_date(date_str: str) -> str:
    if not date_str:
        return ""
    m = re.search(r'(\d{1,2})\s+([а-яА-ЯёЁ]+)\s+(\d{4})', date_str)
    if m:
        day = f"{int(m.group(1)):02d}"
        mon_str = m.group(2).lower()
        mon = MONTHS.get(mon_str, "01")
        year = m.group(3)
        return f"{day}.{mon}.{year}"
    m2 = re.search(r'(\d{2}\.\d{2}\.\d{4})', date_str)
    if m2:
        return m2.group(1)
    return date_str.strip()

def clean_court_name(raw_court: str) -> str:
    if not raw_court:
        return ""
    c = " ".join(raw_court.split())
    c = re.sub(r'област\s+и', 'области', c, flags=re.IGNORECASE)
    c = re.sub(r'кра\s+я', 'края', c, flags=re.IGNORECASE)
    parts = c.split()
    if len(parts) >= 2 and parts[0].upper() == 'АРБИТРАЖНЫЙ' and parts[1].upper() == 'СУД':
        res = ['Арбитражный', 'суд']
        for p in parts[2:]:
            plow = p.lower()
            if plow in ('области', 'края', 'района', 'округа', 'города', 'автономного'):
                res.append(plow)
            else:
                res.append(p.capitalize())
        return " ".join(res)
    return c

def inflect_fio(fio_str: str, case: str = 'gent') -> str:
    """
    Inflects full Russian name (Surname Name Patronymic) to a specified case ('gent', 'ablt', 'nomn', etc.)
    accurately respecting grammatical gender and animacy.
    """
    parts = fio_str.strip().split()
    if len(parts) != 3:
        return fio_str

    surn, name, patr = parts
    gender = 'femn' if patr.endswith(('вна', 'чна', 'шна', 'ична', 'вной', 'чной', 'вны', 'чны', 'шной', 'вну')) else 'masc'

    def _inflect_part(part: str, tag_name: str) -> str:
        candidates = morph.parse(part)
        # 1. Match tag, gender, and case
        for c in candidates:
            if tag_name in c.tag and gender in c.tag:
                inf = c.inflect({case})
                if inf:
                    return inf.word.capitalize()
        # 2. Match tag and case
        for c in candidates:
            if tag_name in c.tag:
                inf = c.inflect({case, gender})
                if inf:
                    return inf.word.capitalize()
        # 3. Fallback
        inf = candidates[0].inflect({case})
        return inf.word.capitalize() if inf else part

    s = _inflect_part(surn, 'Surn')
    n = _inflect_part(name, 'Name')
    p = _inflect_part(patr, 'Patr')
    return f"{s} {n} {p}"

def to_nomn_fio(fio_str: str) -> str:
    """
    Converts full Russian name from any case back to Nominative (Именительный).
    """
    parts = fio_str.strip().split()
    if len(parts) != 3:
        return fio_str

    surn, name, patr = parts
    gender = 'femn' if patr.endswith(('вной', 'чной', 'шной', 'вны', 'чны', 'шны', 'вна', 'чна', 'вну')) else 'masc'

    def _to_nomn(part: str, tag_name: str) -> str:
        candidates = morph.parse(part)
        for c in candidates:
            if tag_name in c.tag and gender in c.tag:
                inf = c.inflect({'nomn'})
                if inf:
                    return inf.word.capitalize()
        for c in candidates:
            if tag_name in c.tag:
                inf = c.inflect({'nomn'})
                if inf:
                    return inf.word.capitalize()
        return part

    s = _to_nomn(surn, 'Surn')
    n = _to_nomn(name, 'Name')
    p = _to_nomn(patr, 'Patr')
    return f"{s} {n} {p}"

def extract_text_from_file(file_path: str) -> str:
    """
    Extracts text from PDF or DOCX file.
    """
    ext = os.path.splitext(file_path)[1].lower()
    if ext == '.pdf':
        reader = pypdf.PdfReader(file_path)
        pages_text = [p.extract_text() or "" for p in reader.pages]
        return "\n".join(pages_text)
    elif ext in ('.docx', '.doc'):
        import docx
        doc = docx.Document(file_path)
        return "\n".join(p.text for p in doc.paragraphs)
    else:
        raise ValueError(f"Неподдерживаемый формат файла: {ext}")

def parse_court_decision(file_path: str) -> Dict[str, Any]:
    """
    Analyzes court decision text and extracts structured data.
    """
    text = extract_text_from_file(file_path)
    norm = re.sub(r'[ \t]+', ' ', text)

    res = {
        "file_path": file_path,
        "court_name": "",
        "case_number": "",
        "decision_date": "",
        "debtor_fio": "",
        "debtor_fio_gen": "",
        "debtor_birth_date": "",
        "debtor_birth_place": "",
        "debtor_address": "",
        "debtor_snils": "",
        "debtor_inn": "",
        "debtor_passport_series": "",
        "debtor_passport_number": "",
        "debtor_passport_issued_by": "",
        "debtor_passport_date": "",
        "debtor_passport_code": "",
        "spouse_status": "not_married",  # 'not_married', 'married', 'divorced'
        "spouse_fio": "",
        "spouse_fio_gen": "",
        "spouse_fio_instr": "",
        "spouse_birth_date": "",
        "spouse_birth_place": "",
        "spouse_address": "",
        "spouse_snils": "",
        "spouse_inn": "",
        "spouse_passport_series": "",
        "spouse_passport_number": "",
        "spouse_passport_issued_by": "",
        "spouse_passport_date": "",
        "spouse_passport_code": "",
        "marriage_date": "",
        "manager_fio": "",
        "manager_inn": "",
        "manager_snils": "",
        "manager_sro": 'САМРО "Ассоциация антикризисных управляющих"',
        "manager_sro_ogrn": "1026300003751",
        "manager_sro_inn": "6315944042",
        "manager_sro_address": "443072, г. Самара, Московское шоссе, 18-й км",
        "manager_corr_address": "630007, г. Новосибирск, а/я 1",
        "manager_phone": "+7 (913) 989-01-63",
        "manager_email": "kseniya_gusarova@mail.ru"
    }

    # 1. Court Name
    m_court = re.search(r'(АРБИТРАЖНЫЙ\s+СУД\s+[А-Яа-яЁё\s]+?)(?=\n|\s*Дело|\s*Р\s*Е\s*Ш\s*Е\s*Н\s*И\s*Е|\s*О\s*П\s*Р\s*Е\s*Д\s*Е\s*Л\s*Е\s*Н\s*И\s*Е)', norm, re.IGNORECASE)
    if m_court:
        res["court_name"] = clean_court_name(m_court.group(1))

    # 2. Case Number
    m_case = re.search(r'Дело\s*№?\s*(А\d+[\-–—]\d+/\d+)', norm, re.IGNORECASE)
    if m_case:
        res["case_number"] = m_case.group(1).replace('–', '-').replace('—', '-')

    # 3. Decision Date
    m_date = re.search(r'(\d{1,2}\s+[а-яА-ЯёЁ]+\s+\d{4}\s*года|\d{2}\.\d{2}\.\d{4})', norm)
    if m_date:
        res["decision_date"] = parse_russian_date(m_date.group(1))

    # 4. Debtor Info
    # e.g.: дело по заявлению должника – Иванов Иван Иванович (01.01.1980 г.р., ...)
    m_debtor = re.search(r'дело по заявлению должника\s*[\-–—]\s*([А-Яа-яЁё\s]+?)\s*\((.*?)\)', norm, re.DOTALL)
    if not m_debtor:
        # fallback: в отношении гражданина-должника ...
        m_debtor = re.search(r'в отношении\s+(?:гражданина[\-–—\s]должника|должника)\s*[\-–—\s]*([А-Яа-яЁё\s]+?)\s*\((.*?)\)', norm, re.DOTALL | re.IGNORECASE)

    if m_debtor:
        raw_debtor_fio = " ".join(m_debtor.group(1).split())
        details = " ".join(m_debtor.group(2).split())

        nomn_debtor = to_nomn_fio(raw_debtor_fio)
        res["debtor_fio"] = nomn_debtor
        res["debtor_fio_gen"] = inflect_fio(nomn_debtor, 'gent')

        mb = re.search(r'(\d{2}\.\d{2}\.\d{4})\s*г\.?\s*р\.?', details)
        if mb:
            res["debtor_birth_date"] = mb.group(1)

        mp = re.search(r'место рождения:\s*([^,]+)', details, re.IGNORECASE)
        if mp:
            res["debtor_birth_place"] = mp.group(1).strip()

        ma = re.search(r'адрес регистрации:\s*([^,]+(?:,\s*[^,]+){1,5})', details, re.IGNORECASE)
        if ma:
            addr = ma.group(1).strip()
            addr = re.sub(r',?\s*СНИЛС.*', '', addr, flags=re.IGNORECASE).strip()
            # Clean accidental intra-word spaces from PDF rendering: e.g. "2 -й пер." -> "2-й пер."
            addr = re.sub(r'(\d+)\s*[\-–—]\s*([а-яА-ЯёЁ]+)', r'\1-\2', addr)
            addr = re.sub(r'\s{2,}', ' ', addr)
            res["debtor_address"] = addr

        ms = re.search(r'СНИЛС:\s*([\d\s\-]+)', details, re.IGNORECASE)
        if ms:
            raw_s = ms.group(1).strip()
            raw_s = re.sub(r'(\d+)\s*[\-–—]\s*(\d+)', r'\1-\2', raw_s)
            raw_s = re.sub(r'\s{2,}', ' ', raw_s)
            res["debtor_snils"] = raw_s

        mi = re.search(r'ИНН:\s*([\d\s]+)', details, re.IGNORECASE)
        if mi:
            res["debtor_inn"] = mi.group(1).replace(" ", "").strip()

        # Check passport in details if present
        mpass = re.search(r'паспорт\s*(\d{2}\s*\d{2}|\d{4})\s*(\d{6})', details, re.IGNORECASE)
        if mpass:
            res["debtor_passport_series"] = mpass.group(1).replace(" ", "")
            res["debtor_passport_number"] = mpass.group(2)

    # 5. Passport in general text if not in debtor header
    m_pass_all = re.search(r'паспорт(?:ные данные)?[:\s]+сери[яи]\s*(\d{4})\s*№?\s*(\d{6})[,\s]+выдан\s+([^,]+?)[,\s]+(?:дата выдачи[:\s]*)?(\d{2}\.\d{2}\.\d{4})[,\s]+(?:код подразделения[:\s]*)?(\d{3}[\-–—]\d{3})', norm, re.IGNORECASE)
    if m_pass_all:
        res["debtor_passport_series"] = m_pass_all.group(1)
        res["debtor_passport_number"] = m_pass_all.group(2)
        res["debtor_passport_issued_by"] = m_pass_all.group(3).strip()
        res["debtor_passport_date"] = m_pass_all.group(4)
        res["debtor_passport_code"] = m_pass_all.group(5)

    # 6. Spouse Information
    # "Должник состоит в браке с Ивановой Анной Сергеевной (01.01.1982 г.р.)"
    m_spouse = re.search(r'Должник состоит в браке\s*с\s*([А-Яа-яЁё\s]+?)\s*\((.*?)\)', norm, re.IGNORECASE)
    if m_spouse:
        res["spouse_status"] = "married"
        raw_spouse = " ".join(m_spouse.group(1).split())
        nomn_spouse = to_nomn_fio(raw_spouse)
        res["spouse_fio"] = nomn_spouse
        res["spouse_fio_gen"] = inflect_fio(nomn_spouse, 'gent')
        res["spouse_fio_instr"] = inflect_fio(nomn_spouse, 'ablt')

        s_det = m_spouse.group(2)
        msb = re.search(r'(\d{2}\.\d{2}\.\d{4})', s_det)
        if msb:
            res["spouse_birth_date"] = msb.group(1)
    else:
        # Check divorced: "состоял в браке с ..."
        m_divorced = re.search(r'Должник состоял в браке\s*с\s*([А-Яа-яЁё\s]+?)\s*\((.*?)\)', norm, re.IGNORECASE)
        if m_divorced:
            res["spouse_status"] = "divorced"
            raw_spouse = " ".join(m_divorced.group(1).split())
            nomn_spouse = to_nomn_fio(raw_spouse)
            res["spouse_fio"] = nomn_spouse
            res["spouse_fio_gen"] = inflect_fio(nomn_spouse, 'gent')
            res["spouse_fio_instr"] = inflect_fio(nomn_spouse, 'ablt')

            s_det = m_divorced.group(2)
            msb = re.search(r'(\d{2}\.\d{2}\.\d{4})', s_det)
            if msb:
                res["spouse_birth_date"] = msb.group(1)

    # 7. Financial Manager in decision
    m_mgr = re.search(r'(?:Утвердить финансовым управляющим|финансовым управляющим утвержден[ао]?)[^А-ЯЁ]*([А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+)\s*\((.*?)\)', norm, re.IGNORECASE)
    if m_mgr:
        mgr_raw = m_mgr.group(1).strip()
        res["manager_fio"] = to_nomn_fio(mgr_raw)
        mgr_det = m_mgr.group(2)
        m_minn = re.search(r'ИНН\s*(\d{12})', mgr_det)
        if m_minn:
            res["manager_inn"] = m_minn.group(1)

    return res


class CourtParserWorker(QThread):
    """
    Background worker thread to parse court documents without blocking UI.
    """
    started_signal = Signal()
    progress = Signal(int, str)
    finished_signal = Signal(dict)
    failed_signal = Signal(str)

    def __init__(self, file_path: str):
        super().__init__()
        self.file_path = file_path

    def run(self):
        try:
            self.started_signal.emit()
            self.progress.emit(20, "Чтение файла документа...")
            res = parse_court_decision(self.file_path)
            self.progress.emit(70, "Анализ реквизитов и участников...")
            self.progress.emit(100, "Готово")
            self.finished_signal.emit(res)
        except Exception as e:
            self.failed_signal.emit(str(e))
