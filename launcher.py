import os
import sys
import json
import struct
from PyQt6.QtWidgets import (QApplication, QMainWindow, QPushButton, 
                             QVBoxLayout, QHBoxLayout, QWidget, 
                             QListWidget, QListWidgetItem, QPlainTextEdit, 
                             QLabel, QDialog, QFileDialog, QLineEdit, QComboBox)
from PyQt6.QtCore import QProcess, QProcessEnvironment, Qt, QSize
from PyQt6.QtGui import QIcon, QPixmap


class ConsoleWindow(QDialog):
    """Ventana independiente para la terminal del servidor."""
    def __init__(self, nombre_instancia, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Terminal del Servidor - {nombre_instancia}")
        self.resize(800, 500)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowMinMaxButtonsHint)

        self.consola = QPlainTextEdit()
        self.consola.setReadOnly(True)
        self.consola.setStyleSheet("""
            QPlainTextEdit {
                background-color: #121212;
                color: #dcdcdc;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 11pt;
            }
        """)
        
        self.input_comando = QLineEdit()
        self.input_comando.setPlaceholderText("Escribe un comando aquí (ej: op mi_usuario) y presiona Enter...")
        self.input_comando.setStyleSheet("""
            QLineEdit { 
                background-color: #1e1e1e; 
                color: #ffffff; 
                border: 1px solid #333333; 
                font-family: 'Consolas', monospace; 
                padding: 6px; 
            }
        """)

        layout = QVBoxLayout()
        layout.addWidget(QLabel(f"Consola activa: {nombre_instancia}"))
        layout.addWidget(self.consola)
        layout.addWidget(self.input_comando)
        self.setLayout(layout)


class ConfigGlobalDialog(QDialog):
    def __init__(self, ruta_instancias, ruta_javas_raiz, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configuración General")
        self.resize(600, 180)
        
        self.ruta_instancias = ruta_instancias
        self.ruta_javas_raiz = ruta_javas_raiz

        self.lbl_instancias = QLabel("Ruta raíz de la carpeta de Instancias:")
        self.txt_instancias = QLineEdit(self.ruta_instancias)
        self.txt_instancias.setReadOnly(True)
        self.btn_buscar_instancias = QPushButton("Examinar...")

        self.lbl_javas_raiz = QLabel("Carpeta raíz de entornos Java (subcarpetas de Java):")
        self.txt_javas_raiz = QLineEdit(self.ruta_javas_raiz)
        self.txt_javas_raiz.setReadOnly(True)
        self.btn_buscar_javas = QPushButton("Examinar...")

        self.btn_guardar = QPushButton("Guardar")
        self.btn_cancelar = QPushButton("Cancelar")

        layout_instancias = QHBoxLayout()
        layout_instancias.addWidget(self.txt_instancias)
        layout_instancias.addWidget(self.btn_buscar_instancias)

        layout_javas = QHBoxLayout()
        layout_javas.addWidget(self.txt_javas_raiz)
        layout_javas.addWidget(self.btn_buscar_javas)

        layout_botones = QHBoxLayout()
        layout_botones.addStretch()
        layout_botones.addWidget(self.btn_guardar)
        layout_botones.addWidget(self.btn_cancelar)

        layout_principal = QVBoxLayout()
        layout_principal.addWidget(self.lbl_instancias)
        layout_principal.addLayout(layout_instancias)
        layout_principal.addSpacing(10)
        layout_principal.addWidget(self.lbl_javas_raiz)
        layout_principal.addLayout(layout_javas)
        layout_principal.addSpacing(15)
        layout_principal.addLayout(layout_botones)
        self.setLayout(layout_principal)

        self.btn_buscar_instancias.clicked.connect(self.seleccionar_instancias)
        self.btn_buscar_javas.clicked.connect(self.seleccionar_carpeta_javas)
        self.btn_guardar.clicked.connect(self.accept)
        self.btn_cancelar.clicked.connect(self.reject)

    def seleccionar_instancias(self):
        carpeta = QFileDialog.getExistingDirectory(self, "Seleccionar Carpeta de Instancias", self.ruta_instancias)
        if carpeta:
            self.ruta_instancias = carpeta
            self.txt_instancias.setText(carpeta)

    def seleccionar_carpeta_javas(self):
        carpeta = QFileDialog.getExistingDirectory(self, "Seleccionar Carpeta de Javas", self.ruta_javas_raiz if self.ruta_javas_raiz else "C:\\")
        if carpeta:
            self.ruta_javas_raiz = carpeta
            self.txt_javas_raiz.setText(carpeta)


class ConfigInstanciaDialog(QDialog):
    def __init__(self, nombre_instancia, ruta_instancia, archivo_actual, java_actual, ruta_javas_raiz, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Configurar Instancia: {nombre_instancia}")
        self.resize(600, 260)
        
        self.ruta_instancia = ruta_instancia
        self.archivo_seleccionado = archivo_actual
        self.java_seleccionado = java_actual
        self.ruta_javas_raiz = ruta_javas_raiz

        self.lbl_info = QLabel("Archivo ejecutable/arranque de la instancia (ej: run.bat):")
        self.txt_archivo = QLineEdit(self.archivo_seleccionado)
        self.txt_archivo.setReadOnly(True)
        self.btn_buscar_archivo = QPushButton("Seleccionar...")

        self.lbl_java = QLabel("Asignación de Java para esta instancia:")
        self.combo_java = QComboBox()

        self.lbl_icon = QLabel("Icono personalizado de la instancia (Opcional - Imagen PNG/JPG):")
        self.txt_icon = QLineEdit()
        self.txt_icon.setReadOnly(True)
        self.btn_buscar_icon = QPushButton("Cambiar Icono...")
        
        ruta_icon_json = os.path.join(self.ruta_instancia, "icon.png")
        if os.path.exists(ruta_icon_json):
            self.txt_icon.setText("icon.png (Personalizado Detectado)")

        self.btn_guardar = QPushButton("Guardar Cambios")
        self.btn_cancelar = QPushButton("Cancelar")

        layout_archivo = QHBoxLayout()
        layout_archivo.addWidget(self.txt_archivo)
        layout_archivo.addWidget(self.btn_buscar_archivo)

        layout_icon = QHBoxLayout()
        layout_icon.addWidget(self.txt_icon)
        layout_icon.addWidget(self.btn_buscar_icon)

        layout_botones = QHBoxLayout()
        layout_botones.addStretch()
        layout_botones.addWidget(self.btn_guardar)
        layout_botones.addWidget(self.btn_cancelar)

        layout_principal = QVBoxLayout()
        layout_principal.addWidget(self.lbl_info)
        layout_principal.addLayout(layout_archivo)
        layout_principal.addSpacing(10)
        layout_principal.addWidget(self.lbl_icon)
        layout_principal.addLayout(layout_icon)
        layout_principal.addSpacing(10)
        layout_principal.addWidget(self.lbl_java)
        layout_principal.addWidget(self.combo_java)
        layout_principal.addSpacing(15)
        layout_principal.addLayout(layout_botones)
        self.setLayout(layout_principal)

        self.btn_buscar_archivo.clicked.connect(self.seleccionar_archivo)
        self.btn_buscar_icon.clicked.connect(self.seleccionar_icono)
        self.btn_guardar.clicked.connect(self.accept)
        self.btn_cancelar.clicked.connect(self.reject)

        self.cargar_combo_javas()

    def seleccionar_archivo(self):
        archivo, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar Ejecutable", self.ruta_instancia, 
            "Ejecutables (*.bat *.jar *.sh);;Todos los archivos (*.*)"
        )
        if archivo:
            self.archivo_seleccionado = os.path.basename(archivo)
            self.txt_archivo.setText(self.archivo_seleccionado)

    def seleccionar_icono(self):
        archivo, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar Icono", "", "Imágenes (*.png *.jpg *.jpeg)"
        )
        if archivo:
            try:
                import shutil
                destino = os.path.join(self.ruta_instancia, "icon.png")
                shutil.copy(archivo, destino)
                self.txt_icon.setText("icon.png (Actualizado)")
            except Exception as e:
                self.txt_icon.setText(f"Error al copiar: {e}")

    def cargar_combo_javas(self):
        self.combo_java.clear()
        self.combo_java.addItem("🤖 Auto-detectar Java necesario (Recomendado)", "AUTO")
        
        if self.ruta_javas_raiz and os.path.exists(self.ruta_javas_raiz):
            try:
                for item in os.listdir(self.ruta_javas_raiz):
                    ruta_sub = os.path.join(self.ruta_javas_raiz, item)
                    if os.path.isdir(ruta_sub):
                        ruta_exe = os.path.join(ruta_sub, "bin", "java.exe")
                        if os.path.exists(ruta_exe):
                            self.combo_java.addItem(f"Forzar: {item}", item)
            except Exception:
                pass
        
        index = self.combo_java.findData(self.java_seleccionado)
        if index != -1:
            self.combo_java.setCurrentIndex(index)


class ServerLauncher(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Minecraft Server Launcher Grid Pro")
        self.resize(900, 600)

        self.ARCHIVO_CONFIG_GLOBAL = os.path.join(os.path.dirname(__file__), "config.json")
        self.ruta_instancias = ""
        self.ruta_javas_raiz = ""
        
        self.cargar_configuracion_global()

        self.lbl_instancias = QLabel("Instancias de Servidores disponibles:")
        self.lbl_instancias.setStyleSheet("font-weight: bold; font-size: 11pt;")
        
        self.lista_servidores = QListWidget()
        self.lista_servidores.setViewMode(QListWidget.ViewMode.IconMode)
        self.lista_servidores.setIconSize(QSize(70, 70))
        self.lista_servidores.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.lista_servidores.setMovement(QListWidget.Movement.Static)
        self.lista_servidores.setSpacing(15)
        self.lista_servidores.setStyleSheet("""
            QListWidget {
                background-color: #1e1e1e;
                color: #ffffff;
                border: 1px solid #2d2d2d;
                border-radius: 6px;
                padding: 10px;
            }
            QListWidget::item {
                background-color: #2a2a2a;
                border-radius: 8px;
                padding: 8px;
                width: 110px;
                height: 120px;
            }
            QListWidget::item:selected {
                background-color: #007acc;
                color: white;
            }
            QListWidget::item:hover {
                background-color: #3a3a3a;
            }
        """)
        
        self.btn_iniciar = QPushButton("🚀 Iniciar Servidor")
        self.btn_config_instancia = QPushButton("🛠️ Configurar Instancia")
        self.btn_config_global = QPushButton("⚙️ Configuración General")
        
        estilo_botones = "QPushButton { padding: 8px; font-size: 10pt; font-weight: bold; }"
        self.btn_iniciar.setStyleSheet(estilo_botones)
        self.btn_config_instancia.setStyleSheet(estilo_botones)
        self.btn_config_global.setStyleSheet(estilo_botones)

        layout_botones = QHBoxLayout()
        layout_botones.addWidget(self.btn_iniciar, stretch=2)
        layout_botones.addWidget(self.btn_config_instancia, stretch=1)
        layout_botones.addWidget(self.btn_config_global, stretch=1)

        layout_principal = QVBoxLayout()
        layout_principal.addWidget(self.lbl_instancias)
        layout_principal.addWidget(self.lista_servidores)
        layout_principal.addLayout(layout_botones)

        container = QWidget()
        container.setLayout(layout_principal)
        self.setCentralWidget(container)

        self.proceso_server = QProcess(self)
        self.instancia_actual = None
        self.proceso_server.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        
        self.ventana_consola = None

        self.btn_iniciar.clicked.connect(self.controlar_servidor)
        self.btn_config_global.clicked.connect(self.abrir_configuracion_global)
        self.btn_config_instancia.clicked.connect(self.abrir_configuracion_instancia)
        self.lista_servidores.currentItemChanged.connect(self.actualizar_estado_botones)
        
        self.proceso_server.readyRead.connect(self.leer_consola)
        self.proceso_server.finished.connect(self.servidor_terminado)

        self.cargar_instancias()

    def cargar_configuracion_global(self):
        if os.path.exists(self.ARCHIVO_CONFIG_GLOBAL):
            try:
                with open(self.ARCHIVO_CONFIG_GLOBAL, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.ruta_instancias = data.get("ruta_instancias", "")
                    self.ruta_javas_raiz = data.get("ruta_javas_raiz", "")
            except Exception:
                pass
        
        if not self.ruta_instancias or not os.path.exists(self.ruta_instancias):
            self.ruta_instancias = os.path.join(os.path.dirname(__file__), "instancias")
            if not os.path.exists(self.ruta_instancias):
                os.makedirs(self.ruta_instancias)
            self.guardar_configuracion_global()

    def guardar_configuracion_global(self):
        data = {"ruta_instancias": self.ruta_instancias, "ruta_javas_raiz": self.ruta_javas_raiz}
        with open(self.ARCHIVO_CONFIG_GLOBAL, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    def obtener_datos_instancia(self, ruta_servidor):
        ruta_json = os.path.join(ruta_servidor, "config_instancia.json")
        archivo = ""
        java_esp = "AUTO"
        if os.path.exists(ruta_json):
            try:
                with open(ruta_json, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    archivo = data.get("archivo_arranque", "")
                    java_esp = data.get("java_especifico", "AUTO")
            except Exception:
                pass
        
        if not archivo:
            for opcion in ["run.bat", "start.bat", "server.jar"]:
                if os.path.exists(os.path.join(ruta_servidor, opcion)):
                    archivo = opcion
                    break
        return archivo, java_esp

    def guardar_datos_instancia(self, ruta_servidor, archivo, java_esp):
        ruta_json = os.path.join(ruta_servidor, "config_instancia.json")
        data = {"archivo_arranque": archivo, "java_especifico": java_esp}
        with open(ruta_json, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    def abrir_configuracion_global(self):
        dialogo = ConfigGlobalDialog(self.ruta_instancias, self.ruta_javas_raiz, self)
        if dialogo.exec() == QDialog.DialogCode.Accepted:
            self.ruta_instancias = dialogo.ruta_instancias
            self.ruta_javas_raiz = dialogo.ruta_javas_raiz
            self.guardar_configuracion_global()
            self.cargar_instancias()

    def abrir_configuracion_instancia(self):
        item = self.lista_servidores.currentItem()
        if not item: return
        
        nombre_carpeta = item.text()
        ruta_servidor = os.path.join(self.ruta_instancias, nombre_carpeta)
        archivo_actual, java_actual = self.obtener_datos_instancia(ruta_servidor)

        dialogo = ConfigInstanciaDialog(nombre_carpeta, ruta_servidor, archivo_actual, java_actual, self.ruta_javas_raiz, self)
        if dialogo.exec() == QDialog.DialogCode.Accepted:
            self.guardar_datos_instancia(ruta_servidor, dialogo.archivo_seleccionado, dialogo.combo_java.currentData())
            self.cargar_instancias()

    def cargar_instancias(self):
        self.lista_servidores.clear()
        if os.path.exists(self.ruta_instancias):
            try:
                for f in os.listdir(self.ruta_instancias):
                    ruta_sub = os.path.join(self.ruta_instancias, f)
                    if os.path.isdir(ruta_sub):
                        item = QListWidgetItem(f)
                        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                        
                        ruta_icon = os.path.join(ruta_sub, "icon.png")
                        if os.path.exists(ruta_icon):
                            item.setIcon(QIcon(ruta_icon))
                        else:
                            item.setIcon(QIcon.fromTheme("folder-remote"))
                        
                        self.lista_servidores.addItem(item)
            except Exception:
                pass
        self.actualizar_estado_botones()

    def actualizar_estado_botones(self):
        tiene_seleccion = self.lista_servidores.currentItem() is not None
        en_ejecucion = self.proceso_server.state() == QProcess.ProcessState.Running
        self.btn_config_instancia.setEnabled(tiene_seleccion and not en_ejecucion)
        self.btn_config_global.setEnabled(not en_ejecucion)
        self.lista_servidores.setEnabled(not en_ejecucion)

    def detectar_version_java_de_jar(self, ruta_jar):
        if not os.path.exists(ruta_jar): return 17
        try:
            import zipfile
            with zipfile.ZipFile(ruta_jar, 'r') as z:
                for name in z.namelist():
                    if name.endswith('.class'):
                        with z.open(name) as f:
                            magic = f.read(4)
                            if magic == b'\xca\xfe\xba\xbe':
                                minor, major = struct.unpack('>HH', f.read(4))
                                mapa = {52: 8, 53: 9, 54: 10, 55: 11, 56: 12, 57: 13, 58: 14, 59: 15, 60: 16, 61: 17, 62: 18, 63: 19, 64: 20, 65: 21, 66: 22}
                                return mapa.get(major, 17)
        except Exception: pass
        return 17

    def escanear_versiones_en_carpeta_javas(self):
        javas_disponibles = {}
        if not self.ruta_javas_raiz or not os.path.exists(self.ruta_javas_raiz): return javas_disponibles
        for item in os.listdir(self.ruta_javas_raiz):
            ruta_exe = os.path.join(self.ruta_javas_raiz, item, "bin", "java.exe")
            if os.path.exists(ruta_exe):
                v = self.obtener_version_de_binario(ruta_exe)
                if v: javas_disponibles[v] = ruta_exe
        return javas_disponibles

    def obtener_version_de_binario(self, ruta_exe):
        p = QProcess()
        p.start(ruta_exe, ["-version"])
        p.waitForFinished(1000)
        output = str(p.readAllStandardError())
        if "1.8.0" in output or '"1.8' in output: return 8
        for v in [11, 16, 17, 18, 19, 20, 21, 22]:
            if f'"{v}.' in output or f' {v}.' in output: return v
        return None

    def seleccionar_mejor_java(self, ruta_servidor):
        version_requerida = 17
        jar_principal = os.path.join(ruta_servidor, "server.jar")
        if not os.path.exists(jar_principal):
            for f in os.listdir(ruta_servidor):
                if f.endswith(".jar") and ("forge" in f or "fabric" in f or "paper" in f or "server" in f):
                    jar_principal = os.path.join(ruta_servidor, f)
                    break
        if os.path.exists(jar_principal):
            version_requerida = self.detectar_version_java_de_jar(jar_principal)
        diccionario_javas = self.escanear_versiones_en_carpeta_javas()
        if version_requerida in diccionario_javas: return diccionario_javas[version_requerida]
        if diccionario_javas: return diccionario_javas[sorted(diccionario_javas.keys(), reverse=True)[0]]
        return None

    def controlar_servidor(self):
        if self.proceso_server.state() == QProcess.ProcessState.NotRunning:
            item_seleccionado = self.lista_servidores.currentItem()
            if not item_seleccionado: return

            nombre_carpeta = item_seleccionado.text()
            ruta_servidor = os.path.join(self.ruta_instancias, nombre_carpeta)
            ejecutable, java_especifico = self.obtener_datos_instancia(ruta_servidor)
            
            if java_especifico == "AUTO" or not java_especifico:
                java_exe_real = self.seleccionar_mejor_java(ruta_servidor)
            else:
                java_exe_real = os.path.join(self.ruta_javas_raiz, java_especifico, "bin", "java.exe")

            if not java_exe_real or not ejecutable: return

            self.instancia_actual = nombre_carpeta

            self.ventana_consola = ConsoleWindow(nombre_carpeta, self)
            self.ventana_consola.consola.appendPlainText(f"[Launcher] Lanzando instancia en modo silencioso (NOGUI)...")
            self.ventana_consola.input_comando.returnPressed.connect(self.enviar_comando_servidor)
            self.ventana_consola.show()

            env = QProcessEnvironment.systemEnvironment()
            env.insert("PATH", os.path.dirname(java_exe_real) + os.path.pathsep + env.value("PATH"))
            self.proceso_server.setProcessEnvironment(env)
            self.proceso_server.setWorkingDirectory(ruta_servidor)

            if ejecutable.endswith(".bat"):
                comando = "cmd.exe"
                argumentos = ["/c", ejecutable, "nogui"]
            else:
                comando = java_exe_real
                argumentos = ["-Xmx2G", "-Xms1G", "-jar", ejecutable, "nogui"]

            self.actualizar_estado_botones()
            self.proceso_server.start(comando, argumentos)
            self.btn_iniciar.setText("🛑 Detener Servidor Seleccionado")
        else:
            if self.ventana_consola:
                self.ventana_consola.consola.appendPlainText("\n[Launcher] Enviando comando 'stop'...")
            self.proceso_server.write(b"stop\n")

    def enviar_comando_servidor(self):
        if not self.ventana_consola: return
        texto = self.ventana_consola.input_comando.text().strip()
        if texto:
            self.ventana_consola.consola.appendPlainText(f"> {texto}")
            self.proceso_server.write(f"{texto}\n".encode("utf-8"))
            self.ventana_consola.input_comando.clear()

    def leer_consola(self):
        data = self.proceso_server.readAll().data()
        try:
            texto = data.decode("utf-8")
        except UnicodeDecodeError:
            texto = data.decode("cp1252", errors="replace")
        
        if self.ventana_consola:
            # --- EVITAR QUEDARSE TRABADO EN EL PAUSE ---
            if "Presione una tecla para continuar" in texto:
                # Si el script manda el pause, le mandamos un Enter virtual automáticamente
                self.proceso_server.write(b"\n")
            else:
                self.ventana_consola.consola.appendPlainText(texto.rstrip())

    def servidor_terminado(self):
        # --- CIERRE AUTOMÁTICO DE LA VENTANA ---
        if self.ventana_consola:
            self.ventana_consola.close()  # Cierra la ventana flotante inmediatamente de forma limpia
            self.ventana_consola = None
        
        self.btn_iniciar.setText("🚀 Iniciar Servidor")
        self.instancia_actual = None
        self.actualizar_estado_botones()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    ventana = ServerLauncher()
    ventana.show()
    sys.exit(app.exec())