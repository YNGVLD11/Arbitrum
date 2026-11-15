import os
import sqlite3
import threading
from typing import Optional, Any


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
        Создание необходимых таблиц базы данных при их отсутствии.
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
                    address TEXT
                );
            """)

            conn.commit()

    # -------------------------------------------------------------------------
    # CRUD: Должники (Debtors)
    # -------------------------------------------------------------------------

    def add_debtor(
        self,
        full_name: str,
        case_number: str = "",
        snils: str = "",
        inn: str = "",
        passport_data: str = "",
        address: str = ""
    ) -> int:
        """
        Добавление записи о должнике или возврат идентификатора существующего должника.
        """
        full_name_clean = full_name.strip()
        case_number_clean = case_number.strip()

        with self._lock, self._get_connection() as conn:
            cursor = conn.cursor()

            # Поиск дубликата по номеру дела или полному совпадению ФИО
            if case_number_clean:
                cursor.execute(
                    "SELECT id FROM Debtors WHERE case_number = ? LIMIT 1;",
                    (case_number_clean,)
                )
                existing = cursor.fetchone()
                if existing:
                    cursor.execute("""
                        UPDATE Debtors
                        SET full_name = ?, snils = COALESCE(NULLIF(?, ''), snils),
                            inn = COALESCE(NULLIF(?, ''), inn),
                            passport_data = COALESCE(NULLIF(?, ''), passport_data),
                            address = COALESCE(NULLIF(?, ''), address)
                        WHERE id = ?;
                    """, (full_name_clean, snils, inn, passport_data, address, existing["id"]))
                    conn.commit()
                    return int(existing["id"])

            cursor.execute("""
                INSERT INTO Debtors (full_name, case_number, snils, inn, passport_data, address)
                VALUES (?, ?, ?, ?, ?, ?);
            """, (full_name_clean, case_number_clean, snils, inn, passport_data, address))
            conn.commit()
            return int(cursor.lastrowid)

    def get_debtors(self) -> list[dict[str, Any]]:
        """
        Получение списка всех должников, отсортированных по имени.
        """
        with self._lock, self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM Debtors ORDER BY full_name ASC;")
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    def get_debtor_by_id(self, debtor_id: int) -> Optional[dict[str, Any]]:
        """
        Получение карточки должника по его первичному ключу.
        """
        with self._lock, self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM Debtors WHERE id = ?;", (debtor_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def delete_debtor(self, debtor_id: int) -> bool:
        """
        Удаление записи должника по идентификатору.
        """
        with self._lock, self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM Debtors WHERE id = ?;", (debtor_id,))
            conn.commit()
            return cursor.rowcount > 0

