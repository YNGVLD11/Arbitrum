import os
import sqlite3
import threading
from typing import Optional, Any


class DatabaseManager:
    """
    Управление локальной реляционной базой данных SQLite для хранения сведений
    о должниках, календарных событиях и прикрепленных файлах.
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

            # Таблица календарных событий
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS Calendar_Events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    debtor_id INTEGER,
                    event_date DATE NOT NULL,
                    description TEXT,
                    is_system BOOLEAN DEFAULT 0,
                    FOREIGN KEY (debtor_id) REFERENCES Debtors(id) ON DELETE SET NULL
                );
            """)

            # Таблица файлов
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS Files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    debtor_id INTEGER,
                    event_id INTEGER,
                    file_path TEXT NOT NULL,
                    FOREIGN KEY (debtor_id) REFERENCES Debtors(id) ON DELETE SET NULL,
                    FOREIGN KEY (event_id) REFERENCES Calendar_Events(id) ON DELETE SET NULL
                );
            """)

            # Таблица заметок дня
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS Day_Notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    debtor_id INTEGER,
                    note_date DATE NOT NULL,
                    note_text TEXT,
                    FOREIGN KEY (debtor_id) REFERENCES Debtors(id) ON DELETE CASCADE,
                    UNIQUE(debtor_id, note_date)
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

    # -------------------------------------------------------------------------
    # CRUD: Календарные события (Calendar_Events)
    # -------------------------------------------------------------------------

    def add_event(
        self,
        event_date: str,
        description: str,
        debtor_id: Optional[int] = None,
        is_system: bool = False
    ) -> int:
        """
        Создание календарного события или задачи.
        """
        with self._lock, self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO Calendar_Events (debtor_id, event_date, description, is_system)
                VALUES (?, ?, ?, ?);
            """, (debtor_id, event_date, description.strip(), 1 if is_system else 0))
            conn.commit()
            return int(cursor.lastrowid)

    def get_events_for_date(
        self,
        event_date: str,
        debtor_id: Optional[int] = None
    ) -> list[dict[str, Any]]:
        """
        Получение списка событий и задач на указанную дату.
        """
        with self._lock, self._get_connection() as conn:
            cursor = conn.cursor()
            if debtor_id is not None:
                cursor.execute("""
                    SELECT * FROM Calendar_Events
                    WHERE event_date = ? AND (debtor_id = ? OR debtor_id IS NULL)
                    ORDER BY is_system DESC, id ASC;
                """, (event_date, debtor_id))
            else:
                cursor.execute("""
                    SELECT * FROM Calendar_Events
                    WHERE event_date = ?
                    ORDER BY is_system DESC, id ASC;
                """, (event_date,))
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    def delete_event(self, event_id: int) -> bool:
        """
        Удаление календарного события по первичному ключу.
        """
        with self._lock, self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM Calendar_Events WHERE id = ?;", (event_id,))
            conn.commit()
            return cursor.rowcount > 0

    def ensure_default_system_events(
        self,
        event_date: str,
        debtor_id: Optional[int] = None
    ) -> list[dict[str, Any]]:
        """
        Гарантирует наличие типовых системных задач на указанную дату.
        """
        existing = self.get_events_for_date(event_date, debtor_id)
        if not existing:
            default_tasks = [
                "Публикация сведений в ЕФРСБ",
                "Направление запросов в государственные ведомства",
                "Проверка входящей корреспонденции и ответов банков",
                "Контроль поступлений на основной счет должника"
            ]
            for task in default_tasks:
                self.add_event(
                    event_date=event_date,
                    description=task,
                    debtor_id=debtor_id,
                    is_system=True
                )
            existing = self.get_events_for_date(event_date, debtor_id)
        return existing

    # -------------------------------------------------------------------------
    # CRUD: Файлы (Files)
    # -------------------------------------------------------------------------

    def save_file(
        self,
        file_path: str,
        event_date: str,
        debtor_id: Optional[int] = None,
        event_id: Optional[int] = None
    ) -> int:
        """
        Сохранение пути к файлу с привязкой к дате и должнику.
        Если событие не указано, создается связующее событие дня.
        """
        with self._lock, self._get_connection() as conn:
            cursor = conn.cursor()

            target_event_id = event_id
            if target_event_id is None:
                cursor.execute("""
                    SELECT id FROM Calendar_Events
                    WHERE event_date = ? AND (debtor_id = ? OR (debtor_id IS NULL AND ? IS NULL))
                    ORDER BY id ASC LIMIT 1;
                """, (event_date, debtor_id, debtor_id))
                found_event = cursor.fetchone()
                if found_event:
                    target_event_id = found_event["id"]
                else:
                    cursor.execute("""
                        INSERT INTO Calendar_Events (debtor_id, event_date, description, is_system)
                        VALUES (?, ?, 'Материалы дня', 1);
                    """, (debtor_id, event_date))
                    target_event_id = cursor.lastrowid

            cursor.execute("""
                INSERT INTO Files (debtor_id, event_id, file_path)
                VALUES (?, ?, ?);
            """, (debtor_id, target_event_id, file_path))
            conn.commit()
            return int(cursor.lastrowid)

    def get_files_for_date(
        self,
        event_date: str,
        debtor_id: Optional[int] = None
    ) -> list[dict[str, Any]]:
        """
        Получение всех файлов, привязанных к конкретной дате и должнику.
        """
        with self._lock, self._get_connection() as conn:
            cursor = conn.cursor()
            if debtor_id is not None:
                cursor.execute("""
                    SELECT f.id, f.debtor_id, f.event_id, f.file_path, e.event_date
                    FROM Files f
                    INNER JOIN Calendar_Events e ON f.event_id = e.id
                    WHERE e.event_date = ? AND (f.debtor_id = ? OR f.debtor_id IS NULL)
                    ORDER BY f.id ASC;
                """, (event_date, debtor_id))
            else:
                cursor.execute("""
                    SELECT f.id, f.debtor_id, f.event_id, f.file_path, e.event_date
                    FROM Files f
                    INNER JOIN Calendar_Events e ON f.event_id = e.id
                    WHERE e.event_date = ?
                    ORDER BY f.id ASC;
                """, (event_date,))
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    def delete_file(self, file_id: int) -> bool:
        """
        Удаление записи о файле из базы данных по идентификатору.
        """
        with self._lock, self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM Files WHERE id = ?;", (file_id,))
            conn.commit()
            return cursor.rowcount > 0

    # -------------------------------------------------------------------------
    # Заметки дня (Day_Notes)
    # -------------------------------------------------------------------------

    def save_day_note(
        self,
        event_date: str,
        note_text: str,
        debtor_id: Optional[int] = None
    ) -> None:
        """
        Сохранение текста ежедневной заметки с привязкой к дате и должнику.
        """
        with self._lock, self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO Day_Notes (debtor_id, note_date, note_text)
                VALUES (?, ?, ?)
                ON CONFLICT(debtor_id, note_date) DO UPDATE SET note_text = excluded.note_text;
            """, (debtor_id, event_date, note_text))
            conn.commit()

    def get_day_note(
        self,
        event_date: str,
        debtor_id: Optional[int] = None
    ) -> str:
        """
        Загрузка текста ежедневной заметки на выбранную дату.
        """
        with self._lock, self._get_connection() as conn:
            cursor = conn.cursor()
            if debtor_id is not None:
                cursor.execute("""
                    SELECT note_text FROM Day_Notes
                    WHERE note_date = ? AND debtor_id = ?;
                """, (event_date, debtor_id))
            else:
                cursor.execute("""
                    SELECT note_text FROM Day_Notes
                    WHERE note_date = ? AND debtor_id IS NULL;
                """, (event_date,))
            row = cursor.fetchone()
            return str(row["note_text"]) if row and row["note_text"] else ""
