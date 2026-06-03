import os
import sys
import json
from PyQt6.QtWidgets import (QApplication, QMainWindow, QPushButton, 
                             QVBoxLayout, QHBoxLayout, QWidget, 
                             QListWidget, QPlainTextEdit, QLabel, 
                             QDialog, QFileDialog, QLineEdit)
from PyQt6.QtCore import QProcess


class ConfigDialog(QDialog):
    """Ventana emergente para la configuración del launcher."""
    def __init__(self, ruta_actual, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configuración")
        self.resize(500, 150)
        
        self.ruta_seleccionada = ruta_actual

        # Componentes
        self.lbl_info = QLabel("Ruta de la carpeta de Instancias:")
        self.txt_ruta = QLineEdit(self.ruta_seleccionada)
        self.txt_ruta.setReadOnly(True)
        
        self.btn_buscar = QPushButton("Examinar...")
        self.btn_guardar = QPushButton("Guardar")
        self.btn_cancelar = QPushButton("Cancelar")

        # Layouts
        layout_ruta = QHBoxLayout()
        layout_ruta.addWidget(self.txt_ruta)
        layout_ruta.addWidget(self.btn_buscar)

        layout_botones = QHBoxLayout()
        layout_botones.addStretch()
        layout_botones.addWidget(self.btn_guardar)
        layout_botones.addWidget(self.btn_cancelar)

        layout_principal = QVBoxLayout()
        layout_principal.addWidget(self.lbl_info)
        layout_principal.addLayout(layout_ruta)
        layout_principal.addLayout(layout_botones)
        self.setLayout(layout_principal)

        # Eventos
        self.btn_buscar.clicked.connect(self.seleccionar_carpeta)
        self.btn_guardar.clicked.connect(self.accept)
        self.btn_cancelar.clicked.connect(self.reject)

    def seleccionar_carpeta(self):
        # Abrir el selector de carpetas nativo del sistema
        carpeta = QFileDialog.getExistingDirectory(self, "Seleccionar Carpeta de Instancias", self.ruta_seleccionada)
        if carpeta:
            self.ruta_seleccionada = carpeta
            self.txt_ruta.setText(carpeta)


class ServerLauncher(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Minecraft Server Launcher")
        self.resize(950, 550)

        # Archivo donde se guardará la configuración
        self.ARCHIVO_CONFIG = os.path.join(os.path.dirname(__file__), "config.json")
        self.ruta_instancias = ""
        
        # Cargar configuración inicial
        self.cargar_configuracion()

        # --- COMPONENTES DE LA INTERFAZ ---
        self.lbl_instancias = QLabel("Selecciona un Servidor:")
        self.lista_servidores = QListWidget()
        
        self.btn_iniciar = QPushButton("Iniciar Servidor Seleccionado")
        self.btn_config = QPushButton("⚙️ Configuración")
        
        self.consola = QPlainTextEdit()
        self.consola.setReadOnly(True)
        self.consola.setPlaceholderText("La consola del servidor se mostrará aquí...")

        # --- DISEÑO (LAYOUT) ---
        layout_izquierdo = QVBoxLayout()
        layout_izquierdo.addWidget(self.lbl_instancias)
        layout_izquierdo.addWidget(self.lista_servidores)
        layout_izquierdo.addWidget(self.btn_iniciar)
        layout_izquierdo.addWidget(self.btn_config) # Botón de configuración abajo a la izquierda

        layout_derecho = QVBoxLayout()
        layout_derecho.addWidget(QLabel("Consola en Tiempo Real:"))
        layout_derecho.addWidget(self.consola)

        layout_principal = QHBoxLayout()
        layout_principal.addLayout(layout_izquierdo, stretch=1)
        layout_principal.addLayout(layout_derecho, stretch=2)

        container = QWidget()
        container.setLayout(layout_principal)
        self.setCentralWidget(container)

        # --- CONTROL DE PROCESOS ---
        self.proceso_server = QProcess(self)
        self.instancia_actual = None

        # --- SEÑALES / EVENTOS ---
        self.btn_iniciar.clicked.connect(self.controlar_servidor)
        self.btn_config.clicked.connect(self.abrir_configuracion)
        self.proceso_server.readyReadStandardOutput.connect(self.leer_consola)
        self.proceso_server.finished.connect(self.servidor_terminado)

        # Escanear carpetas por primera vez
        self.cargar_instancias()

    def cargar_configuracion(self):
        """Lee el archivo JSON de configuración. Si no existe, crea uno por defecto."""
        if os.path.exists(self.ARCHIVO_CONFIG):
            try:
                with open(self.ARCHIVO_CONFIG, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.ruta_instancias = data.get("ruta_instancias", "")
            except Exception:
                self.ruta_instancias = ""
        
        # Si no hay ruta válida guardada, usar una carpeta '/instancias' por defecto al lado del script
        if not self.ruta_instancias or not os.path.exists(self.ruta_instancias):
            self.ruta_instancias = os.path.join(os.path.dirname(__file__), "instancias")
            if not os.path.exists(self.ruta_instancias):
                os.makedirs(self.ruta_instancias)
            self.guardar_configuracion()

    def guardar_configuracion(self):
        """Guarda la ruta actual en el archivo JSON."""
        data = {"ruta_instancias": self.ruta_instancias}
        with open(self.ARCHIVO_CONFIG, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    def abrir_configuracion(self):
        """Abre el diálogo de configuración y actualiza la ruta si se guarda."""
        dialogo = ConfigDialog(self.ruta_instancias, self)
        if dialogo.exec() == QDialog.DialogCode.Accepted:
            self.ruta_instancias = dialogo.ruta_seleccionada
            self.guardar_configuracion()
            self.consola.appendPlainText(f"📁 Nueva carpeta de instancias configurada: {self.ruta_instancias}")
            self.cargar_instancias()

    def cargar_instancias(self):
        """Escanea la carpeta configurada y actualiza la lista."""
        self.lista_servidores.clear()
        if os.path.exists(self.ruta_instancias):
            try:
                carpetas = [f for f in os.listdir(self.ruta_instancias) if os.path.isdir(os.path.join(self.ruta_instancias, f))]
                self.lista_servidores.addItems(carpetas)
            except Exception as e:
                self.consola.appendPlainText(f"❌ Error al leer la carpeta: {e}")
        
        if self.lista_servidores.count() == 0:
            self.consola.appendPlainText("⚠️ La carpeta actual está vacía o no es válida. Configura una ruta con servidores.")

    def controlar_servidor(self):
        if self.proceso_server.state() == QProcess.ProcessState.NotRunning:
            item_seleccionado = self.lista_servidores.currentItem()
            
            if not item_seleccionado:
                self.consola.appendPlainText("❌ Por favor, selecciona un servidor de la lista.")
                return

            nombre_carpeta = item_seleccionado.text()
            ruta_servidor = os.path.join(self.ruta_instancias, nombre_carpeta)
            ruta_jar = os.path.join(ruta_servidor, "server.jar")

            if not os.path.exists(ruta_jar):
                self.consola.appendPlainText(f"❌ No se encontró 'server.jar' en:\n {ruta_servidor}")
                return

            self.instancia_actual = nombre_carpeta
            self.consola.clear()
            self.consola.appendPlainText(f"🚀 Iniciando instancia: {nombre_carpeta}...\n")

            self.proceso_server.setWorkingDirectory(ruta_servidor)

            comando = "java"
            argumentos = ["-Xmx2G", "-Xms1G", "-jar", "server.jar", "nogui"]

            self.lista_servidores.setEnabled(False)
            self.btn_config.setEnabled(False) # Bloquear config mientras corre el sv
            self.proceso_server.start(comando, argumentos)
            self.btn_iniciar.setText("Detener Servidor")
        
        else:
            self.consola.appendPlainText("\n🛑 Enviando comando 'stop' al servidor...")
            self.proceso_server.write(b"stop\n")

    def leer_consola(self):
        data = self.proceso_server.readAllStandardOutput().data()
        try:
            texto = data.decode("utf-8")
        except UnicodeDecodeError:
            texto = data.decode("cp1252", errors="replace")
        self.consola.appendPlainText(texto.strip())

    def servidor_terminado(self):
        self.consola.appendPlainText(f"\n✨ Instancia '{self.instancia_actual}' detenida.")
        self.btn_iniciar.setText("Iniciar Servidor Seleccionado")
        self.lista_servidores.setEnabled(True)
        self.btn_config.setEnabled(True)
        self.instancia_actual = None


if __name__ == "__main__":
    app = QApplication(sys.argv)
    ventana = ServerLauncher()
    ventana.show()
    sys.exit(app.exec())