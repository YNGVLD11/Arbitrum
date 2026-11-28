import os
import sys
import re
import html
import json
import urllib.request
import subprocess
import tempfile
from PySide6.QtCore import QObject, Signal, QThread
from PySide6.QtWidgets import QApplication

CURRENT_VERSION = "v1.5.0"
GITHUB_REPO = "YNGVLD11/Arbitrum"
LATEST_RELEASE_WEB_URL = f"https://github.com/{GITHUB_REPO}/releases/latest"
API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"


class CheckUpdateThread(QThread):
    """
    Фоновый поток проверки наличия обновления на GitHub.
    Использует прямой веб-редирект releases/latest без лимитов GitHub API (403 rate limit).
    При необходимости делает fallback на API.
    """
    check_finished = Signal(bool, str, str, str)  # has_update, new_version, release_notes, download_url
    check_failed = Signal(str)

    def run(self):
        try:
            tag_name = ""
            body = ""
            download_url = ""

            # 1. Попытка через веб-страницу релиза (нет лимитов по IP)
            try:
                req = urllib.request.Request(
                    LATEST_RELEASE_WEB_URL,
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
                )
                with urllib.request.urlopen(req, timeout=8) as response:
                    final_url = response.geturl()
                    tag_candidate = final_url.rstrip("/").split("/")[-1].strip()
                    if tag_candidate and tag_candidate != "releases" and tag_candidate != "latest":
                        tag_name = tag_candidate
                        # Приоритетно ищем инсталлятор ArbitrumSetup.exe
                        download_url = f"https://github.com/{GITHUB_REPO}/releases/download/{tag_name}/ArbitrumSetup.exe"
                        page_html = response.read().decode("utf-8", errors="ignore")
                        m = re.search(r'class="markdown-body[^>]*>(.*?)</div>', page_html, re.DOTALL)
                        if m:
                            clean = re.sub(r'<[^>]+>', '', m.group(1))
                            body = html.unescape(clean).strip()
            except Exception:
                tag_name = ""

            # 2. Fallback через GitHub REST API, если веб-запрос не сработал
            if not tag_name:
                api_req = urllib.request.Request(API_URL, headers={"User-Agent": "Arbitrum-App"})
                with urllib.request.urlopen(api_req, timeout=6) as response:
                    if response.status == 200:
                        data = json.loads(response.read().decode("utf-8"))
                        tag_name = data.get("tag_name", "").strip()
                        body = data.get("body", "Описание обновления отсутствует.")
                        for asset in data.get("assets", []):
                            aname = asset.get("name", "").lower()
                            if aname == "arbitrumsetup.exe" or "setup" in aname:
                                download_url = asset.get("browser_download_url", "")
                                break
                            elif aname.endswith(".exe") and not download_url:
                                download_url = asset.get("browser_download_url", "")

            if not tag_name:
                self.check_failed.emit("Не удалось получить информацию о последней версии.")
                return

            if not body:
                body = "Доступна новая версия программы."

            # Сравнение версий
            cur_clean = CURRENT_VERSION.lstrip("v").strip()
            new_clean = tag_name.lstrip("v").strip()

            has_update = False
            if new_clean and new_clean != cur_clean:
                try:
                    cur_parts = [int(p) for p in cur_clean.split(".")]
                    new_parts = [int(p) for p in new_clean.split(".")]
                    if new_parts > cur_parts:
                        has_update = True
                except Exception:
                    has_update = (new_clean != cur_clean)

            self.check_finished.emit(has_update, tag_name, body, download_url)

        except Exception as e:
            self.check_failed.emit(str(e))


class DownloadUpdateThread(QThread):
    """
    Фоновый поток скачивания нового исполняемого файла с увеличенным буфером.
    Передает прогресс в процентах, скачанных МБ и общем размере МБ.
    """
    progress = Signal(int, float, float)  # percent (0..100), downloaded_mb, total_mb
    download_finished = Signal(str)  # final_file_path
    download_failed = Signal(str)

    def __init__(self, download_url: str):
        super().__init__()
        self.download_url = download_url

    def run(self):
        try:
            temp_dir = tempfile.gettempdir()
            target_path = os.path.join(temp_dir, "arbitrum_new_version.exe")
            part_path = target_path + ".part"

            # Очищаем старые остаточные файлы
            for p in (part_path, target_path):
                if os.path.exists(p):
                    try:
                        os.remove(p)
                    except Exception:
                        pass

            req = urllib.request.Request(
                self.download_url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                total_size = int(resp.headers.get("content-length", 0))
                total_mb = round(total_size / (1024 * 1024), 1) if total_size > 0 else 0.0
                downloaded = 0
                block_size = 524288  # 512 КБ для быстрой потоковой загрузки

                with open(part_path, "wb") as f:
                    while True:
                        buffer = resp.read(block_size)
                        if not buffer:
                            break
                        downloaded += len(buffer)
                        f.write(buffer)
                        dl_mb = round(downloaded / (1024 * 1024), 1)
                        if total_size > 0:
                            percent = int((downloaded / total_size) * 100)
                            self.progress.emit(min(percent, 99), dl_mb, total_mb)
                        else:
                            self.progress.emit(0, dl_mb, 0.0)

            # Проверка целостности файла
            if total_size > 0 and downloaded < total_size:
                if os.path.exists(part_path):
                    try:
                        os.remove(part_path)
                    except Exception:
                        pass
                raise RuntimeError(f"Файл загружен не полностью ({downloaded} из {total_size} байт).")

            # Переименовываем проверенный .part в целевой .exe
            if os.path.exists(target_path):
                try:
                    os.remove(target_path)
                except Exception:
                    pass
            os.replace(part_path, target_path)

            self.progress.emit(100, total_mb, total_mb)
            self.download_finished.emit(target_path)
        except Exception as e:
            self.download_failed.emit(str(e))


def restart_and_replace(new_exe_path: str):
    """
    Применяет скачанное обновление:
    1. Если скачан установщик (ArbitrumSetup.exe) — запускает его в абсолютно тихом
       фоновом режиме (/VERYSILENT /SUPPRESSMSGBOXES /NORESTART), который сам штатно
       обновляет файлы и запускает приложение.
    2. Если скачан бинарник exe — использует нативный updater.exe.
    """
    if not getattr(sys, "frozen", False):
        raise RuntimeError("Приложение запущено из исходного кода Python. Обновление доступно только для скомпилированной версии.")

    current_exe = os.path.abspath(sys.argv[0])
    current_pid = os.getpid()

    # Снимаем метку Zone.Identifier (Mark-of-the-Web)
    try:
        import ctypes
        ctypes.windll.kernel32.DeleteFileW(new_exe_path + ":Zone.Identifier")
    except Exception:
        pass

    # Проверяем, является ли файл инсталлятором Inno Setup
    is_installer = "setup" in os.path.basename(new_exe_path).lower()

    if is_installer:
        # Запускаем Inno Setup инсталлятор в тихом режиме
        # /VERYSILENT — без окон мастера
        # /SUPPRESSMSGBOXES — без всплывающих диалогов
        # /NORESTART — без перезагрузки системы
        flags = 0x08000008 if os.name == "nt" else 0  # DETACHED_PROCESS | CREATE_NO_WINDOW
        subprocess.Popen(
            [new_exe_path, "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/CLOSEAPPLICATIONS", "/RESTARTAPPLICATIONS"],
            creationflags=flags,
            close_fds=True
        )
    else:
        # Нативный C# updater
        temp_dir = tempfile.gettempdir()
        updater_exe = os.path.join(temp_dir, "arbitrum_updater_native.exe")
        base_dir = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        source_updater = os.path.join(base_dir, "assets", "updater.exe")

        if os.path.exists(source_updater):
            import shutil
            shutil.copyfile(source_updater, updater_exe)

        flags = 0x08000008 if os.name == "nt" else 0
        subprocess.Popen(
            [updater_exe, str(current_pid), new_exe_path, current_exe],
            creationflags=flags,
            close_fds=True
        )

    # Корректно закрываем приложение
    app = QApplication.instance()
    if app:
        app.closeAllWindows()
        app.quit()
    sys.exit(0)
