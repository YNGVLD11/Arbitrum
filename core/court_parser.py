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
    # Cut off judges / clerk suffixes: 'в составе судьи...', 'председательствующего...'
    c = re.split(r'\s+в\s+составе|\s+судь[ия]|\s+председательствующ|\s+дело\b', c, flags=re.IGNORECASE)[0].strip()
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

def _inflect_surname_rule(surn: str, gender: str, case: str) -> str:
    """
    Правила склонения стандартных русских фамилий, защищающие от ошибок словаря
    (например, когда 'Плешков' ошибочно трактуется как Pltm plur 'Плешковы').
    """
    surn_low = surn.lower()
    if gender == 'masc':
        if surn_low.endswith(('ов', 'ев', 'ёв', 'ин', 'ын')):
            m = {'nomn': '', 'gent': 'а', 'datv': 'у', 'accs': 'а', 'ablt': 'ым', 'loct': 'е'}
            return (surn + m.get(case, '')).capitalize()
        elif surn_low.endswith(('ский', 'цкий')):
            base = surn[:-2]
            m = {'nomn': 'ий', 'gent': 'ого', 'datv': 'ому', 'accs': 'ого', 'ablt': 'им', 'loct': 'ом'}
            return (base + m.get(case, 'ий')).capitalize()
        elif surn_low.endswith(('ой',)):
            base = surn[:-2]
            m = {'nomn': 'ой', 'gent': 'ого', 'datv': 'ому', 'accs': 'ого', 'ablt': 'ым', 'loct': 'ом'}
            return (base + m.get(case, 'ой')).capitalize()
    elif gender == 'femn':
        if surn_low.endswith(('ова', 'ева', 'ёва', 'ина', 'ына')):
            base = surn[:-1]
            m = {'nomn': 'а', 'gent': 'ой', 'datv': 'ой', 'accs': 'у', 'ablt': 'ой', 'loct': 'ой'}
            return (base + m.get(case, 'а')).capitalize()
        elif surn_low.endswith(('ская', 'цкая')):
            base = surn[:-2]
            m = {'nomn': 'ая', 'gent': 'ой', 'datv': 'ой', 'accs': 'ую', 'ablt': 'ой', 'loct': 'ой'}
            return (base + m.get(case, 'ая')).capitalize()
    return ""


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

    # Приоритет правилу склонения фамилий
    s_rule = _inflect_surname_rule(surn, gender, case)

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

    s = s_rule if s_rule else _inflect_part(surn, 'Surn')
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
    Analyzes court decision text (or file) and extracts structured data.
    """
    if "\n" in file_path or len(file_path) > 260 or not os.path.exists(file_path):
        text = file_path
        actual_path = ""
    else:
        text = extract_text_from_file(file_path)
        actual_path = file_path

    norm = re.sub(r'[ \t]+', ' ', text)

    res = {
        "file_path": actual_path,
        "court_name": "",
        "case_number": "",
        "decision_date": "",
        "petition_date": "",
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
        "manager_fio": "Гусарова Ксения Андреевна",
        "manager_inn": "380470431942",
        "manager_snils": "136-556-599 95",
        "manager_sro": 'САМРО "Ассоциация антикризисных управляющих"',
        "manager_sro_ogrn": "1026300003751",
        "manager_sro_inn": "6315944042",
        "manager_sro_address": "443072, г. Самара, Московское шоссе, 18-й км",
        "manager_corr_address": "630007, г. Новосибирск, а/я 1",
        "manager_phone": "+7 (913) 989-01-63",
        "manager_email": "kseniya_gusarova@mail.ru"
    }

    # 1. Court Name
    m_court = re.search(r'(АРБИТРАЖНЫЙ\s+СУД\s+[А-Яа-яЁё\s]+?)(?=\s+в\s+составе|\n|\s*Дело|\s*Р\s*Е\s*Ш\s*Е\s*Н\s*И\s*Е|\s*О\s*П\s*Р\s*Е\s*Д\s*Е\s*Л\s*Е\s*Н\s*И\s*Е|\s*\d{1,2}\s+[а-яА-ЯёЁ]+)', norm, re.IGNORECASE)
    if m_court:
        res["court_name"] = clean_court_name(m_court.group(1))

    single_norm = ' '.join(norm.split())

    # 2. Case Number
    m_case = re.search(r'Дело\s*№?\s*(А\d+[\-–—]\d+/\d+)', single_norm, re.IGNORECASE)
    if m_case:
        res["case_number"] = m_case.group(1).replace('–', '-').replace('—', '-')

    # 3. Decision Date (prioritize top header zone)
    header_chunk = single_norm[:800]
    m_date = re.search(r'(\d{1,2}\s+[а-яА-ЯёЁ]+\s+\d{4}\s*(?:года|г\.?)|(?<!\d)\d{2}\.\d{2}\.\d{4})', header_chunk)
    if not m_date:
        m_date = re.search(r'(\d{1,2}\s+[а-яА-ЯёЁ]+\s+\d{4}\s*(?:года|г\.?))', single_norm)
    if not m_date:
        m_date = re.search(r'(\d{2}\.\d{2}\.\d{4})', single_norm)
    if m_date:
        res["decision_date"] = parse_russian_date(m_date.group(1))

    # 3.1. Petition / Application Date (Дата принятия заявления к производству)
    m_pet = re.search(r'(?:заявление\s*(?:должника|конкурсного\s*кредитора)?\s*(?:принято|поступило|зарегистрировано)|принять\s*заявление|определением\s*от)\s*(\d{2}\.\d{2}\.\d{4}|\d{1,2}\s+[а-яА-ЯёЁ]+\s+\d{4})', single_norm, re.IGNORECASE)
    if m_pet:
        res["petition_date"] = parse_russian_date(m_pet.group(1))
    else:
        m_pet2 = re.search(r'заявлени[ея][^\.\n]*?от\s*(\d{2}\.\d{2}\.\d{4})', single_norm, re.IGNORECASE)
        if m_pet2:
            res["petition_date"] = m_pet2.group(1)

    # 4. Debtor Info
    debtor_fio = ""
    # Strategy 1: introductory part 'заявление <ФИО> о признании'
    m_intro = re.search(r'заявление\s+([А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+)\s+о признании', single_norm)
    if m_intro:
        debtor_fio = m_intro.group(1).strip()

    # Strategy 2: 'дело по заявлению должника – <ФИО>'
    if not debtor_fio:
        m_fio2 = re.search(r'дело по заявлению должника\s*[\-–—\s]*([А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+)', single_norm)
        if m_fio2:
            debtor_fio = m_fio2.group(1).strip()

    # Strategy 3: in operative part 'ввести в отношении <ФИО>,' / 'признать гражданина <ФИО>'
    if not debtor_fio:
        m_fio3 = re.search(r'(?:ввести в отношении|признать гражданина)\s+([А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+)[,\s]+(?:\d{2}\.\d{2}\.\d{4}|\()', single_norm)
        if m_fio3:
            debtor_fio = m_fio3.group(1).strip()

    # Strategy 4: fallback to parenthesized block if exists
    if not debtor_fio:
        m_debtor = re.search(r'дело по заявлению должника\s*[\-–—]\s*([А-Яа-яЁё\s]+?)\s*\((.*?)\)', norm, re.DOTALL)
        if not m_debtor:
            m_debtor = re.search(r'в отношении\s+(?:гражданина[\-–—\s]должника|должника)\s*[\-–—\s]*([А-Яа-яЁё\s]+?)\s*\((.*?)\)', norm, re.DOTALL | re.IGNORECASE)
        if m_debtor:
            raw_cand = " ".join(m_debtor.group(1).split())
            if "супруг" not in raw_cand.lower() and len(raw_cand.split()) == 3:
                debtor_fio = raw_cand

    # Strategy 5: Anchor backwards from INN / SNILS (for decisions like: 'признать банкротом Поварницыну Дарью Викторовну, 17.04.1986 года рождения, ..., ИНН ...')
    if not debtor_fio:
        m_anchor = re.search(r'(?:ИНН|СНИЛС)[:\s]*\d', single_norm, re.IGNORECASE)
        if m_anchor:
            pre_anchor = single_norm[max(0, m_anchor.start() - 350):m_anchor.start()]
            # Pattern: 3 words capitalized followed by date of birth or comma
            m_cand_pre = re.search(r'([А-ЯЁ][а-яё]+(?:-[А-ЯЁ][а-яё]+)?\s+[А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+)[,\s]+(?:\d{2}\.\d{2}\.\d{4}|(?:\d{1,2}\s+[а-яА-ЯёЁ]+\s+\d{4})|\()', pre_anchor)
            if m_cand_pre:
                cand_text = m_cand_pre.group(1).strip()
                if not any(k in cand_text.lower() for k in ('арбитражный', 'судья', 'управляющий', 'гусарова')):
                    debtor_fio = cand_text

    # Strategy 6: NLP / Natasha extraction fallback
    if not debtor_fio:
        try:
            from natasha import Segmenter, MorphVocab, NewsEmbedding, NewsMorphTagger, NewsNERTagger, Doc
            _seg = Segmenter()
            _mv = MorphVocab()
            _emb = NewsEmbedding()
            _mt = NewsMorphTagger(_emb)
            _nt = NewsNERTagger(_emb)
            _doc = Doc(single_norm[:2500])
            _doc.segment(_seg)
            _doc.tag_morph(_mt)
            _doc.tag_ner(_nt)
            for s in _doc.spans:
                if s.type == "PER":
                    s.normalize(_mv)
                    p_name = s.normal
                    p_parts = p_name.split()
                    if len(p_parts) == 3 and not any(k in p_name.lower() for k in ('судь', 'гусарова', 'секретар', 'председател')):
                        debtor_fio = p_name
                        break
        except Exception:
            pass

    if debtor_fio:
        nomn_debtor = to_nomn_fio(debtor_fio)
        res["debtor_fio"] = nomn_debtor
        res["debtor_fio_gen"] = inflect_fio(nomn_debtor, 'gent')

    # 4.1 Debtor Details (Birth Date, Birth Place, Address, SNILS, INN)
    # 4.1.1 Birth Date: '17.04.1986 г.р.' or '17.04.1986 года рождения' or right after debtor name
    mb = re.search(r'(\d{2}\.\d{2}\.\d{4})\s*(?:г\.?\s*р|года рождения|г\.\s*рождения)', single_norm, re.IGNORECASE)
    if not mb and debtor_fio:
        # Search directly near debtor fio
        idx_fio = single_norm.find(debtor_fio)
        if idx_fio >= 0:
            after_fio = single_norm[idx_fio:idx_fio + 200]
            mb = re.search(r'(\d{2}\.\d{2}\.\d{4})', after_fio)
    if not mb:
        mb = re.search(r'(?:дата рождения|родивш[ая][яся|егося]+)[:\s]*(\d{2}\.\d{2}\.\d{4})', single_norm, re.IGNORECASE)
    if mb:
        res["debtor_birth_date"] = mb.group(1)

    mp = re.search(r'место рождения:\s*(.*?)(?=\.?\s*[Аа]дрес|\s*ИНН|\s*СНИЛС|;)', single_norm, re.IGNORECASE)
    if mp:
        res["debtor_birth_place"] = mp.group(1).strip(' .,')

    ma = re.search(r'[Аа]дрес(?: места)? регистрации:\s*(.*?)(?=;\s*ИНН|\s*ИНН|,\s*СНИЛС|\s*СНИЛС|\s*реализацию|\s*паспорт|\))', single_norm, re.IGNORECASE)
    if ma:
        addr = ma.group(1).strip(' .,;')
        addr = re.sub(r',?\s*СНИЛС.*', '', addr, flags=re.IGNORECASE).strip()
        addr = re.sub(r'(\d+)\s*[\-–—]\s*([а-яА-ЯёЁ]+)', r'\1-\2', addr)
        addr = re.sub(r'\s{2,}', ' ', addr)
        res["debtor_address"] = addr

    ms = re.search(r'СНИЛС[:\s]*([\d\s\-–—]{11,25})', single_norm, re.IGNORECASE)
    if ms:
        raw_s = ms.group(1).strip()
        digits = re.sub(r'\D', '', raw_s)[:11]
        if len(digits) == 11:
            res["debtor_snils"] = f"{digits[:3]}-{digits[3:6]}-{digits[6:9]} {digits[9:]}"
        else:
            raw_s = re.sub(r'(\d+)\s*[\-–—]\s*(\d+)', r'\1-\2', raw_s)
            raw_s = re.sub(r'\s{2,}', ' ', raw_s)
            res["debtor_snils"] = raw_s

    mi = re.search(r'ИНН[:\s]*(\d{12})', single_norm, re.IGNORECASE)
    if mi:
        res["debtor_inn"] = mi.group(1)

    # 5. Passport
    m_pass_all = re.search(r'паспорт(?:ные данные)?[:\s]+сери[яи]?\s*(\d{4})\s*№?\s*(\d{6})[,\s]+выдан\s+([^,]+?)[,\s]+(?:дата выдачи[:\s]*)?(\d{2}\.\d{2}\.\d{4})[,\s]+(?:код подразделения[:\s]*)?(\d{3}[\-–—]\d{3})', single_norm, re.IGNORECASE)
    if m_pass_all:
        res["debtor_passport_series"] = m_pass_all.group(1)
        res["debtor_passport_number"] = m_pass_all.group(2)
        res["debtor_passport_issued_by"] = m_pass_all.group(3).strip()
        res["debtor_passport_date"] = m_pass_all.group(4)
        res["debtor_passport_code"] = m_pass_all.group(5)

    # 6. Spouse Information (only genuine full names)
    m_spouse = re.search(r'Должник состоит в браке\s*с\s*([А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+)', single_norm)
    if m_spouse:
        res["spouse_status"] = "married"
        raw_spouse = m_spouse.group(1).strip()
        nomn_spouse = to_nomn_fio(raw_spouse)
        res["spouse_fio"] = nomn_spouse
        res["spouse_fio_gen"] = inflect_fio(nomn_spouse, 'gent')
        res["spouse_fio_instr"] = inflect_fio(nomn_spouse, 'ablt')

        after_sp = single_norm[m_spouse.end():m_spouse.end() + 150]
        msb = re.search(r'(\d{2}\.\d{2}\.\d{4})', after_sp)
        if msb:
            res["spouse_birth_date"] = msb.group(1)
    else:
        m_divorced = re.search(r'Должник состоял в браке\s*с\s*([А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+)', single_norm)
        if m_divorced:
            res["spouse_status"] = "divorced"
            raw_spouse = m_divorced.group(1).strip()
            nomn_spouse = to_nomn_fio(raw_spouse)
            res["spouse_fio"] = nomn_spouse
            res["spouse_fio_gen"] = inflect_fio(nomn_spouse, 'gent')
            res["spouse_fio_instr"] = inflect_fio(nomn_spouse, 'ablt')

            after_div = single_norm[m_divorced.end():m_divorced.end() + 150]
            msb = re.search(r'(\d{2}\.\d{2}\.\d{4})', after_div)
            if msb:
                res["spouse_birth_date"] = msb.group(1)
        else:
            res["spouse_status"] = "not_married"

    # 7. Financial Manager in decision
    m_mgr = re.search(r'(?i:утвердить финансовым управляющим|финансовым управляющим утвержден[ао]?).*?([А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+)', single_norm)
    if m_mgr:
        mgr_raw = m_mgr.group(1).strip()
        res["manager_fio"] = to_nomn_fio(mgr_raw)
        after_mgr = single_norm[m_mgr.end():m_mgr.end() + 300]
        m_minn = re.search(r'ИНН[:\s]*(\d{12})', after_mgr)
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
    parsed = Signal(dict)
    failed = Signal(str)

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
            self.parsed.emit(res)
        except Exception as e:
            self.failed_signal.emit(str(e))
            self.failed.emit(str(e))
