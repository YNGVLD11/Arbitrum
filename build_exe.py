import os
import sys
import subprocess

def build():
    print("=== Сборка автономного EXE для Windows ===")
    project_dir = os.path.dirname(os.path.abspath(__file__))
    main_py = os.path.join(project_dir, "main.py")
    dist_dir = os.path.join(project_dir, "dist")
    build_dir = os.path.join(project_dir, "build")
    ico_path = os.path.join(project_dir, "assets", "app_icon.ico")
    assets_dir = os.path.join(project_dir, "assets")

    cmd = [
        sys.executable,
        "-m", "PyInstaller",
        "--noconsole",
        "--onefile",
        "--clean",
        "--name=Арбитрум",
        f"--icon={ico_path}",
        f"--distpath={dist_dir}",
        f"--workpath={build_dir}",
        f"--add-data={assets_dir};assets",
        f"--add-data={os.path.join(project_dir, 'ui')};ui",
        f"--add-data={os.path.join(project_dir, 'core')};core",
        "--exclude-module=PyQt6",
        "--exclude-module=PyQt5",
        "--hidden-import=pymorphy3",
        "--hidden-import=pymorphy3_dicts_ru",
        "--collect-all=pymorphy3_dicts_ru",
        main_py
    ]

    print("Запуск PyInstaller с иконкой:", ico_path)
    ret = subprocess.run(cmd)
    if ret.returncode == 0:
        exe_path = os.path.join(dist_dir, "Арбитрум.exe")
        print(f"\n[УСПЕХ] Автономный EXE собран с иконкой: {exe_path}")
    else:
        print("\n[ОШИБКА] Сборка завершилась с ошибкой.")

if __name__ == "__main__":
    build()
