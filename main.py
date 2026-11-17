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

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFontDatabase, QFont
from ui.themes import get_app_icon
from ui.main_window import MainWindow


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

    window = MainWindow()
    if not icon.isNull():
        window.setWindowIcon(icon)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
