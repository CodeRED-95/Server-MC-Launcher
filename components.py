# components.py
import os
import shutil
import json
import urllib.request
import urllib.parse
from PyQt6.QtWidgets import (QDialog, QPlainTextEdit, QLineEdit, QPushButton, 
                             QHBoxLayout, QVBoxLayout, QLabel, QComboBox, 
                             QProgressBar, QMessageBox, QFileDialog, QListWidget, QListWidgetItem)
from PyQt6.QtCore import Qt, pyqtSignal
from workers import DownloaderWorker, FTBDownloadWorker

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


class FTBDownloaderDialog(QDialog):
    def __init__(self, ruta_instancias_raiz, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📥 Descargar Servidor Oficial FTB")
        self.resize(550, 400)
        self.ruta_instancias_raiz = ruta_instancias_raiz
        self.worker = None

        self.lbl_buscar = QLabel("Buscar Modpack en Feed The Beast:")
        self.txt_buscar = QLineEdit()
        self.txt_buscar.setPlaceholderText("Ej: FTB Genesis, Direwolf20, StoneBlock...")
        self.btn_buscar = QPushButton("🔍 Buscar")
        
        self.lista_resultados = QListWidget()
        
        self.lbl_version = QLabel("Seleccionar Versión del Servidor:")
        self.combo_versiones = QComboBox()
        
        self.btn_instalar = QPushButton("⚡ Crear Instancia y Descargar Servidor")
        self.btn_instalar.setEnabled(False)
        self.barra_progreso = QProgressBar()
        self.lbl_estado = QLabel("Estado: Esperando búsqueda...")

        layout_busqueda = QHBoxLayout()
        layout_busqueda.addWidget(self.txt_buscar)
        layout_busqueda.addWidget(self.btn_buscar)

        layout_principal = QVBoxLayout()
        layout_principal.addWidget(self.lbl_buscar)
        layout_principal.addLayout(layout_busqueda)
        layout_principal.addWidget(self.lista_resultados)
        layout_principal.addWidget(self.lbl_version)
        layout_principal.addWidget(self.combo_versiones)
        layout_principal.addWidget(self.lbl_estado)
        layout_principal.addWidget(self.barra_progreso)
        layout_principal.addWidget(self.btn_instalar)
        self.setLayout(layout_principal)

        self.btn_buscar.clicked.connect(self.buscar_modpack_api)
        self.lista_resultados.itemSelectionChanged.connect(self.cargar_versiones_modpack)
        self.btn_instalar.clicked.connect(self.iniciar_descarga_ftb)

    def buscar_modpack_api(self):
            termino = self.txt_buscar.text().strip()
            if not termino: return
            
            self.lbl_estado.setText("Buscando en los servidores de FTB...")
            self.lista_resultados.clear()
            self.combo_versiones.clear()
            self.btn_instalar.setEnabled(False)

            try:
                # Codificamos correctamente el término para la URL
                termino_inc = urllib.parse.quote(termino)
                url = f"https://api.modpacks.ch/public/modpack/search/5?term={termino_inc}"
                
                req = urllib.request.Request(url, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Accept': 'application/json'
                })
                
                with urllib.request.urlopen(req, timeout=10) as response:
                    res_body = response.read().decode('utf-8')
                    datos = json.loads(res_body)
                    
                    # La API puede devolver la lista directa o un diccionario con la clave 'modpacks'
                    lista_ids = []
                    if isinstance(datos, dict):
                        lista_ids = datos.get("modpacks", []) or datos.get("curse", [])
                    elif isinstance(datos, list):
                        lista_ids = datos

                    if lista_ids:
                        for mp_id in lista_ids[:15]: # Limitamos a los primeros 15 resultados para no saturar
                            try:
                                url_detalle = f"https://api.modpacks.ch/public/modpack/{mp_id}"
                                req_det = urllib.request.Request(url_detalle, headers={'User-Agent': 'Mozilla/5.0'})
                                with urllib.request.urlopen(req_det, timeout=5) as resp_det:
                                    detalles = json.loads(resp_det.read().decode('utf-8'))
                                    nombre = detalles.get("name", f"Modpack ID: {mp_id}")
                                    
                                    item = QListWidgetItem(nombre)
                                    # Guardamos los detalles completos en el item
                                    item.setData(Qt.ItemDataRole.UserRole, detalles)
                                    self.lista_resultados.addItem(item)
                            except Exception:
                                continue # Si un modpack falla en sus detalles, saltamos al siguiente
                                
                        self.lbl_estado.setText(f"Se encontraron {self.lista_resultados.count()} modpacks.")
                    else:
                        self.lbl_estado.setText("No se encontraron resultados. Intenta con un nombre más corto (ej: 'Unstable').")
                        
            except urllib.error.HTTPError as e:
                self.lbl_estado.setText(f"Error HTTP de la API: {e.code}")
                QMessageBox.warning(self, "Error de API", f"La API de FTB respondió con un código de error: {e.code}")
            except Exception as e:
                self.lbl_estado.setText("Error al conectar con la API de FTB.")
                QMessageBox.warning(self, "Error de Red", f"No se pudo completar la consulta: {e}")

    def cargar_versiones_modpack(self):
        self.combo_versiones.clear()
        item = self.lista_resultados.currentItem()
        if not item: return

        detalles = item.data(Qt.ItemDataRole.UserRole)
        versiones = detalles.get("versions", [])

        for v in versiones:
            self.combo_versiones.addItem(f"Versión: {v.get('name')}", v)
        
        if versiones:
            self.btn_instalar.setEnabled(True)

    def iniciar_descarga_ftb(self):
        item_mp = self.lista_resultados.currentItem()
        version_data = self.combo_versiones.currentData()
        if not item_mp or not version_data: return

        modpack_detalles = item_mp.data(Qt.ItemDataRole.UserRole)
        id_modpack = modpack_detalles["id"]
        nombre_modpack = modpack_detalles["name"].replace(" ", "_").replace("/", "_")
        id_version = version_data["id"]
        nombre_version = version_data["name"]

        url_descarga_exe = f"https://api.modpacks.ch/public/modpack/{id_modpack}/{id_version}/serverinstall/windows"

        nombre_carpeta_final = f"FTB_{nombre_modpack}_{nombre_version}"
        ruta_instancia_destino = os.path.join(self.ruta_instancias_raiz, nombre_carpeta_final)

        self.btn_instalar.setEnabled(False)
        self.btn_buscar.setEnabled(False)

        self.worker = FTBDownloadWorker(url_descarga_exe, ruta_instancia_destino, id_modpack, id_version)
        self.worker.progreso.connect(self.barra_progreso.setValue)
        self.worker.estado.connect(self.lbl_estado.setText)
        self.worker.finalizado.connect(lambda exito, msg: self.instalacion_ftb_finalizada(exito, msg, ruta_instancia_destino, nombre_carpeta_final))
        self.worker.start()

    def instalacion_ftb_finalizada(self, exito, mensaje, ruta_instancia, nombre_instancia):
        self.btn_instalar.setEnabled(True)
        self.btn_buscar.setEnabled(True)
        self.barra_progreso.setValue(100 if exito else 0)

        if exito:
            self.lbl_estado.setText("¡Instalación de FTB completada!")
            
            archivo_arranque = "start.bat"
            if not os.path.exists(os.path.join(ruta_instancia, "start.bat")):
                archivo_arranque = "run.bat" if os.path.exists(os.path.join(ruta_instancia, "run.bat")) else "server.jar"

            config_data = {
                "archivo_arranque": archivo_arranque,
                "java_especifico": "AUTO"
            }
            with open(os.path.join(ruta_instancia, "config_instancia.json"), "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=4)

            QMessageBox.information(self, "FTB Server Listo", f"Se ha creado e instalado la instancia '{nombre_instancia}' con éxito.")
            self.accept()
        else:
            self.lbl_estado.setText("Error en la instalación.")
            QMessageBox.critical(self, "Error de Instalación FTB", f"No se pudo completar la instalación:\n{mensaje}")