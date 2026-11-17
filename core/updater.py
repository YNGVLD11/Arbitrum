import os
import sys
import json
import urllib.request
import subprocess
import tempfile
from PySide6.QtCore import QObject, Signal, QThread

CURRENT_VERSION = "v1.3.0"
GITHUB_REPO = "YNGVLD11/Arbitrum"
API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"


class CheckUpdateThread(QThread):
    """Фоновый поток проверки наличия обновления на GitHub."""
    check_finished = Signal(bool, str, str, str)  # has_update, new_version, release_notes, download_url
    check_failed = Signal(str)

    def run(self):
        try:
            req = urllib.request.Request(API_URL, headers={"User-Agent": "Arbitrum-App"})
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status != 200:
                    self.check_failed.emit(f"Сервер вернул код {response.status}")
                    return
                data = json.loads(response.read().decode("utf-8"))

            tag_name = data.get("tag_name", "").strip()
            body = data.get("body", "Описание обновления отсутствует.")

            # Search for attached .exe asset
            download_url = ""
            for asset in data.get("assets", []):
                name = asset.get("name", "").lower()
                if name.endswith(".exe"):
                    download_url = asset.get("browser_download_url", "")
                    break

            # Compare versions
            cur_clean = CURRENT_VERSION.lstrip("v").strip()
            new_clean = tag_name.lstrip("v").strip()

            has_update = False
            if new_clean and new_clean != cur_clean:
                # Basic tuple comparison: 1.3.0 > 1.2.0
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
    """Фоновый поток скачивания нового исполняемого файла с прогрессом."""
    progress = Signal(int)  # 0 to 100
    download_finished = Signal(str)  # temp_file_path
    download_failed = Signal(str)

    def __init__(self, download_url: str):
        super().__init__()
        self.download_url = download_url

    def run(self):
        try:
            temp_dir = tempfile.gettempdir()
            target_path = os.path.join(temp_dir, "arbitrum_new_version.exe")

            req = urllib.request.Request(self.download_url, headers={"User-Agent": "Arbitrum-App"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                total_size = int(resp.headers.get("content-length", 0))
                downloaded = 0
                block_size = 65536

                with open(target_path, "wb") as f:
                    while True:
                        buffer = resp.read(block_size)
                        if not buffer:
                            break
                        downloaded += len(buffer)
                        f.write(buffer)
                        if total_size > 0:
                            percent = int((downloaded / total_size) * 100)
                            self.progress.emit(percent)

            self.progress.emit(100)
            self.download_finished.emit(target_path)
        except Exception as e:
            self.download_failed.emit(str(e))


def restart_and_replace(new_exe_path: str):
    """
    Запускает фоновый батник для замены старого exe на новый и перезапуска.
    Работает как в скомпилированном виде, так и корректно сообщает в dev-режиме.
    """
    if not getattr(sys, "frozen", False):
        # We are running from source (.py), not frozen exe
        raise RuntimeError("Приложение запущено из исходного кода Python. Обновление .exe доступно только для скомпилированной версии.")

    current_exe = os.path.abspath(sys.argv[0])
    bat_content = f"""@echo off
chcp 65001 > nul
echo Ожидание завершения работы приложения...
timeout /t 2 /nobreak > nul
echo Замена файла...
move /y "{new_exe_path}" "{current_exe}"
echo Запуск обновленного приложения...
start "" "{current_exe}"
del "%~f0"
"""
    temp_dir = tempfile.gettempdir()
    bat_path = os.path.join(temp_dir, "arbitrum_updater.bat")
    with open(bat_path, "w", encoding="cp866") as f:
        f.write(bat_content)

    subprocess.Popen(
        ["cmd.exe", "/c", bat_path],
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    )
    sys.exit(0)
