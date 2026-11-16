import os
import re
from typing import Dict, Any, List


def export_debtor_to_text(debtor: Dict[str, Any]) -> str:
    """
    Экспортирует карточку должника в текстовый формат 'название поля: значение'.
    """
    raw = debtor.get("parsed_raw") or debtor.get("raw_data")
    if isinstance(raw, str):
        import json
        try:
            raw = json.loads(raw)
        except Exception:
            raw = {}
    elif not isinstance(raw, dict):
        raw = {}

    def val(key, default=""):
        return str(raw.get(key) or debtor.get(key) or default).strip()

    pass_series = val("debtor_passport_series")
    pass_num = val("debtor_passport_number")
    if not pass_series and not pass_num and debtor.get("passport_data"):
        parts = str(debtor.get("passport_data", "")).split(None, 1)
        if len(parts) == 2:
            pass_series, pass_num = parts[0], parts[1]
        else:
            pass_num = str(debtor.get("passport_data", ""))

    lines = [
        "=== КАРТОЧКА ДОЛЖНИКА ===",
        f"Номер дела: {val('case_number')}",
        f"Наименование арбитражного суда: {val('court_name')}",
        f"Дата решения суда: {val('decision_date')}",
        f"Дата принятия заявления: {val('petition_date')}",
        f"ФИО должника: {val('debtor_fio') or val('full_name')}",
        f"ФИО в родительном падеже: {val('debtor_fio_gen')}",
        f"Дата рождения: {val('debtor_birth_date')}",
        f"Место рождения: {val('debtor_birth_place')}",
        f"СНИЛС: {val('debtor_snils') or val('snils')}",
        f"ИНН: {val('debtor_inn') or val('inn')}",
        f"Адрес регистрации: {val('debtor_address') or val('address')}",
        f"Паспорт серия: {pass_series}",
        f"Паспорт номер: {pass_num}",
        f"Кем выдан паспорт: {val('debtor_passport_issued_by')}",
        f"Дата выдачи паспорта: {val('debtor_passport_date')}",
        f"Код подразделения: {val('debtor_passport_code')}",
        f"Трудоустроен: {'Да' if raw.get('employer_employed') or raw.get('employer_name') else 'Нет'}",
        f"Наименование работодателя: {val('employer_name')}",
        f"ИНН работодателя: {val('employer_inn')}",
        f"Адрес работодателя: {val('employer_address')}",
        f"Семейное положение: {val('spouse_status', 'not_married')}",
        f"ФИО супруга: {val('spouse_fio')}",
        f"ФИО супруга в творительном падеже: {val('spouse_fio_instr')}",
        f"Дата рождения супруга: {val('spouse_birth_date')}",
        f"Место рождения супруга: {val('spouse_birth_place')}",
        f"Дата брака или развода: {val('marriage_date')}",
        f"СНИЛС супруга: {val('spouse_snils')}",
        f"ИНН супруга: {val('spouse_inn')}",
        f"Адрес регистрации супруга: {val('spouse_address')}",
    ]

    creditors = raw.get("creditors") or debtor.get("creditors") or []
    if creditors:
        lines.append("--- Кредиторы ---")
        for i, c in enumerate(creditors, 1):
            c_name = str(c.get("name", "")).strip()
            c_inn = str(c.get("inn", "")).strip()
            c_addr = str(c.get("address", "")).strip()
            lines.append(f"Кредитор {i} Наименование: {c_name}")
            lines.append(f"Кредитор {i} ИНН: {c_inn}")
            lines.append(f"Кредитор {i} Адрес: {c_addr}")

    lines.append("=== КОНЕЦ КАРТОЧКИ ===")
    return "\n".join(lines)


def export_all_debtors_to_text(debtors: List[Dict[str, Any]]) -> str:
    """
    Экспортирует список всех должников базы в единый текстовый файл.
    """
    chunks = [export_debtor_to_text(d) for d in debtors]
    return "\n\n".join(chunks)


def parse_debtor_from_text(text: str) -> List[Dict[str, Any]]:
    """
    Считывает одну или несколько карточек должников из текстового файла
    в формате 'название поля: значение'.
    """
    records = []
    # Split by cards if multiple
    if "=== КАРТОЧКА ДОЛЖНИКА ===" in text:
        raw_cards = text.split("=== КАРТОЧКА ДОЛЖНИКА ===")
    else:
        raw_cards = [text]

    for raw_card in raw_cards:
        if not raw_card.strip():
            continue
        data: Dict[str, Any] = {
            "creditors": []
        }
        creditor_map = {}

        for line in raw_card.splitlines():
            line = line.strip()
            if not line or line.startswith("===") or line.startswith("---"):
                continue
            if ":" not in line:
                continue
            key, val = line.split(":", 1)
            key = key.strip()
            val = val.strip()

            k_lower = key.lower()
            if "номер дела" in k_lower:
                data["case_number"] = val
            elif "наименование арбитражного суда" in k_lower or "арбитражный суд" in k_lower:
                data["court_name"] = val
            elif "дата решения суда" in k_lower:
                data["decision_date"] = val
            elif "дата принятия заявления" in k_lower:
                data["petition_date"] = val
            elif "фио должника" in k_lower:
                data["debtor_fio"] = val
                data["full_name"] = val
            elif "в родительном падеже" in k_lower:
                data["debtor_fio_gen"] = val
            elif "дата рождения должника" in k_lower or k_lower == "дата рождения":
                data["debtor_birth_date"] = val
            elif "место рождения должника" in k_lower or k_lower == "место рождения":
                data["debtor_birth_place"] = val
            elif "снилс должника" in k_lower or k_lower == "снилс":
                data["debtor_snils"] = val
                data["snils"] = val
            elif "инн должника" in k_lower or k_lower == "инн":
                data["debtor_inn"] = val
                data["inn"] = val
            elif "адрес регистрации должника" in k_lower or "адрес регистрации" in k_lower:
                data["debtor_address"] = val
                data["address"] = val
            elif "паспорт серия" in k_lower:
                data["debtor_passport_series"] = val
            elif "паспорт номер" in k_lower:
                data["debtor_passport_number"] = val
            elif "кем выдан паспорт" in k_lower:
                data["debtor_passport_issued_by"] = val
            elif "дата выдачи паспорта" in k_lower:
                data["debtor_passport_date"] = val
            elif "код подразделения" in k_lower:
                data["debtor_passport_code"] = val
            elif "трудоустроен" in k_lower:
                data["employer_employed"] = (val.lower() in ("да", "true", "1"))
            elif "наименование работодателя" in k_lower:
                data["employer_name"] = val
            elif "инн работодателя" in k_lower:
                data["employer_inn"] = val
            elif "адрес работодателя" in k_lower:
                data["employer_address"] = val
            elif "семейное положение" in k_lower:
                data["spouse_status"] = val
            elif "фио супруга в творительном" in k_lower:
                data["spouse_fio_instr"] = val
            elif "фио супруга" in k_lower:
                data["spouse_fio"] = val
            elif "дата рождения супруга" in k_lower:
                data["spouse_birth_date"] = val
            elif "место рождения супруга" in k_lower:
                data["spouse_birth_place"] = val
            elif "дата брака" in k_lower or "дата заключения" in k_lower:
                data["marriage_date"] = val
            elif "снилс супруга" in k_lower:
                data["spouse_snils"] = val
            elif "инн супруга" in k_lower:
                data["spouse_inn"] = val
            elif "адрес регистрации супруга" in k_lower:
                data["spouse_address"] = val
            elif "кредитор" in k_lower:
                # e.g.: Кредитор 1 Наименование: ПАО Сбербанк
                m = re.search(r'кредитор\s+(\d+)\s+(наименование|инн|адрес)', k_lower)
                if m:
                    idx = int(m.group(1))
                    field = m.group(2)
                    if idx not in creditor_map:
                        creditor_map[idx] = {"name": "", "address": "", "inn": ""}
                    if field == "наименование":
                        creditor_map[idx]["name"] = val
                    elif field == "инн":
                        creditor_map[idx]["inn"] = val
                    elif field == "адрес":
                        creditor_map[idx]["address"] = val

        for idx in sorted(creditor_map.keys()):
            data["creditors"].append(creditor_map[idx])

        if data.get("debtor_fio") or data.get("case_number"):
            records.append(data)

    return records
