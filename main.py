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
from ui.themes import get_app_icon
from ui.main_window import MainWindow


def main():
    # Enable High DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("ArbitrReportBuilder")
    app.setApplicationDisplayName("Арбитум")
    app.setOrganizationName("ArbitrTools")

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
