import os
import json
import sqlite3
import threading
from typing import Optional, Any, Dict, List


class DatabaseManager:
    """
    Управление локальной реляционной базой данных SQLite для хранения картотеки должников.
    """

    def __init__(self, db_path: Optional[str] = None) -> None:
        """
        Инициализация подключения к базе данных SQLite и создание таблиц.
        """
        if db_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            data_dir = os.path.join(base_dir, "data")
            os.makedirs(data_dir, exist_ok=True)
            self.db_path = os.path.join(data_dir, "arbitrum.db")
        else:
            self.db_path = db_path
            parent_dir = os.path.dirname(self.db_path)
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)

        self._lock = threading.Lock()
        self._init_tables()

    def _get_connection(self) -> sqlite3.Connection:
        """
        Создание и настройка подключения к SQLite.
        """
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def _init_tables(self) -> None:
        """
        Создание необходимых таблиц базы данных при их отсутствии и миграция схемы.
        """
        with self._lock, self._get_connection() as conn:
            cursor = conn.cursor()

            # Таблица должников
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS Debtors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    full_name TEXT NOT NULL,
                    case_number TEXT,
                    snils TEXT,
                    inn TEXT,
                    passport_data TEXT,
                    address TEXT,
                    raw_data TEXT
                );
            """)

            # Проверка наличия колонки raw_data для существующих БД
            cursor.execute("PRAGMA table_info(Debtors);")
            cols = [r["name"] for r in cursor.fetchall()]
            if "raw_data" not in cols:
                cursor.execute("ALTER TABLE Debtors ADD COLUMN raw_data TEXT;")

            conn.commit()

    # -------------------------------------------------------------------------
    # CRUD: Должники (Debtors)
    # -------------------------------------------------------------------------

    def save_debtor_full(self, debtor_data: Dict[str, Any], debtor_id: Optional[int] = None) -> int:
        """
        Сохраняет или обновляет полную карточку должника.
        """
        full_name = str(debtor_data.get("debtor_fio", "") or debtor_data.get("full_name", "")).strip()
        case_no = str(debtor_data.get("case_number", "")).strip()
        snils = str(debtor_data.get("debtor_snils", "") or debtor_data.get("snils", "")).strip()
        inn = str(debtor_data.get("debtor_inn", "") or debtor_data.get("inn", "")).strip()
        addr = str(debtor_data.get("debtor_address", "") or debtor_data.get("address", "")).strip()

        pass_series = str(debtor_data.get("debtor_passport_series", "")).strip()
        pass_num = str(debtor_data.get("debtor_passport_number", "")).strip()
        pass_str = debtor_data.get("passport_data", "")
        if not pass_str:
            pass_str = f"{pass_series} {pass_num}".strip()

        raw_json = json.dumps(debtor_data, ensure_ascii=False)

        with self._lock, self._get_connection() as conn:
            cursor = conn.cursor()
            if debtor_id:
                cursor.execute("""
                    UPDATE Debtors
                    SET full_name = ?, case_number = ?, snils = ?, inn = ?,
                        passport_data = ?, address = ?, raw_data = ?
                    WHERE id = ?;
                """, (full_name, case_no, snils, inn, pass_str, addr, raw_json, debtor_id))
                conn.commit()
                return debtor_id
            else:
                cursor.execute("""
                    INSERT INTO Debtors (full_name, case_number, snils, inn, passport_data, address, raw_data)
                    VALUES (?, ?, ?, ?, ?, ?, ?);
                """, (full_name, case_no, snils, inn, pass_str, addr, raw_json))
                conn.commit()
                return int(cursor.lastrowid)

    def add_debtor(
        self,
        full_name: str,
        case_number: str = "",
        snils: str = "",
        inn: str = "",
        passport_data: str = "",
        address: str = "",
        raw_data: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Добавление записи о должнике или возврат идентификатора существующего должника.
        """
        full_name_clean = full_name.strip()
        case_number_clean = case_number.strip()
        raw_json = json.dumps(raw_data, ensure_ascii=False) if raw_data else None

        with self._lock, self._get_connection() as conn:
            cursor = conn.cursor()

            # Поиск дубликата по номеру дела или полному совпадению ФИО
            if case_number_clean:
                cursor.execute(
                    "SELECT id, raw_data FROM Debtors WHERE case_number = ? LIMIT 1;",
                    (case_number_clean,)
                )
                existing = cursor.fetchone()
                if existing:
                    cursor.execute("""
                        UPDATE Debtors
                        SET full_name = ?, snils = COALESCE(NULLIF(?, ''), snils),
                            inn = COALESCE(NULLIF(?, ''), inn),
                            passport_data = COALESCE(NULLIF(?, ''), passport_data),
                            address = COALESCE(NULLIF(?, ''), address),
                            raw_data = COALESCE(?, raw_data)
                        WHERE id = ?;
                    """, (full_name_clean, snils, inn, passport_data, address, raw_json, existing["id"]))
                    conn.commit()
                    return int(existing["id"])

            cursor.execute("""
                INSERT INTO Debtors (full_name, case_number, snils, inn, passport_data, address, raw_data)
                VALUES (?, ?, ?, ?, ?, ?, ?);
            """, (full_name_clean, case_number_clean, snils, inn, passport_data, address, raw_json))
            conn.commit()
            return int(cursor.lastrowid)

    def get_debtors(self) -> List[Dict[str, Any]]:
        """
        Получение списка всех должников, отсортированных по имени.
        """
        with self._lock, self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM Debtors ORDER BY id ASC;")
            rows = cursor.fetchall()
            res = []
            for r in rows:
                item = dict(r)
                if item.get("raw_data"):
                    try:
                        item["parsed_raw"] = json.loads(item["raw_data"])
                    except Exception:
                        item["parsed_raw"] = {}
                else:
                    item["parsed_raw"] = {}
                res.append(item)
            return res

    def get_debtor_by_id(self, debtor_id: int) -> Optional[Dict[str, Any]]:
        """
        Получение карточки должника по его первичному ключу.
        """
        with self._lock, self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM Debtors WHERE id = ?;", (debtor_id,))
            row = cursor.fetchone()
            if not row:
                return None
            item = dict(row)
            if item.get("raw_data"):
                try:
                    item["parsed_raw"] = json.loads(item["raw_data"])
                except Exception:
                    item["parsed_raw"] = {}
            else:
                item["parsed_raw"] = {}
            return item

    def delete_debtor(self, debtor_id: int) -> bool:
        """
        Удаление записи должника по идентификатору.
        """
        with self._lock, self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM Debtors WHERE id = ?;", (debtor_id,))
            conn.commit()
            return cursor.rowcount > 0


