import os
import sys
import json
import struct
from PyQt6.QtWidgets import (QApplication, QMainWindow, QPushButton, 
                             QVBoxLayout, QHBoxLayout, QWidget, 
                             QListWidget, QPlainTextEdit, QLabel, 
                             QDialog, QFileDialog, QLineEdit, QComboBox)
from PyQt6.QtCore import QProcess, QProcessEnvironment


class ConfigGlobalDialog(QDialog):
    def __init__(self, ruta_instancias, ruta_javas_raiz, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configuración General")
        self.resize(600, 180)
        
        self.ruta_instancias = ruta_instancias
        self.ruta_javas_raiz = ruta_javas_raiz

        # Componentes carpeta de instancias
        self.lbl_instancias = QLabel("Ruta raíz de la carpeta de Instancias:")
        self.txt_instancias = QLineEdit(self.ruta_instancias)
        self.txt_instancias.setReadOnly(True)
        self.btn_buscar_instancias = QPushButton("Examinar...")

        # Componentes Carpeta Raíz de Javas
        self.lbl_javas_raiz = QLabel("Carpeta raíz de entornos Java (donde están tus subcarpetas de Java):")
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
        self.resize(600, 220)
        
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

        self.btn_guardar = QPushButton("Guardar Cambios")
        self.btn_cancelar = QPushButton("Cancelar")

        layout_archivo = QHBoxLayout()
        layout_archivo.addWidget(self.txt_archivo)
        layout_archivo.addWidget(self.btn_buscar_archivo)

        layout_botones = QHBoxLayout()
        layout_botones.addStretch()
        layout_botones.addWidget(self.btn_guardar)
        layout_botones.addWidget(self.btn_cancelar)

        layout_principal = QVBoxLayout()
        layout_principal.addWidget(self.lbl_info)
        layout_principal.addLayout(layout_archivo)
        layout_principal.addSpacing(10)
        layout_principal.addWidget(self.lbl_java)
        layout_principal.addWidget(self.combo_java)
        layout_principal.addSpacing(15)
        layout_principal.addLayout(layout_botones)
        self.setLayout(layout_principal)

        self.btn_buscar_archivo.clicked.connect(self.seleccionar_archivo)
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
        self.setWindowTitle("Minecraft Server Launcher Pro")
        self.resize(1050, 600)

        self.ARCHIVO_CONFIG_GLOBAL = os.path.join(os.path.dirname(__file__), "config.json")
        self.ruta_instancias = ""
        self.ruta_javas_raiz = ""
        
        self.cargar_configuracion_global()

        # --- INTERFAZ UI ---
        self.lbl_instancias = QLabel("Selecciona un Servidor:")
        self.lista_servidores = QListWidget()
        
        self.btn_iniciar = QPushButton("Iniciar Servidor Seleccionado")
        self.btn_config_instancia = QPushButton("🛠️ Configurar Instancia")
        self.btn_config_global = QPushButton("⚙️ Configuración General")
        
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
        self.consola.setPlaceholderText("La terminal del servidor se mostrará aquí...")

        self.input_comando = QLineEdit()
        self.input_comando.setPlaceholderText("Escribe un comando aquí y presiona Enter...")
        self.input_comando.setStyleSheet("""
            QLineEdit { background-color: #1e1e1e; color: #ffffff; border: 1px solid #333333; font-family: 'Consolas', monospace; padding: 4px; }
        """)
        self.input_comando.setEnabled(False)

        layout_izquierdo = QVBoxLayout()
        layout_izquierdo.addWidget(self.lbl_instancias)
        layout_izquierdo.addWidget(self.lista_servidores)
        layout_izquierdo.addWidget(self.btn_iniciar)
        layout_izquierdo.addWidget(self.btn_config_instancia)
        layout_izquierdo.addWidget(self.btn_config_global)

        layout_derecho = QVBoxLayout()
        layout_derecho.addWidget(QLabel("Terminal del Servidor:"))
        layout_derecho.addWidget(self.consola)
        layout_derecho.addWidget(self.input_comando)

        layout_principal = QHBoxLayout()
        layout_principal.addLayout(layout_izquierdo, stretch=1)
        layout_principal.addLayout(layout_derecho, stretch=3)

        container = QWidget()
        container.setLayout(layout_principal)
        self.setCentralWidget(container)

        self.proceso_server = QProcess(self)
        self.instancia_actual = None
        self.proceso_server.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)

        # Eventos
        self.btn_iniciar.clicked.connect(self.controlar_servidor)
        self.btn_config_global.clicked.connect(self.abrir_configuracion_global)
        self.btn_config_instancia.clicked.connect(self.abrir_configuracion_instancia)
        self.input_comando.returnPressed.connect(self.enviar_comando_servidor)
        self.lista_servidores.currentTextChanged.connect(self.actualizar_estado_botones)
        
        self.proceso_server.readyRead.connect(self.leer_consola)
        self.proceso_server.finished.connect(self.servidor_terminado)

        self.cargar_instancias()
        self.actualizar_estado_botones()

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
            self.consola.appendPlainText("[Launcher] Configuración general guardada.")
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
            self.consola.appendPlainText(f"[Launcher] Opciones guardadas para '{nombre_carpeta}'.")

    def cargar_instancias(self):
        self.lista_servidores.clear()
        if os.path.exists(self.ruta_instancias):
            try:
                carpetas = [f for f in os.listdir(self.ruta_instancias) if os.path.isdir(os.path.join(self.ruta_instancias, f))]
                self.lista_servidores.addItems(carpetas)
            except Exception as e:
                self.consola.appendPlainText(f"[Launcher] Error al leer carpetas: {e}")
        self.actualizar_estado_botones()

    def actualizar_estado_botones(self):
        tiene_seleccion = self.lista_servidores.currentItem() is not None
        self.btn_config_instancia.setEnabled(tiene_seleccion and self.proceso_server.state() == QProcess.ProcessState.NotRunning)

    # --- MOTOR DE AUTO-DETECCIÓN DE JAVA ---
    def detectar_version_java_de_jar(self, ruta_jar):
        """Inspecciona los bytes de un archivo .jar para saber qué versión de Java exige."""
        if not os.path.exists(ruta_jar):
            return 17 # Por defecto si no se encuentra
        try:
            import zipfile
            with zipfile.ZipFile(ruta_jar, 'r') as z:
                # Buscamos cualquier clase compilada interna para ver su formato
                for name in z.namelist():
                    if name.endswith('.class'):
                        with z.open(name) as f:
                            magic = f.read(4)
                            if magic == b'\xca\xfe\xba\xbe': # Magic bytes de Java Class
                                minor, major = struct.unpack('>HH', f.read(4))
                                # Mapeo de versiones mayores de clase Java
                                mapa_versiones = {52: 8, 53: 9, 54: 10, 55: 11, 56: 12, 57: 13, 58: 14, 59: 15, 60: 16, 61: 17, 62: 18, 63: 19, 64: 20, 65: 21, 66: 22}
                                return mapa_versiones.get(major, 17)
        except Exception:
            pass
        return 17

    def escanear_versiones_en_carpeta_javas(self):
        """Escanea las subcarpetas de Java y detecta de manera real su versión ejecutando java -version."""
        javas_disponibles = {}
        if not self.ruta_javas_raiz or not os.path.exists(self.ruta_javas_raiz):
            return javas_disponibles

        for item in os.listdir(self.ruta_javas_raiz):
            ruta_exe = os.path.join(self.ruta_javas_raiz, item, "bin", "java.exe")
            if os.path.exists(ruta_exe):
                # Consultamos de manera silenciosa qué versión tiene este binario
                version_detectada = self.obtener_version_de_binario(ruta_exe)
                if version_detectada:
                    javas_disponibles[version_detectada] = ruta_exe
        return javas_disponibles

    def obtener_version_de_binario(self, ruta_exe):
        """Ejecuta temporalmente el java.exe para parsear su string de versión."""
        p = QProcess()
        p.start(ruta_exe, ["-version"])
        p.waitForFinished(1000)
        output = str(p.readAllStandardError()) # Java imprime el -version en el canal de error
        
        if "1.8.0" in output or '"1.8' in output: return 8
        for v in [11, 16, 17, 18, 19, 20, 21, 22]:
            if f'"{v}.' in output or f' {v}.' in output:
                return v
        # Fallback analizando el nombre de la carpeta por si acaso
        nombre_dir = os.path.basename(os.path.dirname(os.path.dirname(ruta_exe))).lower()
        if "legacy" in nombre_dir or "8" in nombre_dir: return 8
        if "17" in nombre_dir: return 17
        if "21" in nombre_dir: return 21
        return None

    def seleccionar_mejor_java(self, ruta_servidor):
        """Algoritmo inteligente de emparejamiento."""
        # 1. Averiguar qué versión quiere el Servidor
        version_requerida = 17 # Base por defecto si es difuso
        
        # Buscar server.jar o cualquier archivo jar principal
        jar_principal = os.path.join(ruta_servidor, "server.jar")
        if not os.path.exists(jar_principal):
            for f in os.listdir(ruta_servidor):
                if f.endswith(".jar") and ("forge" in f or "fabric" in f or "paper" in f or "server" in f):
                    jar_principal = os.path.join(ruta_servidor, f)
                    break
        
        if os.path.exists(jar_principal):
            version_requerida = self.detectar_version_java_de_jar(jar_principal)
        else:
            # Analizar si es un servidor moderno o viejo por la presencia de ciertos scripts
            if os.path.exists(os.path.join(ruta_servidor, "user_jvm_args.txt")):
                version_requerida = 17
            elif os.path.exists(os.path.join(ruta_servidor, "libraries")):
                version_requerida = 17

        self.consola.appendPlainText(f"[Auto-Detector] El servidor parece requerir Java {version_requerida}.")

        # 2. Buscar en tus carpetas cuál coincide
        diccionario_javas = self.escanear_versiones_en_carpeta_javas()
        
        if version_requerida in diccionario_javas:
            ruta_final = diccionario_javas[version_requerida]
            self.consola.appendPlainText(f"[Auto-Detector] ¡Match perfecto! Usando: '{os.path.basename(os.path.dirname(os.path.dirname(ruta_final)))}' (Java {version_requerida})")
            return ruta_final
        
        # Si no hay match perfecto, buscar la versión más alta que tengamos
        if diccionario_javas:
            versiones_ordenadas = sorted(diccionario_javas.keys(), reverse=True)
            mejor_fallback = versiones_ordenadas[0]
            self.consola.appendPlainText(f"[Auto-Detector] Advertencia: No tienes instalado Java {version_requerida}. Usando la versión más alta disponible: Java {mejor_fallback}")
            return diccionario_javas[mejor_fallback]
        
        return None

    # --- CONTROL DE EJECUCIÓN ---
    def controlar_servidor(self):
        if self.proceso_server.state() == QProcess.ProcessState.NotRunning:
            item_seleccionado = self.lista_servidores.currentItem()
            if not item_seleccionado: return

            nombre_carpeta = item_seleccionado.text()
            ruta_servidor = os.path.join(self.ruta_instancias, nombre_carpeta)
            
            ejecutable, java_especifico = self.obtener_datos_instancia(ruta_servidor)
            
            self.consola.clear()
            self.consola.appendPlainText(f"[Launcher] Analizando instancia '{nombre_carpeta}'...")

            # Determinar qué Java usar (Manual o Auto-detectado)
            if java_especifico == "AUTO" or not java_especifico:
                java_exe_real = self.seleccionar_mejor_java(ruta_servidor)
            else:
                # Selección forzada por el usuario
                java_exe_real = os.path.join(self.ruta_javas_raiz, java_especifico, "bin", "java.exe")
                if not os.path.exists(java_exe_real): java_exe_real = None

            if not java_exe_real:
                self.consola.appendPlainText("[Launcher] Error Crítico: No se pudo auto-detectar ningún entorno de Java en tu carpeta raíz de Javas. Por favor, verifica la Configuración General.")
                return

            if not ejecutable:
                self.consola.appendPlainText("[Launcher] Error: No se encontró un archivo ejecutable (run.bat / server.jar).")
                return

            self.instancia_actual = nombre_carpeta
            self.consola.appendPlainText(f"[Launcher] Lanzando servidor...\n")

            # Inyectar el Java seleccionado al PATH dinámico
            env = QProcessEnvironment.systemEnvironment()
            carpeta_java_bin = os.path.dirname(java_exe_real)
            env.insert("PATH", carpeta_java_bin + os.path.pathsep + env.value("PATH"))
            self.proceso_server.setProcessEnvironment(env)

            self.proceso_server.setWorkingDirectory(ruta_servidor)

            if ejecutable.endswith(".bat"):
                comando = "cmd.exe"
                argumentos = ["/c", ejecutable]
            elif ejecutable.endswith(".jar"):
                comando = java_exe_real
                argumentos = ["-Xmx2G", "-Xms1G", "-jar", ejecutable, "nogui"]
            else:
                comando = os.path.join(ruta_servidor, ejecutable)
                argumentos = []

            self.lista_servidores.setEnabled(False)
            self.btn_config_global.setEnabled(False)
            self.btn_config_instancia.setEnabled(False)
            self.input_comando.setEnabled(True)
            
            self.proceso_server.start(comando, argumentos)
            self.btn_iniciar.setText("Detener Servidor")
        else:
            self.consola.appendPlainText("\n[Launcher] Enviando comando 'stop'...")
            self.proceso_server.write(b"stop\n")

    def enviar_comando_servidor(self):
        texto = self.input_comando.text().strip()
        if texto:
            self.consola.appendPlainText(f"> {texto}")
            self.proceso_server.write(f"{texto}\n".encode("utf-8"))
            self.input_comando.clear()

    def leer_consola(self):
        data = self.proceso_server.readAll().data()
        try:
            texto = data.decode("utf-8")
        except UnicodeDecodeError:
            texto = data.decode("cp1252", errors="replace")
        self.consola.appendPlainText(texto.rstrip())

    def servidor_terminado(self):
        self.consola.appendPlainText(f"\n[Launcher] Proceso cerrado correctamente.")
        self.btn_iniciar.setText("Iniciar Servidor Seleccionado")
        self.lista_servidores.setEnabled(True)
        self.btn_config_global.setEnabled(True)
        self.input_comando.setEnabled(False)
        self.input_comando.clear()
        self.instancia_actual = None
        self.actualizar_estado_botones()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    ventana = ServerLauncher()
    ventana.show()
    sys.exit(app.exec())