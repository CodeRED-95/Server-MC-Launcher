# main.py
import sys
from PyQt6.QtWidgets import QApplication
from launcher import ServerLauncher

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    ventana = ServerLauncher()
    ventana.show()
    
    sys.exit(app.exec())