from pathlib import Path
import sys

from PyQt6.QtWidgets import QApplication

from documaster.views.main_window import MainWindow


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("DocuMaster")
    window = MainWindow(Path(__file__).parent)
    window.show()
    sys.exit(app.exec())
