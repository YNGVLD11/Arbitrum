import sys
import os
import ctypes

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set explicit Windows AppUserModelID so the taskbar displays the custom icon
try:
    myappid = "arbitr.report.builder.1.0"
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except Exception:
    pass

from PySide6.QtCore import Qt, QRect
from PySide6.QtWidgets import QApplication, QSplashScreen
from PySide6.QtGui import QFontDatabase, QFont, QPixmap, QPainter, QColor
from ui.themes import get_app_icon
from ui.main_window import MainWindow


def create_splash_screen(app_icon) -> QSplashScreen:
    """Создает компактный аккуратный экран загрузки с логотипом приложения."""
    w, h = 340, 200
    pix = QPixmap(w, h)
    pix.fill(Qt.transparent)

    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.SmoothPixmapTransform)

    # Белая карточка со скругленными углами и легкой рамкой
    p.setBrush(QColor("#FFFFFF"))
    p.setPen(QColor("#E2E8F0"))
    p.drawRoundedRect(QRect(1, 1, w - 2, h - 2), 16, 16)

    # Иконка приложения
    if not app_icon.isNull():
        icon_pix = app_icon.pixmap(56, 56)
        p.drawPixmap((w - 56) // 2, 28, icon_pix)

    # Название
    p.setPen(QColor("#0F172A"))
    p.setFont(QFont("Inter", 16, QFont.Bold))
    p.drawText(QRect(0, 96, w, 28), Qt.AlignCenter, "Арбитрум")

    # Подзаголовок
    p.setPen(QColor("#64748B"))
    p.setFont(QFont("Inter", 10, QFont.Normal))
    p.drawText(QRect(0, 126, w, 20), Qt.AlignCenter, "Автоматизация работы арбитражного управляющего")

    # Статус
    p.setPen(QColor("#94A3B8"))
    p.setFont(QFont("Inter", 9, QFont.Normal))
    p.drawText(QRect(0, 154, w, 18), Qt.AlignCenter, "Загрузка компонентов...")

    p.end()

    splash = QSplashScreen(pix, Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
    splash.setAttribute(Qt.WA_TranslucentBackground)
    return splash


def load_application_fonts():
    """Загружает встроенные шрифты Inter, если они доступны."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    fonts_dir = os.path.join(base_dir, "assets", "fonts")
    if os.path.exists(fonts_dir):
        for font_file in os.listdir(fonts_dir):
            if font_file.lower().endswith((".ttf", ".otf")):
                QFontDatabase.addApplicationFont(os.path.join(fonts_dir, font_file))


def main():
    # Enable High DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("ArbitrReportBuilder")
    app.setApplicationDisplayName("Арбитрум")
    app.setOrganizationName("ArbitrTools")

    # Load custom fonts (Inter)
    load_application_fonts()
    # Set default application font to Inter if available, fallback to Segoe UI
    default_font = QFont("Inter")
    default_font.setStyleHint(QFont.SansSerif)
    app.setFont(default_font)

    # Set application icon (inherited by all windows and taskbar)
    icon = get_app_icon()
    if not icon.isNull():
        app.setWindowIcon(icon)

    # Show Splash Screen during components initialization
    splash = create_splash_screen(icon)
    splash.show()
    app.processEvents()

    window = MainWindow()
    if not icon.isNull():
        window.setWindowIcon(icon)
    window.show()
    splash.finish(window)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
