# components.py
import os
import shutil
import json
import urllib.request
import urllib.parse
import urllib.error
import webbrowser
from PyQt6.QtWidgets import (QDialog, QPlainTextEdit, QLineEdit, QPushButton, 
                             QHBoxLayout, QVBoxLayout, QLabel, QComboBox, 
                             QProgressBar, QMessageBox, QFileDialog, QListWidget, QListWidgetItem)
from PyQt6.QtCore import Qt, pyqtSignal, QRegularExpression
from PyQt6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor
from workers import DownloaderWorker, FTBDownloadWorker

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

                with urllib.request.urlopen(req) as response:
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

    def __init__(self, nombre_instancia, ruta_instancia, archivo_actual, java_actual, ruta_javas_raiz, parent=None):
        super().__init__(parent)
        self.nombre_instancia = nombre_instancia
        self.ruta_instancia = ruta_instancia
        self.archivo_seleccionado = archivo_actual
        self.java_seleccionado = java_actual
        self.ruta_javas_raiz = ruta_javas_raiz

        self.setWindowTitle(f"Configurar Instancia: {nombre_instancia}")
        self.resize(600, 360)

        self.lbl_nombre = QLabel("Nombre de la instancia (Carpeta):")
        self.txt_nombre = QLineEdit(self.nombre_instancia)
        self.txt_nombre.setPlaceholderText("Nombre de la carpeta en disco")

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
        layout_principal.addSpacing(20)
        layout_principal.addLayout(layout_botones)
        self.setLayout(layout_principal)

        self.btn_buscar_archivo.clicked.connect(self.seleccionar_archivo)
        self.btn_buscar_icon.clicked.connect(self.seleccionar_icono)
        self.btn_eliminar.clicked.connect(self.eliminar_instancia_con_confirmacion)
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
                    shutil.rmtree(self.ruta_instancia)
                QMessageBox.information(self, "Eliminado", "La instancia fue eliminada.")
                self.instancia_eliminada.emit()
                self.reject()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo eliminar:\n{e}")

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
        
        super().accept()


class FTBDownloaderDialog(QDialog):
    def __init__(self, ruta_instancias_raiz, ruta_javas_raiz=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📥 Descargar Servidor Oficial FTB")
        self.resize(550, 420)
        self.ruta_instancias_raiz = ruta_instancias_raiz
        self.ruta_javas_raiz = ruta_javas_raiz if ruta_javas_raiz else os.path.join(os.getcwd(), "javas")
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
        self.cargar_catalogo_predeterminado()

    def cargar_catalogo_predeterminado(self):
        self.lbl_estado.setText("Cargando catálogo de servidores populares...")
        self.lista_resultados.clear()
        url_popular = "https://api.feed-the-beast.com/v1/modpacks/public/modpack/popular/installs/12"
        self._ejecutar_consulta_api(url_popular, es_busqueda=False)

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
        versiones = detalles.get("versions", [])
        for v in versiones:
            self.combo_versiones.addItem(f"Versión: {v.get('name')}", v)
        if versiones: self.btn_instalar.setEnabled(True)

    def iniciar_descarga_ftb(self):
        item_mp = self.lista_resultados.currentItem()
        version_data = self.combo_versiones.currentData()
        if not item_mp or not version_data: return

        modpack_detalles = item_mp.data(Qt.ItemDataRole.UserRole)
        id_modpack = modpack_detalles["id"]
        nombre_modpack = modpack_detalles["name"].replace(" ", "_").replace("/", "_").replace(":", "_")
        id_version = version_data["id"]
        nombre_version = version_data["name"]

        # Usamos la URL oficial de la API v1 de FTB para el instalador de servidor en Windows
        url_descarga_exe = f"https://api.feed-the-beast.com/v1/modpacks/public/modpack/{id_modpack}/{id_version}/server/windows"
        nombre_carpeta_final = f"FTB_{nombre_modpack}_{nombre_version}"
        ruta_instancia_destino = os.path.join(self.ruta_instancias_raiz, nombre_carpeta_final)

        self.btn_instalar.setEnabled(False)
        self.btn_buscar.setEnabled(False)
        self.log_instalacion.clear()
        self.log_instalacion.appendPlainText("--- Iniciando Instalación ---")

        self.worker = FTBDownloadWorker(url_descarga_exe, ruta_instancia_destino, self.ruta_javas_raiz, id_modpack, id_version)
        self.worker.progreso.connect(self.barra_progreso.setValue)
        self.worker.estado.connect(self.lbl_estado.setText)
        self.worker.estado.connect(self.log_instalacion.appendPlainText)
        self.worker.finalizado.connect(lambda exito, msg: self.instalacion_ftb_finalizada(exito, msg, ruta_instancia_destino, nombre_carpeta_final))
        self.worker.start()

    def enviar_comando_manual(self):
        comando = self.input_interaccion.text().strip()
        if comando and self.worker:
            self.worker.enviar_entrada(comando)
            self.input_interaccion.clear()
            self.log_instalacion.appendPlainText(f"> Enviado al instalador: {comando}")

    def instalacion_ftb_finalizada(self, exito, mensaje, ruta_instancia, nombre_instancia):
        self.btn_instalar.setEnabled(True)
        self.btn_buscar.setEnabled(True)
        self.barra_progreso.setValue(100 if exito else 0)

        if exito:
            archivo_arranque = "start.bat"
            if not os.path.exists(os.path.join(ruta_instancia, "start.bat")):
                archivo_arranque = "run.bat" if os.path.exists(os.path.join(ruta_instancia, "run.bat")) else "server.jar"

            config_data = {"archivo_arranque": archivo_arranque, "java_especifico": "AUTO"}
            with open(os.path.join(ruta_instancia, "config_instancia.json"), "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=4)

            QMessageBox.information(self, "FTB Server Listo", f"Instancia '{nombre_instancia}' creada exitosamente.")
            self.accept()
        else:
            QMessageBox.critical(self, "Error de Instalación FTB", f"No se pudo completar la instalación:\n{mensaje}")