import os
import sys
import json
import struct
import shutil
import zipfile
from PyQt6.QtWidgets import (QApplication, QMainWindow, QPushButton, 
                             QVBoxLayout, QHBoxLayout, QWidget, 
                             QListWidget, QListWidgetItem, QPlainTextEdit, 
                             QLabel, QDialog, QFileDialog, QLineEdit, QComboBox,
                             QProgressBar, QMessageBox)
from PyQt6.QtCore import QProcess, QProcessEnvironment, Qt, QSize, QThread, pyqtSignal
from PyQt6.QtGui import QIcon, QPixmap


class DownloaderWorker(QThread):
    """Hilo secundario para descargar y extraer Java sin congelar la interfaz."""
    progreso = pyqtSignal(int)
    estado = pyqtSignal(str)
    finalizado = pyqtSignal(bool, str)

    def __init__(self, url, destino_zip, carpeta_extraccion):
        super().__init__()
        self.url = url
        self.destino_zip = destino_zip
        self.carpeta_extraccion = carpeta_extraccion

    def run(self):
        try:
            import urllib.request
            self.estado.emit("Descargando paquete de Java (OpenJDK)...")
            
            # Conexión y descarga con reporte de progreso
            req = urllib.request.Request(self.url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response:
                total_size = int(response.info().get('Content-Length', 0))
                bytes_leidos = 0
                block_size = 1024 * 64
                
                with open(self.destino_zip, 'wb') as f:
                    while True:
                        buffer = response.read(block_size)
                        if not buffer:
                            break
                        bytes_leidos += len(buffer)
                        f.write(buffer)
                        if total_size > 0:
                            porcentaje = int((bytes_leidos / total_size) * 100)
                            self.progreso.emit(porcentaje)

            self.estado.emit("Extrayendo archivos de entorno portable...")
            self.progreso.emit(0)
            
            # Extracción del ZIP
            with zipfile.ZipFile(self.destino_zip, 'r') as zip_ref:
                lista_archivos = zip_ref.namelist()
                total_archivos = len(lista_archivos)
                
                # Crear el directorio raíz de extracción si no existe
                if not os.path.exists(self.carpeta_extraccion):
                    os.makedirs(self.carpeta_extraccion)

                for i, archivo in enumerate(lista_archivos):
                    zip_ref.extract(archivo, self.carpeta_extraccion)
                    if total_archivos > 0:
                        self.progreso.emit(int(((i + 1) / total_archivos) * 100))

            # Limpieza del instalador comprimido temporal
            if os.path.exists(self.destino_zip):
                os.remove(self.destino_zip)

            self.finalizado.emit(True, "Java instalado y configurado correctamente.")
        except Exception as e:
            self.finalizado.emit(False, str(e))


class ConsoleWindow(QDialog):
    """Ventana independiente para la terminal del servidor con botón de detención."""
    solicitar_stop = pyqtSignal()

    def __init__(self, nombre_instancia, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Terminal del Servidor - {nombre_instancia}")
        self.resize(850, 530)
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

        # Botón dedicado para apagar el servidor directamente desde aquí
        self.btn_stop_consola = QPushButton("🛑 Detener Servidor")
        self.btn_stop_consola.setStyleSheet("""
            QPushButton {
                background-color: #a61c1c;
                color: white;
                font-weight: bold;
                padding: 6px 12px;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #cc2424; }
        """)
        self.btn_stop_consola.clicked.connect(self.solicitar_stop.emit)

        layout_comandos = QHBoxLayout()
        layout_comandos.addWidget(self.input_comando, stretch=4)
        layout_comandos.addWidget(self.btn_stop_consola, stretch=1)

        layout = QVBoxLayout()
        layout.addWidget(QLabel(f"Consola activa: {nombre_instancia}"))
        layout.addWidget(self.consola)
        layout.addLayout(layout_comandos)
        self.setLayout(layout)


class ConfigGlobalDialog(QDialog):
    def __init__(self, ruta_instancias, ruta_javas_raiz, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configuración General y Gestor de Java")
        self.resize(650, 380)
        
        self.ruta_instancias = ruta_instancias
        self.ruta_javas_raiz = ruta_javas_raiz
        self.worker = None

        # --- SECCIÓN CARPETAS ---
        self.lbl_instancias = QLabel("Ruta raíz de la carpeta de Instancias:")
        self.txt_instancias = QLineEdit(self.ruta_instancias)
        self.txt_instancias.setReadOnly(True)
        self.btn_buscar_instancias = QPushButton("Examinar...")

        self.lbl_javas_raiz = QLabel("Carpeta raíz de entornos Java (Portables):")
        self.txt_javas_raiz = QLineEdit(self.ruta_javas_raiz)
        self.txt_javas_raiz.setReadOnly(True)
        self.btn_buscar_javas = QPushButton("Examinar...")

        # --- SECCIÓN GESTOR DE DESCARGAS JAVA ---
        self.lbl_downloader = QLabel("📥 Descargar versiones de Java Runtime portables necesarias:")
        self.lbl_downloader.setStyleSheet("font-weight: bold; margin-top: 10px;")
        
        self.combo_descargas = QComboBox()
        # URLs oficiales pre-configuradas para descargas portables de Eclipse Temurin (Windows x64)
        self.combo_descargas.addItem("Java 8 (Recomendado para servidores Minecraft antiguos 1.7 - 1.12)", "https://github.com/adoptium/temurin8-binaries/releases/download/jdk8u412-b08/OpenJDK8U-jdk_x64_windows_hotspot_8u412b08.zip")
        self.combo_descargas.addItem("Java 17 (Recomendado para servidores de versiones 1.17 a 1.20.4)", "https://github.com/adoptium/temurin17-binaries/releases/download/jdk-17.0.11%2B9/OpenJDK17U-jdk_x64_windows_hotspot_17.0.11_9.zip")
        self.combo_descargas.addItem("Java 21 (Recomendado para servidores modernos 1.20.5+ y superiores)", "https://github.com/adoptium/temurin21-binaries/releases/download/jdk-21.0.3%2B9/OpenJDK21U-jdk_x64_windows_hotspot_21.0.3_9.zip")

        self.btn_descargar_java = QPushButton("⚡ Descargar e Instalar")
        self.lbl_estado_descarga = QLabel("Estado: Esperando acción...")
        self.barra_progreso = QProgressBar()
        self.barra_progreso.setValue(0)

        self.btn_guardar = QPushButton("Guardar y Cerrar")
        self.btn_cancelar = QPushButton("Cancelar")

        # Layouts
        layout_instancias = QHBoxLayout()
        layout_instancias.addWidget(self.txt_instancias)
        layout_instancias.addWidget(self.btn_buscar_instancias)

        layout_javas = QHBoxLayout()
        layout_javas.addWidget(self.txt_javas_raiz)
        layout_javas.addWidget(self.btn_buscar_javas)

        layout_dl_controles = QHBoxLayout()
        layout_dl_controles.addWidget(self.combo_descargas)
        layout_dl_controles.addWidget(self.btn_descargar_java)

        layout_botones = QHBoxLayout()
        layout_botones.addStretch()
        layout_botones.addWidget(self.btn_guardar)
        layout_botones.addWidget(self.btn_cancelar)

        layout_principal = QVBoxLayout()
        layout_principal.addWidget(self.lbl_instancias)
        layout_principal.addLayout(layout_instancias)
        layout_principal.addSpacing(5)
        layout_principal.addWidget(self.lbl_javas_raiz)
        layout_principal.addLayout(layout_javas)
        
        layout_principal.addSpacing(10)
        layout_principal.addWidget(self.lbl_downloader)
        layout_principal.addLayout(layout_dl_controles)
        layout_principal.addWidget(self.lbl_estado_descarga)
        layout_principal.addWidget(self.barra_progreso)
        
        layout_principal.addSpacing(20)
        layout_principal.addLayout(layout_botones)
        self.setLayout(layout_principal)

        # Conexiones
        self.btn_buscar_instancias.clicked.connect(self.seleccionar_instancias)
        self.btn_buscar_javas.clicked.connect(self.seleccionar_carpeta_javas)
        self.btn_descargar_java.clicked.connect(self.iniciar_descarga_java)
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

    def iniciar_descarga_java(self):
        if not self.ruta_javas_raiz or not os.path.exists(self.ruta_javas_raiz):
            QMessageBox.warning(self, "Error de Destino", "Por favor, selecciona primero una carpeta raíz de entornos Java válida.")
            return

        url = self.combo_descargas.currentData()
        nombre_zip = "temp_java_download.zip"
        destino_zip = os.path.join(self.ruta_javas_raiz, nombre_zip)
        
        self.btn_descargar_java.setEnabled(False)
        self.combo_descargas.setEnabled(False)

        # Iniciar Worker en hilo separado para no bloquear la GUI
        self.worker = DownloaderWorker(url, destino_zip, self.ruta_javas_raiz)
        self.worker.progreso.connect(self.barra_progreso.setValue)
        self.worker.estado.connect(self.lbl_estado_descarga.setText)
        self.worker.finalizado.connect(self.descarga_completada)
        self.worker.start()

    def descarga_completada(self, exito, mensaje):
        self.btn_descargar_java.setEnabled(True)
        self.combo_descargas.setEnabled(True)
        self.barra_progreso.setValue(100 if exito else 0)
        if exito:
            self.lbl_estado_descarga.setText("Estado: ¡Instalación completada exitosamente!")
            QMessageBox.information(self, "Proceso Finalizado", mensaje)
        else:
            self.lbl_estado_descarga.setText("Estado: Error durante la instalación.")
            QMessageBox.critical(self, "Error de Descarga", f"Ocurrió un problema: {mensaje}")


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
        self.btn_config_global = QPushButton("⚙️ Configuración General / Javas")
        
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
        
        if not self.ruta_javas_raiz:
            self.ruta_javas_raiz = os.path.join(os.path.dirname(__file__), "javas")
            if not os.path.exists(self.ruta_javas_raiz):
                os.makedirs(self.ruta_javas_raiz)
                
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
        
        # Escaneo recursivo para buscar ejecutables java.exe (soporta la extracción directa de carpetas comprimidas)
        for raiz, directorios, archivos in os.walk(self.ruta_javas_raiz):
            if "java.exe" in archivos:
                ruta_exe = os.path.join(raiz, "java.exe")
                v = self.obtener_version_de_binario(ruta_exe)
                if v: 
                    javas_disponibles[v] = ruta_exe
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

    def detener_servidor_desde_consola(self):
        if self.proceso_server.state() == QProcess.ProcessState.Running:
            if self.ventana_consola:
                self.ventana_consola.consola.appendPlainText("\n[Launcher] Detención solicitada desde la terminal externa...")
            self.proceso_server.write(b"stop\n")

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
                # Buscar dinámicamente si existe la subcarpeta específica
                java_exe_real = None
                for raiz, _, archivos in os.walk(os.path.join(self.ruta_javas_raiz, java_especifico)):
                    if "java.exe" in archivos:
                        java_exe_real = os.path.join(raiz, "java.exe")
                        break

            if not java_exe_real or not ejecutable: 
                QMessageBox.critical(self, "Falta Entorno", "No se pudo localizar un ejecutable válido de Java para esta instancia. Ve a Configuración General y descarga una versión compatible.")
                return

            self.instancia_actual = nombre_carpeta

            self.ventana_consola = ConsoleWindow(nombre_carpeta, self)
            self.ventana_consola.consola.appendPlainText(f"[Launcher] Iniciando con binario: {java_exe_real}")
            self.ventana_consola.input_comando.returnPressed.connect(self.enviar_comando_servidor)
            self.ventana_consola.solicitar_stop.connect(self.detener_servidor_desde_consola)
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
            self.detener_servidor_desde_consola()

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
            if "Presione una tecla para continuar" in texto:
                self.proceso_server.write(b"\n")
            else:
                self.ventana_consola.consola.appendPlainText(texto.rstrip())

    def servidor_terminado(self):
        if self.ventana_consola:
            self.ventana_consola.close()
            self.ventana_consola = None
        
        self.btn_iniciar.setText("🚀 Iniciar Servidor")
        self.instancia_actual = None
        self.actualizar_estado_botones()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    ventana = ServerLauncher()
    ventana.show()
    sys.exit(app.exec())