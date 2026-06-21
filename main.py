# main.py
import os
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from launcher import ServerLauncher

if __name__ == "__main__":
    app = QApplication(sys.argv)
    ruta_icono = os.path.join(os.path.dirname(__file__), "assets", "app_icon.png")
    if os.path.exists(ruta_icono):
        app.setWindowIcon(QIcon(ruta_icono))
    
    # Podrías agregar configuraciones globales de estilos de la App aquí
    ventana = ServerLauncher()
    ventana.show()
    
    sys.exit(app.exec())
