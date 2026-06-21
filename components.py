# components.py
import os
import shutil
import stat
import json
import re
import urllib.request
import urllib.parse
import urllib.error
import webbrowser
import zipfile
from PyQt6.QtWidgets import (QDialog, QPlainTextEdit, QLineEdit, QPushButton, 
                             QHBoxLayout, QVBoxLayout, QLabel, QComboBox, 
                              QProgressBar, QMessageBox, QFileDialog, QListWidget, QListWidgetItem)
from PyQt6.QtWidgets import QGroupBox
from PyQt6.QtCore import Qt, pyqtSignal, QRegularExpression, QUrl
from PyQt6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QIcon, QDesktopServices
from workers import DownloaderWorker, FTBDownloadWorker, ZipExtractionWorker

class LogHighlighter(QSyntaxHighlighter):
    def __init__(self, parent):
        super().__init__(parent)
        self.formatos = {
            "INFO": self._crear_formato("#7dd3fc"),    # Azul claro
            "WARN": self._crear_formato("#fbbf24"),    # Ámbar
            "ERROR": self._crear_formato("#f87171"),   # Rojo suave
            "FATAL": self._crear_formato("#ef4444", bold=True), # Rojo fuerte
            "LAUNCHER": self._crear_formato("#a78bfa"), # Violeta
            "DONE": self._crear_formato("#4ade80", bold=True)   # Verde brillante
        }

    def _crear_formato(self, color, bold=False):
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))
        if bold: fmt.setFontWeight(700)
        return fmt

    def highlightBlock(self, text):
        text_up = text.upper()
        if "[LAUNCHER]" in text_up: self.setFormat(0, len(text), self.formatos["LAUNCHER"])
        elif "DONE (" in text_up or "FOR HELP, TYPE \"HELP\"" in text_up: self.setFormat(0, len(text), self.formatos["DONE"])
        elif "ERROR" in text_up: self.setFormat(0, len(text), self.formatos["ERROR"])
        elif "WARN" in text_up: self.setFormat(0, len(text), self.formatos["WARN"])
        elif "FATAL" in text_up: self.setFormat(0, len(text), self.formatos["FATAL"])
        elif "INFO" in text_up: self.setFormat(0, len(text), self.formatos["INFO"])

class ConsoleWindow(QDialog):
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
        # Aseguramos que la consola siempre muestre lo último que llega (autoscroll)
        self.consola.textChanged.connect(lambda: self.consola.ensureCursorVisible())
        self.highlighter = LogHighlighter(self.consola.document())
        
        self.input_comando = QLineEdit()
        self.input_comando.setPlaceholderText("Escribe un comando aquí y presiona Enter...")
        self.input_comando.setStyleSheet("""
            QLineEdit { background-color: #1e1e1e; color: #ffffff; border: 1px solid #333333; font-family: 'Consolas', monospace; padding: 6px; }
        """)

        self.btn_stop_consola = QPushButton("🛑 Detener Servidor")
        # IMPORTANTE: Evitamos que el botón sea el 'default' y se active con Enter
        self.btn_stop_consola.setAutoDefault(False)
        self.btn_stop_consola.setDefault(False)
        
        self.btn_stop_consola.setStyleSheet("""
            QPushButton { background-color: #a61c1c; color: white; font-weight: bold; padding: 6px 12px; border-radius: 4px; }
            QPushButton:hover { background-color: #cc2424; }
        """)
        self.btn_stop_consola.clicked.connect(self.solicitar_stop.emit)

        self.btn_subir_log = QPushButton("📤 Subir")
        self.btn_subir_log.setAutoDefault(False)
        self.btn_subir_log.setStyleSheet("""
            QPushButton { background-color: #2563eb; color: white; font-weight: bold; padding: 6px 12px; border-radius: 4px; }
            QPushButton:hover { background-color: #1d4ed8; }
        """)
        self.btn_subir_log.clicked.connect(self.subir_log_a_mclogs)

        layout_comandos = QHBoxLayout()
        layout_comandos.addWidget(self.input_comando, stretch=3)
        layout_comandos.addWidget(self.btn_subir_log, stretch=1)
        layout_comandos.addWidget(self.btn_stop_consola, stretch=1)

        layout = QVBoxLayout()
        layout.addWidget(QLabel(f"Consola activa: {nombre_instancia}"))
        layout.addWidget(self.consola)
        layout.addLayout(layout_comandos)
        self.setLayout(layout)

    def subir_log_a_mclogs(self):
        """Sube el contenido actual de la consola a mclo.gs."""
        log_content = self.consola.toPlainText().strip()
        if not log_content:
            QMessageBox.warning(self, "Log vacío", "No hay contenido en la consola para subir.")
            return

        confirm = QMessageBox.question(
            self, "Confirmar subida",
            "¿Deseas subir el log actual a mclo.gs?\n\n"
            "Esto generará un enlace público para compartir tus registros de errores.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if confirm == QMessageBox.StandardButton.Yes:
            try:
                # La API de mclo.gs requiere el contenido en el cuerpo de un POST (x-www-form-urlencoded)
                url = "https://api.mclo.gs/1/log"
                data = urllib.parse.urlencode({'content': log_content}).encode('utf-8')
                req = urllib.request.Request(url, data=data, method='POST')
                req.add_header('Content-Type', 'application/x-www-form-urlencoded')

                with urllib.request.urlopen(req, timeout=30) as response:
                    res_data = json.loads(response.read().decode('utf-8'))
                    if res_data.get("success"):
                        log_url = res_data.get("url")
                        
                        pregunta = QMessageBox.information(
                            self, "Log Subido",
                            f"El log se ha subido correctamente.\n\nEnlace: {log_url}\n\n¿Deseas abrir el link en el navegador?",
                            QMessageBox.StandardButton.Open | QMessageBox.StandardButton.Close
                        )
                        
                        if pregunta == QMessageBox.StandardButton.Open:
                            webbrowser.open(log_url)
                    else:
                        error_msg = res_data.get("error", "Error desconocido")
                        QMessageBox.critical(self, "Error al subir", f"mclo.gs devolvió un error: {error_msg}")
            except Exception as e:
                QMessageBox.critical(self, "Error de red", f"No se pudo conectar con mclo.gs:\n{e}")


class ConfigGlobalDialog(QDialog):
    def __init__(self, ruta_instancias, ruta_javas_raiz, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configuración General y Gestor de Java")
        self.resize(650, 380)
        
        self.ruta_instancias = ruta_instancias
        self.ruta_javas_raiz = ruta_javas_raiz
        self.worker = None

        self.lbl_instancias = QLabel("Ruta raíz de la carpeta de Instancias:")
        self.txt_instancias = QLineEdit(self.ruta_instancias)
        self.txt_instancias.setReadOnly(True)
        self.btn_buscar_instancias = QPushButton("Examinar...")

        self.lbl_javas_raiz = QLabel("Carpeta raíz de entornos Java (Portables):")
        self.txt_javas_raiz = QLineEdit(self.ruta_javas_raiz)
        self.txt_javas_raiz.setReadOnly(True)
        self.btn_buscar_javas = QPushButton("Examinar...")

        self.lbl_downloader = QLabel("📥 Descargar versiones de Java Runtime portables necesarias:")
        self.lbl_downloader.setStyleSheet("font-weight: bold; margin-top: 10px;")
        
        self.combo_descargas = QComboBox()
        self.combo_descargas.addItem("Java 8 (Minecraft antiguos 1.7 - 1.12)", "https://github.com/adoptium/temurin8-binaries/releases/download/jdk8u412-b08/OpenJDK8U-jdk_x64_windows_hotspot_8u412b08.zip")
        self.combo_descargas.addItem("Java 17 (Versiones 1.17 a 1.20.4)", "https://github.com/adoptium/temurin17-binaries/releases/download/jdk-17.0.11%2B9/OpenJDK17U-jdk_x64_windows_hotspot_17.0.11_9.zip")
        self.combo_descargas.addItem("Java 21 (Versiones modernas 1.20.5+)", "https://github.com/adoptium/temurin21-binaries/releases/download/jdk-21.0.3%2B9/OpenJDK21U-jdk_x64_windows_hotspot_21.0.3_9.zip")

        self.btn_descargar_java = QPushButton("⚡ Descargar e Instalar")
        self.lbl_estado_descarga = QLabel("Estado: Esperando acción...")
        self.barra_progreso = QProgressBar()
        self.barra_progreso.setValue(0)

        self.btn_guardar = QPushButton("Guardar y Cerrar")
        self.btn_cancelar = QPushButton("Cancelar")

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
    instancia_eliminada = pyqtSignal()
    solicitar_actualizacion = pyqtSignal(str, str, str) # nombre, modpack_id, version_id
    solicitar_actualizacion_zip = pyqtSignal()

    def __init__(self, nombre_instancia, ruta_instancia, archivo_actual, java_actual,
                 ruta_javas_raiz, grupos_disponibles=None, parent=None):
        super().__init__(parent)
        self.nombre_instancia = nombre_instancia
        self.ruta_instancia = ruta_instancia
        self.archivo_seleccionado = archivo_actual
        self.java_seleccionado = java_actual
        self.ruta_javas_raiz = ruta_javas_raiz

        self.ftb_nombre_real = ""
        self.ftb_modpack_id = ""
        self.ftb_version_id = ""
        self.grupo_instancia = "No agrupado"
        ruta_json = os.path.join(self.ruta_instancia, "config_instancia.json")
        if os.path.exists(ruta_json):
            try:
                with open(ruta_json, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.ftb_nombre_real = data.get("ftb_nombre_real", "")
                    self.ftb_modpack_id = data.get("ftb_modpack_id", "")
                    self.ftb_version_id = data.get("ftb_version_id", "")
                    self.grupo_instancia = data.get("grupo", "No agrupado") or "No agrupado"
            except Exception: pass

        # Si no hay datos en el JSON, intentamos recuperarlos del LOG del instalador
        if not self.ftb_modpack_id:
            self.intentar_recuperar_metadatos_log()

        self.setWindowTitle(f"Configurar Instancia: {nombre_instancia}")
        self.resize(720, 680)

        self.lbl_nombre = QLabel("Nombre de la instancia (Carpeta):")
        self.txt_nombre = QLineEdit(self.nombre_instancia)
        self.txt_nombre.setPlaceholderText("Nombre de la carpeta en disco")

        self.lbl_info = QLabel("Archivo ejecutable/arranque de la instancia (ej: run.bat):")
        self.txt_archivo = QLineEdit(self.archivo_seleccionado)
        self.txt_archivo.setReadOnly(True)
        self.btn_buscar_archivo = QPushButton("Seleccionar...")

        self.lbl_java = QLabel("Asignación de Java para esta instancia:")
        self.combo_java = QComboBox()

        self.lbl_grupo = QLabel("Grupo de la instancia:")
        self.combo_grupo = QComboBox()
        self.combo_grupo.setEditable(True)
        grupos = sorted(set(grupos_disponibles or []) | {"No agrupado", self.grupo_instancia})
        self.combo_grupo.addItems(grupos)
        self.combo_grupo.setCurrentText(self.grupo_instancia)

        self.lbl_icon = QLabel("Icono personalizado de la instancia (Opcional - Imagen PNG/JPG):")
        self.txt_icon = QLineEdit()
        self.txt_icon.setReadOnly(True)
        self.btn_buscar_icon = QPushButton("Cambiar Icono...")
        
        ruta_icon_json = os.path.join(self.ruta_instancia, "icon.png")
        if os.path.exists(ruta_icon_json):
            self.txt_icon.setText("icon.png (Personalizado Detectado)")

        self.grupo_mods = QGroupBox("Mods instalados")
        self.lbl_cantidad_mods = QLabel()
        self.lista_mods = QListWidget()
        self.lista_mods.setMinimumHeight(130)
        self.btn_abrir_instancia = QPushButton("📂 Abrir carpeta de la instancia")
        self.btn_abrir_mods = QPushButton("🧩 Abrir carpeta de mods")
        layout_carpetas = QHBoxLayout()
        layout_carpetas.addWidget(self.btn_abrir_instancia)
        layout_carpetas.addWidget(self.btn_abrir_mods)
        layout_mods = QVBoxLayout(self.grupo_mods)
        layout_mods.addWidget(self.lbl_cantidad_mods)
        layout_mods.addWidget(self.lista_mods)
        layout_mods.addLayout(layout_carpetas)
        self.cargar_lista_mods()

        self.btn_actualizar = QPushButton("🔄 Actualizar Modpack")
        self.btn_actualizar.setEnabled(bool(self.ftb_modpack_id))
        self.btn_actualizar.setStyleSheet("""
            QPushButton { background-color: #0d9488; color: white; font-weight: bold; padding: 6px 15px; border-radius: 4px; }
            QPushButton:hover { background-color: #0f766e; }
            QPushButton:disabled { background-color: #4b5563; }
        """)

        self.btn_actualizar_zip = QPushButton("📦 Actualizar por ZIP")
        self.btn_actualizar_zip.setStyleSheet("""
            QPushButton { background-color: #7c3aed; color: white; font-weight: bold; padding: 6px 15px; border-radius: 4px; }
            QPushButton:hover { background-color: #6d28d9; }
        """)

        self.btn_eliminar = QPushButton("🗑️ Eliminar Instancia")
        self.btn_eliminar.setStyleSheet("""
            QPushButton { background-color: #a61c1c; color: white; font-weight: bold; padding: 6px 15px; border-radius: 4px; }
            QPushButton:hover { background-color: #cc2424; }
        """)

        self.btn_guardar = QPushButton("Guardar Cambios")
        self.btn_cancelar = QPushButton("Cancelar")

        layout_archivo = QHBoxLayout()
        layout_archivo.addWidget(self.txt_archivo)
        layout_archivo.addWidget(self.btn_buscar_archivo)

        layout_icon = QHBoxLayout()
        layout_icon.addWidget(self.txt_icon)
        layout_icon.addWidget(self.btn_buscar_icon)

        layout_botones = QHBoxLayout()
        layout_botones.addWidget(self.btn_eliminar)
        layout_botones.addWidget(self.btn_actualizar)
        layout_botones.addWidget(self.btn_actualizar_zip)
        layout_botones.addStretch()
        layout_botones.addWidget(self.btn_guardar)
        layout_botones.addWidget(self.btn_cancelar)

        layout_principal = QVBoxLayout()
        layout_principal.addWidget(self.lbl_nombre)
        layout_principal.addWidget(self.txt_nombre)
        layout_principal.addSpacing(10)
        layout_principal.addWidget(self.lbl_info)
        layout_principal.addLayout(layout_archivo)
        layout_principal.addSpacing(10)
        layout_principal.addWidget(self.lbl_icon)
        layout_principal.addLayout(layout_icon)
        layout_principal.addSpacing(10)
        layout_principal.addWidget(self.lbl_java)
        layout_principal.addWidget(self.combo_java)
        layout_principal.addSpacing(10)
        layout_principal.addWidget(self.lbl_grupo)
        layout_principal.addWidget(self.combo_grupo)
        layout_principal.addSpacing(10)
        layout_principal.addWidget(self.grupo_mods)
        layout_principal.addSpacing(20)
        layout_principal.addLayout(layout_botones)
        self.setLayout(layout_principal)

        self.btn_buscar_archivo.clicked.connect(self.seleccionar_archivo)
        self.btn_buscar_icon.clicked.connect(self.seleccionar_icono)
        self.btn_abrir_instancia.clicked.connect(
            lambda: self.abrir_carpeta(self.ruta_instancia)
        )
        self.btn_abrir_mods.clicked.connect(
            lambda: self.abrir_carpeta(os.path.join(self.ruta_instancia, "mods"), crear=True)
        )
        self.btn_eliminar.clicked.connect(self.eliminar_instancia_con_confirmacion)
        self.btn_actualizar.clicked.connect(self.preparar_actualizacion)
        self.btn_actualizar_zip.clicked.connect(self.solicitar_actualizacion_zip.emit)
        self.btn_guardar.clicked.connect(self.accept)
        self.btn_cancelar.clicked.connect(self.reject)

        self.cargar_combo_javas()

    def cargar_lista_mods(self):
        self.lista_mods.clear()
        ruta_mods = os.path.join(self.ruta_instancia, "mods")
        mods = []
        if os.path.isdir(ruta_mods):
            for archivo in sorted(os.listdir(ruta_mods), key=str.lower):
                if archivo.lower().endswith((".jar", ".jar.disabled")):
                    mods.append(self.leer_info_mod(os.path.join(ruta_mods, archivo), archivo))
        for nombre, version, archivo in mods:
            texto = nombre
            if version:
                texto += f"  —  {version}"
            texto += f"  [{archivo}]"
            self.lista_mods.addItem(texto)
        self.lbl_cantidad_mods.setText(f"{len(mods)} mod(s) encontrado(s)")
        if not mods:
            self.lista_mods.addItem("Esta instancia no contiene mods.")

    def leer_info_mod(self, ruta, nombre_archivo):
        nombre = os.path.splitext(os.path.splitext(nombre_archivo)[0])[0]
        version = ""
        try:
            with zipfile.ZipFile(ruta) as jar:
                if "fabric.mod.json" in jar.namelist():
                    data = json.loads(jar.read("fabric.mod.json").decode("utf-8"))
                    return data.get("name") or data.get("id") or nombre, str(data.get("version", "")), nombre_archivo

                metadata = next(
                    (ruta_meta for ruta_meta in (
                        "META-INF/neoforge.mods.toml", "META-INF/mods.toml"
                    ) if ruta_meta in jar.namelist()),
                    None,
                )
                if metadata:
                    contenido = jar.read(metadata).decode("utf-8", errors="replace")
                    match_nombre = re.search(r'^\s*displayName\s*=\s*["\'](.+?)["\']', contenido, re.MULTILINE)
                    match_version = re.search(r'^\s*version\s*=\s*["\'](.+?)["\']', contenido, re.MULTILINE)
                    if match_nombre:
                        nombre = match_nombre.group(1)
                    if match_version and "${" not in match_version.group(1):
                        version = match_version.group(1)
        except (OSError, zipfile.BadZipFile, json.JSONDecodeError):
            pass
        return nombre, version, nombre_archivo

    def abrir_carpeta(self, ruta, crear=False):
        try:
            if crear:
                os.makedirs(ruta, exist_ok=True)
            if not os.path.isdir(ruta):
                QMessageBox.warning(self, "Carpeta no encontrada", f"No existe la carpeta:\n{ruta}")
                return
            QDesktopServices.openUrl(QUrl.fromLocalFile(ruta))
        except OSError as error:
            QMessageBox.critical(self, "No se pudo abrir la carpeta", str(error))

    def intentar_recuperar_metadatos_log(self):
        """Analiza el archivo log de FTB para recuperar el nombre e ID del modpack."""
        ruta_log = os.path.join(self.ruta_instancia, "ftb-server-installer.log")
        if not os.path.exists(ruta_log): return
        try:
            with open(ruta_log, "r", encoding="utf-8", errors="ignore") as f:
                contenido = f.read()
                # Buscamos Nombre e ID permitiendo saltos de línea y espacios (común en FTB Installer)
                # Buscamos el patrón: Name: ... (ID)
                m_mp = re.search(r"Name:\s*([\w\s\-\.]+?)\s*\((\d+)\)", contenido, re.MULTILINE)
                if m_mp:
                    self.ftb_nombre_real = m_mp.group(1).strip()
                    self.ftb_modpack_id = m_mp.group(2)
                
                # Intentamos también sacar el ID de versión si está ahí para mayor precisión
                m_v = re.search(r"Version:\s+.*?\s+\((\d+)\)", contenido)
                if m_v: self.version_log_id = m_v.group(1)
        except: pass

    def parsear_version_log(self):
        """Lee el log del instalador para extraer el ID de la versión instalada."""
        ruta_log = os.path.join(self.ruta_instancia, "ftb-server-installer.log")
        if not os.path.exists(ruta_log): return ""
        try:
            with open(ruta_log, "r", encoding="utf-8", errors="ignore") as f:
                contenido = f.read()
                match = re.search(r"Version:\s+.*?\s+\((\d+)\)", contenido)
                return match.group(1) if match else ""
        except: return ""

    def preparar_actualizacion(self):
        version_actual = self.ftb_version_id or self.parsear_version_log()
        self.solicitar_actualizacion.emit(self.ftb_nombre_real, str(self.ftb_modpack_id), version_actual)

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

    def _handle_remove_readonly(self, func, path, excinfo):
        """Manejador de errores para shutil.rmtree que quita el atributo de solo lectura."""
        os.chmod(path, stat.S_IWRITE)
        func(path)

    def eliminar_instancia_con_confirmacion(self):
        confirmacion = QMessageBox.question(
            self, "Confirmar Eliminación", 
            f"¿Estás completamente seguro de que deseas eliminar la instancia '{self.nombre_instancia}'?\n\n"
            "⚠️ Esta acción borrará permanentemente todos los archivos, mundos y mods.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No
        )
        if confirmacion == QMessageBox.StandardButton.Yes:
            try:
                if os.path.exists(self.ruta_instancia):
                    # Intentamos eliminar manejando archivos de solo lectura (común en JREs)
                    shutil.rmtree(self.ruta_instancia, onerror=self._handle_remove_readonly)
                
                QMessageBox.information(self, "Eliminado", "La instancia fue eliminada.")
                self.instancia_eliminada.emit()
                self.reject()
            except Exception as e:
                error_msg = str(e)
                if "Acceso denegado" in error_msg or "WinError 5" in error_msg:
                    error_msg = (
                        "Acceso Denegado. Esto suele ocurrir porque el servidor aún se está cerrando "
                        "o hay un proceso de Java usando la carpeta.\n\n"
                        "Por favor, asegúrate de que el servidor esté detenido y, si el error persiste, "
                        "revisa el Administrador de Tareas para cerrar cualquier proceso 'java.exe' activo."
                    )
                QMessageBox.critical(self, "Error al eliminar", f"{error_msg}")

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
            except Exception: pass
        index = self.combo_java.findData(self.java_seleccionado)
        if index != -1: self.combo_java.setCurrentIndex(index)

    def accept(self):
        nuevo_nombre = self.txt_nombre.text().strip()
        if not nuevo_nombre:
            QMessageBox.warning(self, "Nombre inválido", "El nombre de la instancia no puede estar vacío.")
            return
            
        # Validación básica de caracteres prohibidos en carpetas
        caracteres_invalidos = '<>:"/\\|?*'
        if any(c in nuevo_nombre for c in caracteres_invalidos):
            QMessageBox.warning(self, "Nombre inválido", f"El nombre contiene caracteres no permitidos: {caracteres_invalidos}")
            return

        if nuevo_nombre != self.nombre_instancia:
            ruta_padre = os.path.dirname(self.ruta_instancia)
            nueva_ruta = os.path.join(ruta_padre, nuevo_nombre)
            
            if os.path.exists(nueva_ruta):
                QMessageBox.warning(self, "Error", "Ya existe una carpeta con ese nombre.")
                return
                
            try:
                os.rename(self.ruta_instancia, nueva_ruta)
                self.ruta_instancia = nueva_ruta
                self.nombre_instancia = nuevo_nombre
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo renombrar la carpeta de la instancia:\n{e}")
                return
        
        self.grupo_instancia = self.combo_grupo.currentText().strip() or "No agrupado"
        super().accept()


class FTBDownloaderDialog(QDialog):
    def __init__(self, ruta_instancias_raiz, ruta_javas_raiz=None, ruta_update=None, modpack_id=None, version_actual=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📥 Descargar Servidor Oficial FTB")
        self.resize(550, 420)
        self.ruta_instancias_raiz = ruta_instancias_raiz
        self.ruta_javas_raiz = ruta_javas_raiz if ruta_javas_raiz else os.path.join(os.getcwd(), "javas")
        self.ruta_update = ruta_update
        self.modpack_id_update = modpack_id
        self.version_id_actual = version_actual
        self.worker = None

        self.lbl_buscar = QLabel("Buscar Modpack en Feed The Beast:")
        self.txt_buscar = QLineEdit()
        self.txt_buscar.setPlaceholderText("Ej: StoneBlock, Skies, Genesis...")
        self.btn_buscar = QPushButton("🔍 Buscar")
        
        self.lista_resultados = QListWidget()
        self.lbl_version = QLabel("Seleccionar Versión del Servidor:")
        self.combo_versiones = QComboBox()
        
        self.log_instalacion = QPlainTextEdit()
        self.log_instalacion.setReadOnly(True)
        self.log_instalacion.setMaximumHeight(120)
        self.log_instalacion.setStyleSheet("background-color: #1a1a1a; color: #00ff00; font-family: Consolas; font-size: 9pt;")
        # Auto-scroll al final
        self.log_instalacion.textChanged.connect(lambda: self.log_instalacion.ensureCursorVisible())

        self.input_interaccion = QLineEdit()
        self.input_interaccion.setPlaceholderText("Escribe 'y' y pulsa Enter si el instalador se detiene...")
        self.btn_enviar_interaccion = QPushButton("Enviar comando")

        self.btn_instalar = QPushButton("⚡ Crear Instancia y Descargar Servidor")
        self.btn_instalar.setEnabled(False)
        self.barra_progreso = QProgressBar()
        self.lbl_estado = QLabel("Estado: Listo.")

        layout_busqueda = QHBoxLayout()
        layout_busqueda.addWidget(self.txt_buscar)
        layout_busqueda.addWidget(self.btn_buscar)

        layout_interactivo = QHBoxLayout()
        layout_interactivo.addWidget(self.input_interaccion)
        layout_interactivo.addWidget(self.btn_enviar_interaccion)

        layout_principal = QVBoxLayout()
        layout_principal.addWidget(self.lbl_buscar)
        layout_principal.addLayout(layout_busqueda)
        layout_principal.addWidget(self.lista_resultados)
        layout_principal.addWidget(self.lbl_version)
        layout_principal.addWidget(self.combo_versiones)
        layout_principal.addWidget(self.log_instalacion)
        layout_principal.addLayout(layout_interactivo)
        layout_principal.addWidget(self.lbl_estado)
        layout_principal.addWidget(self.barra_progreso)
        layout_principal.addWidget(self.btn_instalar)
        self.setLayout(layout_principal)

        self.btn_buscar.clicked.connect(self.buscar_modpack_api)
        self.lista_resultados.itemSelectionChanged.connect(self.cargar_versiones_modpack)
        self.btn_instalar.clicked.connect(self.iniciar_descarga_ftb)
        self.btn_enviar_interaccion.clicked.connect(self.enviar_comando_manual)
        self.input_interaccion.returnPressed.connect(self.enviar_comando_manual)
        
        if self.modpack_id_update:
            self.cargar_modpack_especifico(self.modpack_id_update)
        else:
            self.cargar_catalogo_predeterminado()

    def set_busqueda_inicial(self, texto):
        self.txt_buscar.setText(texto)
        self.buscar_modpack_api()

    def cargar_catalogo_predeterminado(self):
        self.lbl_estado.setText("Cargando catálogo de servidores populares...")
        self.lista_resultados.clear()
        url_popular = "https://api.feed-the-beast.com/v1/modpacks/public/modpack/popular/installs/12"
        self._ejecutar_consulta_api(url_popular, es_busqueda=False)

    def cargar_modpack_especifico(self, modpack_id):
        self.lbl_estado.setText("Buscando actualizaciones disponibles...")
        url = f"https://api.feed-the-beast.com/v1/modpacks/public/modpack/{modpack_id}"
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                detalles = json.loads(response.read().decode('utf-8'))
                if "name" in detalles:
                    self.lista_resultados.clear()
                    item = QListWidgetItem(detalles["name"] + " (Actualización detectada)")
                    item.setData(Qt.ItemDataRole.UserRole, detalles)
                    self.lista_resultados.addItem(item)
                    self.lista_resultados.setCurrentItem(item)
        except Exception:
            self.lbl_estado.setText("Error al cargar datos de actualización.")

    def buscar_modpack_api(self):
        termino = self.txt_buscar.text().strip()
        if not termino: 
            self.cargar_catalogo_predeterminado()
            return
        self.lbl_estado.setText(f"Buscando '{termino}'...")
        self.lista_resultados.clear()
        self.combo_versiones.clear()
        self.btn_instalar.setEnabled(False)

        termino_inc = urllib.parse.quote(termino)
        url_busqueda = f"https://api.feed-the-beast.com/v1/modpacks/public/modpack/search/5?term={termino_inc}"
        self._ejecutar_consulta_api(url_busqueda, es_busqueda=True)

    def _ejecutar_consulta_api(self, url, es_busqueda=True):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'})
            with urllib.request.urlopen(req, timeout=10) as response:
                datos = json.loads(response.read().decode('utf-8'))
                lista_ids = []
                if isinstance(datos, dict):
                    lista_ids = datos.get("modpacks", []) or datos.get("packs", []) or datos.get("curse", [])
                elif isinstance(datos, list):
                    lista_ids = datos

                if lista_ids:
                    lista_ids = lista_ids[:12]
                    for mp_id in lista_ids:
                        try:
                            url_detalle = f"https://api.feed-the-beast.com/v1/modpacks/public/modpack/{mp_id}"
                            req_det = urllib.request.Request(url_detalle, headers={'User-Agent': 'Mozilla/5.0'})
                            with urllib.request.urlopen(req_det, timeout=3) as resp_det:
                                detalles = json.loads(resp_det.read().decode('utf-8'))
                                if "name" in detalles:
                                    item = QListWidgetItem(detalles["name"])
                                    item.setData(Qt.ItemDataRole.UserRole, detalles)
                                    self.lista_resultados.addItem(item)
                        except Exception: continue
                    msg = f"Se encontraron {self.lista_resultados.count()} modpacks." if es_busqueda else "Catálogo listo."
                    self.lbl_estado.setText(msg)
                else:
                    self.lbl_estado.setText("No se encontraron resultados.")
        except Exception as e:
            self.lbl_estado.setText("Error al conectar con FTB.")

    def cargar_versiones_modpack(self):
        self.combo_versiones.clear()
        item = self.lista_resultados.currentItem()
        if not item: return
        detalles = item.data(Qt.ItemDataRole.UserRole)
        versiones = list(detalles.get("versions", []))
        
        # Si estamos actualizando, filtramos para mostrar solo versiones posteriores
        if self.version_id_actual:
            try:
                v_id_actual = int(self.version_id_actual)
                versiones = [
                    version for version in versiones
                    if int(version.get("id", 0)) > v_id_actual
                ]
                self.lbl_version.setText(f"Nuevas versiones (ID actual: {v_id_actual}):")
            except: pass

        # Los IDs de FTB crecen con cada publicación. Ordenar siempre en descendente
        # garantiza que la versión más reciente sea la opción seleccionada por defecto.
        versiones.sort(key=lambda version: int(version.get("id", 0)), reverse=True)

        if not versiones:
            if self.version_id_actual: self.lbl_estado.setText("Ya tienes la versión más reciente instalada.")
            self.btn_instalar.setEnabled(False)
        else:
            for v in versiones:
                self.combo_versiones.addItem(f"Versión: {v.get('name')}", v)
            self.combo_versiones.setCurrentIndex(0)
            self.btn_instalar.setEnabled(True)

    def iniciar_descarga_ftb(self):
        item_mp = self.lista_resultados.currentItem()
        version_data = self.combo_versiones.currentData()
        if not item_mp or not version_data: return

        modpack_detalles = item_mp.data(Qt.ItemDataRole.UserRole)
        id_modpack = modpack_detalles["id"]
        # Sanitizamos el nombre del modpack y la versión para el nombre de la carpeta
        nombre_modpack = modpack_detalles["name"].replace(" ", "_").replace("/", "_").replace(":", "_")
        nombre_version = version_data["name"].replace(" ", "_").replace("/", "_").replace(":", "_")
        id_version = version_data["id"]

        # Usamos la URL oficial de la API v1 de FTB para el instalador de servidor en Windows
        url_descarga_exe = f"https://api.feed-the-beast.com/v1/modpacks/public/modpack/{id_modpack}/{id_version}/server/windows"
        
        # Definimos el nombre de la carpeta basado en modpack y versión
        nombre_carpeta_final = f"{nombre_modpack}_{nombre_version}"
        ruta_instancia_destino = os.path.join(self.ruta_instancias_raiz, nombre_carpeta_final)

        if self.ruta_update:
            confirmacion = QMessageBox.warning(
                self, "Confirmar Actualización",
                f"Se actualizará la instancia a la versión {version_data['name']}.\n\n"
                f"La carpeta se renombrará a: {nombre_carpeta_final}\n\n"
                "⚠️ IMPORTANTE: Haz un backup de tu mundo antes de continuar.\n"
                "¿Deseas proceder con la actualización?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if confirmacion == QMessageBox.StandardButton.No: return

            # Si el nombre cambia, intentamos renombrar la carpeta existente antes de descargar
            if self.ruta_update != ruta_instancia_destino:
                if os.path.exists(ruta_instancia_destino):
                    QMessageBox.critical(self, "Error", f"No se pudo renombrar porque ya existe una carpeta llamada '{nombre_carpeta_final}'.")
                    return
                try:
                    os.rename(self.ruta_update, ruta_instancia_destino)
                    self.ruta_update = ruta_instancia_destino
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"No se pudo renombrar la carpeta para la actualización:\n{e}")
                    return

        self.btn_instalar.setEnabled(False)
        self.btn_buscar.setEnabled(False)
        self.log_instalacion.clear()
        self.log_instalacion.appendPlainText("--- Iniciando Instalación ---")

        self.worker = FTBDownloadWorker(url_descarga_exe, ruta_instancia_destino, self.ruta_javas_raiz, id_modpack, id_version)
        self.worker.progreso.connect(self.barra_progreso.setValue)
        self.worker.estado.connect(self.lbl_estado.setText)
        self.worker.estado.connect(self.log_instalacion.appendPlainText)
        self.worker.finalizado.connect(lambda exito, msg: self.instalacion_ftb_finalizada(
            exito, msg, ruta_instancia_destino, nombre_carpeta_final,
            modpack_detalles, id_modpack, id_version
        ))
        self.worker.start()

    def enviar_comando_manual(self):
        comando = self.input_interaccion.text().strip()
        if comando and self.worker:
            self.worker.enviar_entrada(comando)
            self.input_interaccion.clear()
            self.log_instalacion.appendPlainText(f"> Enviado al instalador: {comando}")

    def instalacion_ftb_finalizada(self, exito, mensaje, ruta_instancia, nombre_instancia,
                                   modpack_detalles, id_modpack, id_version):
        self.btn_instalar.setEnabled(True)
        self.btn_buscar.setEnabled(True)
        self.barra_progreso.setValue(100 if exito else 0)

        if exito:
            archivo_arranque = "start.bat"
            if not os.path.exists(os.path.join(ruta_instancia, "start.bat")):
                archivo_arranque = "run.bat" if os.path.exists(os.path.join(ruta_instancia, "run.bat")) else "server.jar"

            config_path = os.path.join(ruta_instancia, "config_instancia.json")
            config_data = {}
            if os.path.exists(config_path):
                try:
                    with open(config_path, "r", encoding="utf-8") as f:
                        config_data = json.load(f)
                    if not isinstance(config_data, dict):
                        config_data = {}
                except (OSError, json.JSONDecodeError):
                    config_data = {}

            config_data.update({
                "archivo_arranque": archivo_arranque, 
                "java_especifico": config_data.get("java_especifico", "AUTO"),
                "ftb_nombre_real": modpack_detalles.get("name", ""),
                "ftb_modpack_id": id_modpack,
                "ftb_version_id": id_version,
            })
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=4)

            tipo_msg = "actualizada" if self.ruta_update else "creada"
            QMessageBox.information(self, "FTB Server Listo", f"Instancia '{nombre_instancia}' {tipo_msg} exitosamente.")
            self.accept()
        else:
            QMessageBox.critical(self, "Error de Instalación FTB", f"No se pudo completar la instalación:\n{mensaje}")

class ZipInstallerDialog(QDialog):
    def __init__(self, zip_path, destination_root_path, ruta_update=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📦 Instalar/Actualizar Servidor desde ZIP")
        self.resize(450, 250)
        self.zip_path = zip_path
        self.destination_root_path = destination_root_path
        self.ruta_update = ruta_update
        self.instance_name = ""
        self.worker = None

        self.lbl_zip_file = QLabel(f"Archivo ZIP seleccionado: <b>{os.path.basename(zip_path)}</b>")
        self.lbl_instance_name = QLabel("Nombre para la nueva instancia (carpeta):")
        self.txt_instance_name = QLineEdit()
        
        if self.ruta_update:
            self.instance_name = os.path.basename(self.ruta_update)
            self.txt_instance_name.setText(self.instance_name)
            self.txt_instance_name.setEnabled(False)
            self.lbl_estado = QLabel("Estado: Listo para actualizar archivos.")
        else:
            self.txt_instance_name.setPlaceholderText("Ej: MiServidorPersonalizado")
            self.lbl_estado = QLabel("Estado: Esperando nombre de instancia...")
        
        self.btn_instalar = QPushButton("Instalar")
        self.btn_cancelar = QPushButton("Cancelar")
        
        self.barra_progreso = QProgressBar()
        self.barra_progreso.setValue(0)

        layout_botones = QHBoxLayout()
        layout_botones.addStretch()
        layout_botones.addWidget(self.btn_instalar)
        layout_botones.addWidget(self.btn_cancelar)

        layout_principal = QVBoxLayout()
        layout_principal.addWidget(self.lbl_zip_file)
        layout_principal.addSpacing(10)
        layout_principal.addWidget(self.lbl_instance_name)
        layout_principal.addWidget(self.txt_instance_name)
        layout_principal.addSpacing(20)
        layout_principal.addWidget(self.lbl_estado)
        layout_principal.addWidget(self.barra_progreso)
        layout_principal.addSpacing(20)
        layout_principal.addLayout(layout_botones)
        self.setLayout(layout_principal)

        self.btn_instalar.clicked.connect(self.iniciar_instalacion_zip)
        self.btn_cancelar.clicked.connect(self.reject)

    def iniciar_instalacion_zip(self):
        self.instance_name = self.txt_instance_name.text().strip()
        if not self.instance_name:
            QMessageBox.warning(self, "Nombre de Instancia", "Por favor, ingresa un nombre para la instancia.")
            return
        
        invalid_chars = '<>:"/\\|?*'
        if any(c in self.instance_name for c in invalid_chars):
            QMessageBox.warning(self, "Nombre inválido", f"El nombre contiene caracteres no permitidos: {invalid_chars}")
            return

        if self.ruta_update:
            confirm = QMessageBox.warning(
                self, "Confirmar Actualización",
                "Se extraerán los archivos del ZIP sobre la carpeta actual.\n\n"
                "⚠️ IMPORTANTE: Haz un backup de tu mundo antes de continuar.\n"
                "¿Deseas proceder?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if confirm == QMessageBox.StandardButton.No: return

        self.btn_instalar.setEnabled(False)
        self.btn_cancelar.setEnabled(False)
        self.txt_instance_name.setReadOnly(True)
        
        self.worker = ZipExtractionWorker(self.zip_path, self.instance_name, self.destination_root_path, es_update=bool(self.ruta_update))
        self.worker.progreso.connect(self.barra_progreso.setValue)
        self.worker.estado.connect(self.lbl_estado.setText)
        self.worker.finalizado.connect(self.instalacion_zip_finalizada)
        self.worker.start()

    def instalacion_zip_finalizada(self, success, message, instance_path):
        self.btn_instalar.setEnabled(True)
        self.btn_cancelar.setEnabled(True)
        self.txt_instance_name.setReadOnly(False)
        if success:
            self.accept()
        else:
            QMessageBox.critical(self, "Error de Instalación ZIP", message)
            self.barra_progreso.setValue(0)
            self.lbl_estado.setText("Estado: Falló la instalación.")
