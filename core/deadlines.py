import os
import re
from datetime import datetime, timedelta


def parse_date(date_str: str) -> datetime | None:
    """Парсит строку даты в форматах DD.MM.YYYY, DD-MM-YYYY, YYYY-MM-DD и т.д."""
    if not date_str or not isinstance(date_str, str):
        return None
    cleaned = date_str.strip()
    match = re.search(r"(\d{1,2})[./\-](\d{1,2})[./\-](\d{2,4})", cleaned)
    if not match:
        return None
    day, month, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
    if year < 100:
        year += 2000
    try:
        return datetime(year, month, day)
    except ValueError:
        return None


def add_working_days(start_date: datetime, days: int) -> datetime:
    """Добавляет N рабочих дней, пропуская субботы и воскресенья."""
    cur = start_date
    added = 0
    while added < days:
        cur += timedelta(days=1)
        # 5 = Saturday, 6 = Sunday
        if cur.weekday() < 5:
            added += 1
    return cur


def calculate_kommersant_saturday(subm_date: datetime) -> datetime:
    """
    Расписание выхода газеты 'Коммерсантъ':
    - Первая половина недели (Пн, Вт, Ср до 15:00 МСК) -> суббота этой недели.
    - Вторая половина (Чт, Пт, Сб, Вс) или Ср после 15:00 -> суббота следующей недели.
    """
    w = subm_date.weekday()
    if w <= 1:
        days_ahead = 5 - w
    elif w == 2:
        if subm_date.hour < 15:
            days_ahead = 3
        else:
            days_ahead = 10
    else:
        days_ahead = 5 - w + 7

    return subm_date + timedelta(days=days_ahead)


def calculate_deadlines(decision_date_str: str) -> dict | None:
    """
    Вычисляет контрольные процессуальные сроки по блок-схеме.
    Если этап просрочен (diff < 0), флаг is_overdue=True (чтобы скрыть его из интерфейса).
    """
    dec_date = parse_date(decision_date_str)
    if not dec_date:
        return None

    now = datetime.now()
    today = now.date()

    # 1. ЕФРСБ (3 раб. дня)
    efrsb_deadline = add_working_days(dec_date, 3)
    efrsb_diff = (efrsb_deadline.date() - today).days
    efrsb_overdue = (efrsb_diff < 0)

    # 2. Газета Коммерсантъ (10 кал. дней)
    kommersant_deadline = dec_date + timedelta(days=10)
    kom_diff = (kommersant_deadline.date() - today).days
    kom_overdue = (kom_diff < 0)

    # 3. Расчетный выход газеты
    suggested_subm = add_working_days(dec_date, 2)
    gazette_publish_date = calculate_kommersant_saturday(suggested_subm)

    # 4. Отправка запросов (15 дней от решения)
    inquiry_earliest_15d = dec_date + timedelta(days=15)
    inq_diff = (inquiry_earliest_15d.date() - today).days

    def make_deadline_badge(diff: int):
        if diff == 0:
            return {
                "text": "Срок сегодня",
                "bg": "#FEE2E2",
                "color": "#991B1B"
            }
        elif diff <= 2:
            return {
                "text": f"Осталось {diff} дн.",
                "bg": "#FEF3C7",
                "color": "#92400E"
            }
        else:
            return {
                "text": f"Осталось {diff} дн.",
                "bg": "#DCFCE7",
                "color": "#166534"
            }

    inq_badge = {
        "text": f"Через {inq_diff} дн." if inq_diff > 0 else "Можно отправлять",
        "bg": "#F1F5F9" if inq_diff > 0 else "#DCFCE7",
        "color": "#475569" if inq_diff > 0 else "#166534"
    }

    return {
        "decision_date": dec_date.strftime("%d.%m.%Y"),
        "efrsb": {
            "title": "Публикация в ЕФРСБ",
            "date": efrsb_deadline.strftime("%d.%m.%Y"),
            "badge": make_deadline_badge(efrsb_diff),
            "is_overdue": efrsb_overdue,
            "rule": "3 рабочих дня с даты решения суда"
        },
        "kommersant": {
            "title": "Заявка в газету «Коммерсантъ»",
            "date": kommersant_deadline.strftime("%d.%m.%Y"),
            "badge": make_deadline_badge(kom_diff),
            "is_overdue": kom_overdue,
            "rule": "10 календарных дней с даты решения суда",
            "schedule_note": f"График выхода: при подаче Пн–Ср до 15:00 МСК публикация выйдет в субботу ({gazette_publish_date.strftime('%d.%m.%Y')})"
        },
        "inquiries_start": {
            "title": "Отправка запросов и уведомлений",
            "date": inquiry_earliest_15d.strftime("%d.%m.%Y"),
            "badge": inq_badge,
            "is_overdue": False,
            "rule": "15 дней от даты решения или 7 дней от выхода газеты"
        }
    }
