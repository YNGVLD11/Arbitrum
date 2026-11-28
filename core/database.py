import os
import json
import sqlite3
import threading
from typing import Optional, Any, Dict, List


import os
import sys
import json
import shutil
import sqlite3
import tempfile
import threading
import zipfile
import glob
from typing import Optional, Any, Dict, List


def get_default_database_path() -> str:
    """
    Определяет стандартный путь к файлу базы данных arbitrum.db.
    Если приложение запущено в скомпилированном виде (.exe), база сохраняется
    в постоянном каталоге пользователя %APPDATA%/Arbitrum/data/arbitrum.db,
    чтобы данные не зависели от временных папок распаковки PyInstaller (_MEIxxxx).
    В режиме разработки (из исходников) используется локальная папка data/.
    """
    if getattr(sys, "frozen", False):
        appdata = os.environ.get("APPDATA")
        if not appdata:
            appdata = os.path.expanduser("~")
        base_dir = os.path.join(appdata, "Arbitrum")
    else:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    data_dir = os.path.join(base_dir, "data")
    os.makedirs(data_dir, exist_ok=True)
    return os.path.normpath(os.path.join(data_dir, "arbitrum.db"))


def get_regions_json_path() -> str:
    """
    Определяет постоянный путь к справочнику регионов regions.json.
    В скомпилированном виде сохраняется в %APPDATA%/Arbitrum/data/regions.json,
    чтобы пользовательские правки адресов органов и добавленные города сохранялись навсегда.
    Если файл в AppData еще не существует, копирует начальный шаблон из assets/regions.json.
    """
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    bundled_regions = os.path.join(root_dir, "assets", "regions.json")

    if getattr(sys, "frozen", False):
        appdata = os.environ.get("APPDATA")
        if not appdata:
            appdata = os.path.expanduser("~")
        user_data_dir = os.path.join(appdata, "Arbitrum", "data")
        os.makedirs(user_data_dir, exist_ok=True)
        target_path = os.path.normpath(os.path.join(user_data_dir, "regions.json"))

        # Если в AppData файла еще нет, копируем дефолтный из сборки
        if not os.path.exists(target_path) and os.path.exists(bundled_regions):
            try:
                shutil.copyfile(bundled_regions, target_path)
            except Exception:
                return bundled_regions
        return target_path
    else:
        return bundled_regions


class DatabaseManager:
    """
    Управление локальной реляционной базой данных SQLite для хранения картотеки должников.
    """

    def __init__(self, db_path: Optional[str] = None) -> None:
        """
        Инициализация подключения к базе данных SQLite и создание таблиц.
        """
        if db_path is None:
            self.db_path = get_default_database_path()
            self._migrate_legacy_db_if_needed()
        else:
            self.db_path = os.path.normpath(db_path)
            parent_dir = os.path.dirname(self.db_path)
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)

        self._lock = threading.Lock()
        self._init_tables()

    def _migrate_legacy_db_if_needed(self) -> None:
        """
        Автоматический перенос базы данных из предыдущих версий (например, 1.3.0).
        Если база в целевом пути (%APPDATA%/Arbitrum/data/arbitrum.db) ещё не создана
        или пуста (0 байт), проверяются возможные места расположения старой БД:
        1. Временные папки распаковщика PyInstaller: %TEMP%/_MEI*/data/arbitrum.db
        2. Папка data рядом с исполняемым файлом: <exe_dir>/data/arbitrum.db
        3. Локальная папка проекта: <project_root>/data/arbitrum.db
        Если найдена существующая база с записями, она бережно копируется в APPDATA.
        """
        try:
            if os.path.exists(self.db_path) and os.path.getsize(self.db_path) > 0:
                return  # База уже есть и не пустая

            candidates: List[str] = []

            # 1. Поиск во временных каталогах _MEI*
            temp_dir = tempfile.gettempdir()
            mei_pattern = os.path.join(temp_dir, "_MEI*", "data", "arbitrum.db")
            for p in glob.glob(mei_pattern):
                if os.path.isfile(p) and os.path.getsize(p) > 0:
                    candidates.append(os.path.normpath(p))

            # 2. Рядом с исполняемым файлом
            if getattr(sys, "frozen", False) and hasattr(sys, "executable"):
                exe_dir = os.path.dirname(os.path.abspath(sys.executable))
                beside_exe = os.path.join(exe_dir, "data", "arbitrum.db")
                if os.path.isfile(beside_exe) and os.path.getsize(beside_exe) > 0:
                    candidates.append(os.path.normpath(beside_exe))

            # 3. В папке исходников проекта
            script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            project_db = os.path.join(script_dir, "data", "arbitrum.db")
            if os.path.isfile(project_db) and os.path.getsize(project_db) > 0:
                candidates.append(os.path.normpath(project_db))

            # Исключаем целевой путь из кандидатов
            candidates = [c for c in candidates if os.path.normpath(c) != os.path.normpath(self.db_path)]

            if not candidates:
                return

            # Выбираем самый свежий файл по дате модификации
            candidates.sort(key=lambda p: os.path.getmtime(p), reverse=True)
            source_db = candidates[0]

            parent_dir = os.path.dirname(self.db_path)
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)

            shutil.copy2(source_db, self.db_path)
        except Exception:
            pass  # Не блокируем запуск в случае неожиданных проблем с правами

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

    # -------------------------------------------------------------------------
    # Умный импорт и объединение баз данных (Smart Merge)
    # -------------------------------------------------------------------------

    def import_debtors_from_db(self, source_db_path: str) -> Dict[str, int]:
        """
        Импортирует должников из другой базы данных SQLite (или резервной копии).
        Объединяет записи без потери существующих данных:
        - Идентичные должники (по номеру дела или ФИО + СНИЛС / ИНН) определяются как дубликаты.
        - Если у существующего должника в текущей базе какие-то поля пустые,
          а во входящей базе заполнены — они аккуратно дополняются.
        - Новые должники вставляются в картотеку.
        Возвращает словарь со статистикой:
        {'added': int, 'updated': int, 'skipped': int, 'total_source': int}
        """
        if not os.path.isfile(source_db_path):
            raise FileNotFoundError(f"Файл базы данных не найден: {source_db_path}")

        # Проверяем целостность файла источника
        src_conn = sqlite3.connect(source_db_path)
        src_conn.row_factory = sqlite3.Row
        try:
            cur = src_conn.cursor()
            cur.execute("PRAGMA integrity_check;")
            row = cur.fetchone()
            if not row or row[0] != "ok":
                raise ValueError("Файл базы данных поврежден.")

            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='Debtors';")
            if not cur.fetchone():
                raise ValueError("В выбранном файле отсутствует таблица картотеки должников (Debtors).")

            cur.execute("SELECT * FROM Debtors ORDER BY id ASC;")
            source_rows = cur.fetchall()
        finally:
            src_conn.close()

        added = 0
        updated = 0
        skipped = 0

        with self._lock, self._get_connection() as dst_conn:
            cursor = dst_conn.cursor()

            # Загружаем существующие записи для быстрого сопоставления
            cursor.execute("SELECT id, full_name, case_number, snils, inn, passport_data, address, raw_data FROM Debtors;")
            existing_debtors = cursor.fetchall()

            for s in source_rows:
                s_name = (s["full_name"] or "").strip()
                s_case = (s["case_number"] or "").strip()
                s_snils = (s["snils"] or "").strip()
                s_inn = (s["inn"] or "").strip()
                s_pass = (s["passport_data"] or "").strip()
                s_addr = (s["address"] or "").strip()
                s_raw = s["raw_data"]

                if not s_name:
                    continue

                # Ищем совпадение среди существующих должников
                matched_id = None
                matched_row = None

                for ex in existing_debtors:
                    ex_name = (ex["full_name"] or "").strip()
                    ex_case = (ex["case_number"] or "").strip()
                    ex_snils = (ex["snils"] or "").strip()
                    ex_inn = (ex["inn"] or "").strip()

                    # Совпадение 1: по номеру дела
                    if s_case and ex_case and s_case.upper() == ex_case.upper():
                        matched_id = ex["id"]
                        matched_row = ex
                        break

                    # Совпадение 2: по полному ФИО и (СНИЛС или ИНН)
                    if s_name.lower() == ex_name.lower():
                        if (s_snils and ex_snils and s_snils == ex_snils) or \
                           (s_inn and ex_inn and s_inn == ex_inn):
                            matched_id = ex["id"]
                            matched_row = ex
                            break
                        # Если нет СНИЛС и ИНН, но совпадает ФИО и номера дел пустые
                        if not s_case and not ex_case and s_name.lower() == ex_name.lower():
                            matched_id = ex["id"]
                            matched_row = ex
                            break

                if matched_id is not None:
                    # Запись уже существует: проверяем, можно ли дополнить пустые поля
                    fields_to_update = {}
                    if not (matched_row["snils"] or "").strip() and s_snils:
                        fields_to_update["snils"] = s_snils
                    if not (matched_row["inn"] or "").strip() and s_inn:
                        fields_to_update["inn"] = s_inn
                    if not (matched_row["passport_data"] or "").strip() and s_pass:
                        fields_to_update["passport_data"] = s_pass
                    if not (matched_row["address"] or "").strip() and s_addr:
                        fields_to_update["address"] = s_addr
                    if not (matched_row["case_number"] or "").strip() and s_case:
                        fields_to_update["case_number"] = s_case

                    # Слияние raw_data
                    if s_raw:
                        cur_raw_str = matched_row["raw_data"]
                        try:
                            cur_json = json.loads(cur_raw_str) if cur_raw_str else {}
                            new_json = json.loads(s_raw) if s_raw else {}
                            # Дополняем только те ключи, которых не было или они были пустыми
                            merged = False
                            for k, v in new_json.items():
                                if v and not cur_json.get(k):
                                    cur_json[k] = v
                                    merged = True
                            if merged:
                                fields_to_update["raw_data"] = json.dumps(cur_json, ensure_ascii=False)
                        except Exception:
                            pass

                    if fields_to_update:
                        set_clause = ", ".join([f"{k} = ?" for k in fields_to_update.keys()])
                        vals = list(fields_to_update.values()) + [matched_id]
                        cursor.execute(f"UPDATE Debtors SET {set_clause} WHERE id = ?;", vals)
                        updated += 1
                    else:
                        skipped += 1
                else:
                    # Полностью новая запись — добавляем в картотеку
                    cursor.execute("""
                        INSERT INTO Debtors (full_name, case_number, snils, inn, passport_data, address, raw_data)
                        VALUES (?, ?, ?, ?, ?, ?, ?);
                    """, (s_name, s_case, s_snils, s_inn, s_pass, s_addr, s_raw))
                    new_id = int(cursor.lastrowid)
                    added += 1

                    # Добавляем новую запись в локальный кэш existing_debtors
                    cursor.execute("SELECT id, full_name, case_number, snils, inn, passport_data, address, raw_data FROM Debtors WHERE id = ?;", (new_id,))
                    new_row = cursor.fetchone()
                    if new_row:
                        existing_debtors.append(new_row)

            dst_conn.commit()

        return {
            "added": added,
            "updated": updated,
            "skipped": skipped,
            "total_source": len(source_rows)
        }

    # -------------------------------------------------------------------------
    # Резервное копирование и восстановление (Backup & Restore)
    # -------------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """
        Возвращает статистику по базе данных: путь, размер в байтах, количество должников.
        """
        size_bytes = 0
        if os.path.exists(self.db_path):
            try:
                size_bytes = os.path.getsize(self.db_path)
            except Exception:
                size_bytes = 0

        debtor_count = 0
        try:
            with self._lock, self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) AS cnt FROM Debtors;")
                row = cursor.fetchone()
                if row:
                    debtor_count = int(row["cnt"])
        except Exception:
            pass

        return {
            "db_path": self.db_path,
            "size_bytes": size_bytes,
            "debtor_count": debtor_count
        }

    def create_backup(self, zip_filepath: str) -> None:
        """
        Создает резервную копию базы данных SQLite в формате ZIP.
        Используется SQLite Online Backup API для создания целостной непротиворечивой копии,
        даже если в этот момент производятся операции чтения/записи.
        """
        zip_dir = os.path.dirname(os.path.abspath(zip_filepath))
        if zip_dir:
            os.makedirs(zip_dir, exist_ok=True)

        stats = self.get_stats()

        with self._lock:
            # Создаем временный файл через sqlite3 backup API для 100% целостности
            fd, temp_db_path = tempfile.mkstemp(suffix=".db")
            os.close(fd)
            try:
                src_conn = self._get_connection()
                try:
                    bck_conn = sqlite3.connect(temp_db_path)
                    try:
                        src_conn.backup(bck_conn)
                    finally:
                        bck_conn.close()
                finally:
                    src_conn.close()

                with zipfile.ZipFile(zip_filepath, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                    zf.write(temp_db_path, arcname="arbitrum.db")
                    # Добавляем метаданные
                    meta = {
                        "app": "Arbitrum",
                        "debtor_count": stats["debtor_count"],
                        "original_path": self.db_path
                    }
                    zf.writestr("backup_info.json", json.dumps(meta, ensure_ascii=False, indent=2))
            finally:
                if os.path.exists(temp_db_path):
                    try:
                        os.remove(temp_db_path)
                    except Exception:
                        pass

    def export_database_file(self, target_filepath: str) -> None:
        """
        Экспортирует базу данных в виде отдельного файла .db или .sqlite.
        Использует Online Backup API для создания чистой автономной копии.
        """
        target_dir = os.path.dirname(os.path.abspath(target_filepath))
        if target_dir:
            os.makedirs(target_dir, exist_ok=True)

        with self._lock:
            src_conn = self._get_connection()
            try:
                dst_conn = sqlite3.connect(target_filepath)
                try:
                    src_conn.backup(dst_conn)
                finally:
                    dst_conn.close()
            finally:
                src_conn.close()

    def restore_backup(self, zip_filepath: str) -> int:
        """
        Восстанавливает базу данных из резервной копии ZIP.
        Проверяет целостность и наличие таблицы Debtors перед заменой текущей базы.
        Возвращает количество восстановленных записей должников.
        Вызывает ValueError при невалидном архиве или поврежденной БД.
        """
        if not os.path.isfile(zip_filepath):
            raise FileNotFoundError(f"Файл архива не найден: {zip_filepath}")

        with zipfile.ZipFile(zip_filepath, "r") as zf:
            namelist = zf.namelist()
            db_entry = None
            for name in namelist:
                if os.path.basename(name) == "arbitrum.db" or name.endswith(".db"):
                    db_entry = name
                    break
            if not db_entry:
                raise ValueError("В выбранном архиве не найден файл базы данных (arbitrum.db).")

            fd, temp_extracted = tempfile.mkstemp(suffix=".db")
            os.close(fd)
            try:
                with zf.open(db_entry) as src, open(temp_extracted, "wb") as dst:
                    shutil.copyfileobj(src, dst)

                # Проверяем валидность SQLite файла
                test_conn = sqlite3.connect(temp_extracted)
                test_conn.row_factory = sqlite3.Row
                try:
                    cursor = test_conn.cursor()
                    cursor.execute("PRAGMA integrity_check;")
                    row = cursor.fetchone()
                    if not row or row[0] != "ok":
                        raise ValueError("Файл базы данных в архиве поврежден (integrity check failed).")

                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='Debtors';")
                    if not cursor.fetchone():
                        raise ValueError("В базе данных отсутствует таблица должников (Debtors).")

                    cursor.execute("SELECT COUNT(*) AS cnt FROM Debtors;")
                    restored_count = int(cursor.fetchone()["cnt"])
                finally:
                    test_conn.close()

                # Безопасная замена текущей БД
                parent_dir = os.path.dirname(self.db_path)
                if parent_dir:
                    os.makedirs(parent_dir, exist_ok=True)

                with self._lock:
                    # Создаем аварийный backup на случай непредвиденных сбоев
                    if os.path.exists(self.db_path):
                        bak_path = self.db_path + ".bak"
                        try:
                            shutil.copy2(self.db_path, bak_path)
                        except Exception:
                            pass

                    # Перезаписываем файл
                    shutil.copy2(temp_extracted, self.db_path)

                # Инициализируем/обновляем таблицы вне блокировки self._lock (так как _init_tables берет lock сама)
                self._init_tables()

                return restored_count
            finally:
                if os.path.exists(temp_extracted):
                    try:
                        os.remove(temp_extracted)
                    except Exception:
                        pass

    def import_from_archive_or_db(self, file_path: str) -> Dict[str, int]:
        """
        Универсальный импорт картотеки из архива .zip или файла .db / .sqlite.
        Использует логику import_debtors_from_db: если должники уже есть в картотеке,
        дубликаты не плодятся, а лишь дополняются недостающие реквизиты.
        """
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"Файл не найден: {file_path}")

        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".zip":
            with zipfile.ZipFile(file_path, "r") as zf:
                db_entry = None
                for name in zf.namelist():
                    if os.path.basename(name) == "arbitrum.db" or name.endswith(".db") or name.endswith(".sqlite"):
                        db_entry = name
                        break
                if not db_entry:
                    raise ValueError("В архиве не найден файл базы данных SQLite.")

                fd, temp_db = tempfile.mkstemp(suffix=".db")
                os.close(fd)
                try:
                    with zf.open(db_entry) as src, open(temp_db, "wb") as dst:
                        shutil.copyfileobj(src, dst)
                    return self.import_debtors_from_db(temp_db)
                finally:
                    if os.path.exists(temp_db):
                        try:
                            os.remove(temp_db)
                        except Exception:
                            pass
        else:
            return self.import_debtors_from_db(file_path)



