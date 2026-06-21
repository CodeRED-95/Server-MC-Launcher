# launcher.py
import os
import json
import struct
import zipfile
import ctypes
import re
from PyQt6.QtWidgets import (QMainWindow, QPushButton, QVBoxLayout, QHBoxLayout,
                             QWidget, QListWidget, QListWidgetItem, QLabel, 
                             QDialog, QMessageBox, QFileDialog, QGroupBox,
                             QCheckBox, QPlainTextEdit)
from PyQt6.QtCore import QProcess, QProcessEnvironment, Qt, QSize, QFileSystemWatcher
from PyQt6.QtGui import QIcon

from components import ConsoleWindow, ConfigGlobalDialog, ConfigInstanciaDialog, FTBDownloaderDialog, ZipInstallerDialog

class ServerLauncher(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Minecraft Server Launcher Grid Pro")
        self.resize(1120, 650)

        self.ARCHIVO_CONFIG_GLOBAL = os.path.join(os.path.dirname(__file__), "config.json")
        self.RUTA_ICONO_APP = os.path.join(os.path.dirname(__file__), "assets", "app_icon.png")
        self.ruta_instancias = ""
        self.ruta_javas_raiz = ""
        self.ruta_playit = ""
        self.playit_auto = True
        
        self.cargar_configuracion_global()
        if os.path.exists(self.RUTA_ICONO_APP):
            self.setWindowIcon(QIcon(self.RUTA_ICONO_APP))

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
                background-color: #1e1e1e; color: #ffffff;
                border: 1px solid #2d2d2d; border-radius: 6px; padding: 10px;
            }
            QListWidget::item {
                background-color: #2a2a2a; border-radius: 8px;
                padding: 8px; width: 110px; height: 120px;
            }
            QListWidget::item:selected { background-color: #007acc; color: white; }
            QListWidget::item:hover { background-color: #3a3a3a; }
        """)
        
        self.btn_iniciar = QPushButton("🚀 Iniciar Servidor")
        self.btn_config_instancia = QPushButton("🛠️ Configurar Instancia")
        self.btn_config_global = QPushButton("⚙️ Ajustes / Java")
        self.btn_descargar_ftb = QPushButton("🔥 Descargar FTB")
        self.btn_instalar_zip = QPushButton("📦 Instalar desde ZIP")
        self.btn_seleccionar_playit = QPushButton("📁 Elegir playit.exe")
        self.btn_playit = QPushButton("▶ Iniciar Playit")
        self.lbl_estado_playit = QLabel("Playit: detenido")
        self.chk_playit_auto = QCheckBox("Ejecutar junto al servidor")
        self.chk_playit_auto.setChecked(self.playit_auto)
        self.log_playit = QPlainTextEdit()
        self.log_playit.setReadOnly(True)
        self.log_playit.setMaximumHeight(150)
        self.log_playit.setPlaceholderText("Aquí aparecerá la salida de Playit y el enlace de registro.")
        self.log_playit.setStyleSheet(
            "background-color: #151515; color: #9cdcfe; font-family: Consolas; font-size: 8pt;"
        )
        
        estilo_botones = "QPushButton { padding: 8px; font-size: 10pt; font-weight: bold; }"
        self.btn_iniciar.setStyleSheet(estilo_botones)
        self.btn_config_instancia.setStyleSheet(estilo_botones)
        self.btn_config_global.setStyleSheet(estilo_botones)
        self.btn_descargar_ftb.setStyleSheet(estilo_botones)
        self.btn_instalar_zip.setStyleSheet(estilo_botones)
        self.btn_seleccionar_playit.setStyleSheet(estilo_botones)
        self.btn_playit.setStyleSheet(estilo_botones)

        grupo_servidor = QGroupBox("Servidor")
        layout_servidor = QVBoxLayout(grupo_servidor)
        layout_servidor.addWidget(self.btn_iniciar)
        layout_servidor.addWidget(self.btn_config_instancia)

        grupo_instalacion = QGroupBox("Instalación")
        layout_instalacion = QVBoxLayout(grupo_instalacion)
        layout_instalacion.addWidget(self.btn_descargar_ftb)
        layout_instalacion.addWidget(self.btn_instalar_zip)

        grupo_playit = QGroupBox("Red pública con Playit")
        layout_playit = QVBoxLayout(grupo_playit)
        layout_playit.addWidget(self.lbl_estado_playit)
        layout_playit.addWidget(self.chk_playit_auto)
        layout_playit.addWidget(self.btn_seleccionar_playit)
        layout_playit.addWidget(self.btn_playit)
        layout_playit.addWidget(self.log_playit)

        barra_lateral = QWidget()
        barra_lateral.setFixedWidth(285)
        layout_lateral = QVBoxLayout(barra_lateral)
        layout_lateral.setContentsMargins(8, 0, 0, 0)
        layout_lateral.addWidget(grupo_servidor)
        layout_lateral.addWidget(grupo_instalacion)
        layout_lateral.addWidget(grupo_playit)
        layout_lateral.addStretch()
        layout_lateral.addWidget(self.btn_config_global)

        layout_contenido = QHBoxLayout()
        layout_contenido.addWidget(self.lista_servidores, stretch=1)
        layout_contenido.addWidget(barra_lateral)

        layout_principal = QVBoxLayout()
        layout_principal.addWidget(self.lbl_instancias)
        layout_principal.addLayout(layout_contenido)

        container = QWidget()
        container.setLayout(layout_principal)
        self.setCentralWidget(container)

        self.proceso_server = QProcess(self)
        self.proceso_playit = QProcess(self)
        self.instancia_actual = None
        self.proceso_server.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.proceso_playit.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        
        self.ventana_consola = None

        self.btn_iniciar.clicked.connect(self.controlar_servidor)
        self.btn_config_global.clicked.connect(self.abrir_configuracion_global)
        self.btn_config_instancia.clicked.connect(self.abrir_configuracion_instancia)
        self.btn_descargar_ftb.clicked.connect(self.abrir_descargador_ftb)
        self.btn_instalar_zip.clicked.connect(self.abrir_instalador_zip)
        self.btn_seleccionar_playit.clicked.connect(self.seleccionar_ejecutable_playit)
        self.btn_playit.clicked.connect(self.controlar_playit)
        self.chk_playit_auto.toggled.connect(self.guardar_preferencia_playit)
        self.lista_servidores.currentItemChanged.connect(self.actualizar_estado_botones)
        
        self.proceso_server.readyRead.connect(self.leer_consola)
        self.proceso_server.finished.connect(self.servidor_terminado)
        self.proceso_server.stateChanged.connect(self.estado_servidor_cambiado)
        self.proceso_server.errorOccurred.connect(self.error_proceso_servidor)
        self.proceso_playit.readyRead.connect(self.leer_salida_playit)
        self.proceso_playit.stateChanged.connect(self.actualizar_estado_playit)
        self.proceso_playit.errorOccurred.connect(self.error_proceso_playit)

        # Sistema de actualización automática: Observador de la carpeta de instancias
        self.watcher = QFileSystemWatcher()
        if os.path.exists(self.ruta_instancias):
            self.watcher.addPath(self.ruta_instancias)
        self.watcher.directoryChanged.connect(self.cargar_instancias)

        self.cargar_instancias()

    def cargar_configuracion_global(self):
        if os.path.exists(self.ARCHIVO_CONFIG_GLOBAL):
            try:
                with open(self.ARCHIVO_CONFIG_GLOBAL, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.ruta_instancias = data.get("ruta_instancias", "")
                    self.ruta_javas_raiz = data.get("ruta_javas_raiz", "")
                    self.ruta_playit = data.get("ruta_playit", "")
                    self.playit_auto = data.get("playit_auto", True)
            except Exception: pass
        
        if not self.ruta_instancias or not os.path.isdir(self.ruta_instancias):
            self.ruta_instancias = os.path.join(os.path.dirname(__file__), "instancias")
        os.makedirs(self.ruta_instancias, exist_ok=True)
        
        if not self.ruta_javas_raiz or not os.path.isdir(self.ruta_javas_raiz):
            self.ruta_javas_raiz = os.path.join(os.path.dirname(__file__), "javas")
        os.makedirs(self.ruta_javas_raiz, exist_ok=True)
                
        self.guardar_configuracion_global()

    def guardar_configuracion_global(self):
        data = {
            "ruta_instancias": self.ruta_instancias,
            "ruta_javas_raiz": self.ruta_javas_raiz,
            "ruta_playit": self.ruta_playit,
            "playit_auto": self.playit_auto,
        }
        with open(self.ARCHIVO_CONFIG_GLOBAL, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    def guardar_preferencia_playit(self, activado):
        self.playit_auto = activado
        self.guardar_configuracion_global()

    def seleccionar_ejecutable_playit(self):
        ruta_inicial = os.path.dirname(self.ruta_playit) if self.ruta_playit else ""
        ruta, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar ejecutable de Playit",
            ruta_inicial,
            "Playit (playit*.exe);;Ejecutables (*.exe);;Todos los archivos (*.*)",
        )
        if ruta:
            self.ruta_playit = ruta
            self.guardar_configuracion_global()
            self.lbl_estado_playit.setText(f"Playit: listo ({os.path.basename(ruta)})")

    def controlar_playit(self):
        if self.proceso_playit.state() == QProcess.ProcessState.NotRunning:
            self.iniciar_playit(mostrar_error=True)
        else:
            self.detener_playit()

    def iniciar_playit(self, mostrar_error=False):
        if self.proceso_playit.state() != QProcess.ProcessState.NotRunning:
            return
        if not self.ruta_playit or not os.path.isfile(self.ruta_playit):
            mensaje = "Selecciona primero el ejecutable playit.exe."
            self.lbl_estado_playit.setText(f"Playit: {mensaje}")
            if mostrar_error:
                QMessageBox.warning(self, "Playit no configurado", mensaje)
            return

        self.log_playit.clear()
        self.log_playit.appendPlainText("[Launcher] Iniciando Playit...")
        self.proceso_playit.setWorkingDirectory(os.path.dirname(self.ruta_playit))
        self.proceso_playit.start(self.ruta_playit, [])

    def detener_playit(self):
        if self.proceso_playit.state() != QProcess.ProcessState.NotRunning:
            self.log_playit.appendPlainText("[Launcher] Deteniendo Playit...")
            self.proceso_playit.terminate()

    def leer_salida_playit(self):
        data = self.proceso_playit.readAll().data()
        try:
            texto = data.decode("utf-8")
        except UnicodeDecodeError:
            texto = data.decode("cp1252", errors="replace")
        if texto.strip():
            self.log_playit.appendPlainText(texto.rstrip())

    def actualizar_estado_playit(self, estado):
        ejecutando = estado != QProcess.ProcessState.NotRunning
        self.btn_seleccionar_playit.setEnabled(not ejecutando)
        self.btn_playit.setText("■ Detener Playit" if ejecutando else "▶ Iniciar Playit")
        if estado == QProcess.ProcessState.Starting:
            self.lbl_estado_playit.setText("Playit: iniciando...")
        elif estado == QProcess.ProcessState.Running:
            self.lbl_estado_playit.setText("Playit: conectado")
        else:
            self.lbl_estado_playit.setText("Playit: detenido")

    def error_proceso_playit(self, error):
        if error == QProcess.ProcessError.FailedToStart:
            detalle = self.proceso_playit.errorString()
            self.log_playit.appendPlainText(f"[Launcher] No se pudo iniciar Playit: {detalle}")
            self.lbl_estado_playit.setText("Playit: error al iniciar")

    def estado_servidor_cambiado(self, estado):
        self.actualizar_estado_botones()
        if not self.playit_auto:
            return
        if estado == QProcess.ProcessState.Running:
            self.iniciar_playit(mostrar_error=False)
        elif estado == QProcess.ProcessState.NotRunning:
            self.detener_playit()

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
            except Exception: pass
        
        if not archivo:
            for opcion in ["start.bat", "run.bat", "server.jar"]:
                if os.path.exists(os.path.join(ruta_servidor, opcion)):
                    archivo = opcion
                    break
        return archivo, java_esp

    def guardar_datos_instancia(self, ruta_servidor, archivo, java_esp, **kwargs):
        ruta_json = os.path.join(ruta_servidor, "config_instancia.json")
        data = {}
        # Cargamos datos existentes para no sobrescribir metadatos de FTB
        if os.path.exists(ruta_json):
            try:
                with open(ruta_json, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except: pass
        
        data.update({
            "archivo_arranque": archivo,
            "java_especifico": java_esp
        })
        data.update(kwargs)

        with open(ruta_json, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    def abrir_configuracion_global(self):
        dialogo = ConfigGlobalDialog(self.ruta_instancias, self.ruta_javas_raiz, self)
        if dialogo.exec() == QDialog.DialogCode.Accepted:
            # Actualizamos el observador si la ruta cambió
            if self.ruta_instancias != dialogo.ruta_instancias:
                if self.ruta_instancias in self.watcher.directories():
                    self.watcher.removePath(self.ruta_instancias)
                if os.path.exists(dialogo.ruta_instancias):
                    self.watcher.addPath(dialogo.ruta_instancias)

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
        # Ya no es estrictamente necesario conectar instancia_eliminada porque el Watcher lo detectará,
        # pero lo dejamos por seguridad.
        dialogo.instancia_eliminada.connect(self.cargar_instancias)
        
        def manejar_actualizacion(nombre_modpack, mid, vid):
            dialogo.done(QDialog.DialogCode.Rejected)
            self.abrir_descargador_ftb(busqueda=nombre_modpack, ruta_update=ruta_servidor, modpack_id=mid, version_actual=vid)

        dialogo.solicitar_actualizacion.connect(manejar_actualizacion)
        
        def manejar_actualizacion_zip():
            dialogo.done(QDialog.DialogCode.Rejected)
            self.abrir_instalador_zip(ruta_update=ruta_servidor)

        dialogo.solicitar_actualizacion_zip.connect(manejar_actualizacion_zip)

        if dialogo.exec() == QDialog.DialogCode.Accepted:
            # Usamos la ruta del diálogo por si se renombró la carpeta durante la configuración
            self.guardar_datos_instancia(
                dialogo.ruta_instancia, 
                dialogo.archivo_seleccionado, 
                dialogo.combo_java.currentData(),
                ftb_nombre_real=dialogo.ftb_nombre_real,
                ftb_modpack_id=dialogo.ftb_modpack_id
            )
            # Forzamos una recarga para actualizar el texto en la cuadrícula inmediatamente
            self.cargar_instancias()

    def abrir_descargador_ftb(self, busqueda=None, ruta_update=None, modpack_id=None, version_actual=None):
        # Verificación preventiva de permisos de Administrador en Windows
        if os.name == 'nt':
            try:
                is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
            except:
                is_admin = False
                
            if not is_admin:
                QMessageBox.warning(
                    self, "Atención: Sin permisos", 
                    "El instalador de FTB requiere permisos de Administrador para funcionar.\n\n"
                    "IMPORTANTE: Haz click derecho en el acceso directo del programa y selecciona "
                    "'Ejecutar como administrador' antes de intentar descargar."
                )

        dialogo = FTBDownloaderDialog(self.ruta_instancias, self.ruta_javas_raiz, ruta_update, 
                                      modpack_id=modpack_id, version_actual=version_actual, parent=self)
        if busqueda and not isinstance(busqueda, bool):
            dialogo.set_busqueda_inicial(busqueda)
        dialogo.exec() # El watcher actualizará la lista en cuanto se cree la carpeta de la instancia

    def abrir_instalador_zip(self, ruta_update=None):
        # 1. Seleccionar archivo ZIP
        zip_file, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar Archivo ZIP del Servidor", "", "Archivos ZIP (*.zip);;Todos los archivos (*.*)"
        )
        if not zip_file: return

        # 2. Abrir diálogo para nombre de instancia y descompresión
        dialogo = ZipInstallerDialog(zip_file, self.ruta_instancias, ruta_update=ruta_update, parent=self)
        if dialogo.exec() == QDialog.DialogCode.Accepted:
            QMessageBox.information(
                self, "Instalación Completada",
                f"La instancia '{dialogo.instance_name}' ha sido instalada correctamente desde el ZIP."
            )
            self.cargar_instancias()
        else:
            QMessageBox.warning(self, "Instalación Cancelada", "La instalación desde ZIP fue cancelada o falló.")

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
                        if os.path.exists(ruta_icon): item.setIcon(QIcon(ruta_icon))
                        else: item.setIcon(QIcon.fromTheme("folder-remote"))
                        
                        self.lista_servidores.addItem(item)
            except Exception: pass
        self.actualizar_estado_botones()

    def actualizar_estado_botones(self, *_args):
        tiene_seleccion = self.lista_servidores.currentItem() is not None
        en_ejecucion = self.proceso_server.state() != QProcess.ProcessState.NotRunning
        self.btn_iniciar.setEnabled(tiene_seleccion or en_ejecucion)
        self.btn_config_instancia.setEnabled(tiene_seleccion and not en_ejecucion)
        self.btn_config_global.setEnabled(not en_ejecucion)
        self.btn_descargar_ftb.setEnabled(not en_ejecucion)
        self.btn_instalar_zip.setEnabled(not en_ejecucion)
        self.lista_servidores.setEnabled(not en_ejecucion)

    def detectar_version_java_de_jar(self, ruta_jar):
        """Detecta la versión de Java escaneando las clases del JAR y tomando la más alta requerida."""
        if not os.path.exists(ruta_jar): return 17
        max_java = 8
        try:
            with zipfile.ZipFile(ruta_jar, 'r') as z:
                count = 0
                for name in z.namelist():
                    if name.endswith('.class'):
                        with z.open(name) as f:
                            if f.read(4) == b'\xca\xfe\xba\xbe':
                                f.read(2) # minor
                                major = struct.unpack('>H', f.read(2))[0]
                                java_v = major - 44 # 52=8, 61=17, 65=21...
                                if java_v > max_java: max_java = java_v
                        count += 1
                        if count > 50: break # Escaneamos una muestra para no penalizar el rendimiento
            
            # Ajustamos a las versiones estándar de Minecraft
            if max_java <= 8: return 8
            if max_java <= 17: return 17
            return 21
        except Exception: 
            return 17

    def escanear_versiones_en_carpeta_javas(self):
        javas_disponibles = {}
        if not self.ruta_javas_raiz or not os.path.exists(self.ruta_javas_raiz): return javas_disponibles
        
        for raiz, directorios, archivos in os.walk(self.ruta_javas_raiz):
            if "java.exe" in archivos:
                ruta_exe = os.path.join(raiz, "java.exe")
                v = self.obtener_version_de_binario(ruta_exe)
                if v: javas_disponibles[v] = ruta_exe
        return javas_disponibles

    def obtener_version_de_binario(self, ruta_exe):
        p = QProcess()
        p.start(ruta_exe, ["-version"])
        if not p.waitForFinished(3000):
            p.kill()
            p.waitForFinished(1000)
            return None
        output = bytes(p.readAllStandardError()).decode("utf-8", errors="replace")
        output += bytes(p.readAllStandardOutput()).decode("utf-8", errors="replace")
        match = re.search(r'version\s+"(?:1\.)?(\d+)', output, re.IGNORECASE)
        if match:
            return int(match.group(1))
        return None

    def verificar_y_aceptar_eula(self, ruta_servidor):
        """Busca el archivo eula.txt y solicita aceptación si detecta eula=false."""
        ruta_eula = os.path.join(ruta_servidor, "eula.txt")
        if not os.path.exists(ruta_eula):
            # Si no existe, permitimos el arranque para que el server lo genere
            return True
            
        try:
            with open(ruta_eula, "r", encoding="utf-8") as f:
                lineas = f.readlines()
            
            if any("eula=false" in linea.lower() for linea in lineas):
                respuesta = QMessageBox.question(
                    self, "Aceptar EULA de Minecraft",
                    "Para ejecutar el servidor, debes aceptar los términos de la EULA de Mojang.\n\n"
                    "¿Deseas aceptar el Contrato de Licencia (eula.txt) ahora?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                
                if respuesta == QMessageBox.StandardButton.Yes:
                    with open(ruta_eula, "w", encoding="utf-8") as f:
                        for linea in lineas:
                            if "eula=false" in linea.lower():
                                f.write("eula=true\n")
                            else:
                                f.write(linea)
                    return True
                else:
                    return False # El usuario rechazó, no iniciamos el server
        except Exception as e:
            print(f"Error al procesar EULA: {e}")
            
        return True

    def seleccionar_mejor_java(self, ruta_servidor):
        version_requerida = 17
        
        # Si existe user_jvm_args.txt, es un servidor de Forge 1.17+ (Requiere 17 o 21)
        es_forge_moderno = os.path.exists(os.path.join(ruta_servidor, "user_jvm_args.txt"))

        jar_principal = os.path.join(ruta_servidor, "server.jar")
        if not os.path.exists(jar_principal):
            for f in os.listdir(ruta_servidor):
                if f.endswith(".jar") and ("forge" in f or "fabric" in f or "paper" in f or "server" in f):
                    jar_principal = os.path.join(ruta_servidor, f)
                    break
                    
        if os.path.exists(jar_principal):
            version_requerida = self.detectar_version_java_de_jar(jar_principal)
            
        # Si es Forge moderno, nunca permitimos bajar de Java 17
        if es_forge_moderno and version_requerida < 17:
            version_requerida = 17
            
        diccionario_javas = self.escanear_versiones_en_carpeta_javas()
        if not diccionario_javas: return f"ERROR_VACIO:{version_requerida}"
        if version_requerida in diccionario_javas: return diccionario_javas[version_requerida]
            
        return f"ERROR_INCOMPATIBLE:{version_requerida}"

    def detener_servidor_desde_consola(self):
        if self.proceso_server.state() == QProcess.ProcessState.Running:
            if self.ventana_consola:
                self.ventana_consola.consola.appendPlainText("\n[Launcher] Detención solicitada desde la terminal...")
            self.proceso_server.write(b"stop\n")

    def controlar_servidor(self):
        if self.proceso_server.state() == QProcess.ProcessState.NotRunning:
            item_seleccionado = self.lista_servidores.currentItem()
            if not item_seleccionado: return

            nombre_carpeta = item_seleccionado.text()
            ruta_servidor = os.path.join(self.ruta_instancias, nombre_carpeta)
            
            # Verificación proactiva del EULA antes de lanzar el proceso
            if not self.verificar_y_aceptar_eula(ruta_servidor):
                return

            ejecutable, java_especifico = self.obtener_datos_instancia(ruta_servidor)
            
            if java_especifico == "AUTO" or not java_especifico:
                java_exe_real = self.seleccionar_mejor_java(ruta_servidor)
            else:
                java_exe_real = None
                for raiz, _, archivos in os.walk(os.path.join(self.ruta_javas_raiz, java_especifico)):
                    if "java.exe" in archivos:
                        java_exe_real = os.path.join(raiz, "java.exe")
                        break

            if isinstance(java_exe_real, str) and java_exe_real.startswith("ERROR_VACIO"):
                version_necesitada = java_exe_real.split(":")[1]
                QMessageBox.critical(
                    self, "Falta Entorno Java", 
                    f"La instancia '{nombre_carpeta}' requiere **Java {version_necesitada}** para iniciar, "
                    f"pero tu carpeta de entornos portables está vacía.\n\n"
                    f"Solución: Ve a 'Ajustes / Java' y descarga e instala **Java {version_necesitada}**."
                )
                return
                
            if isinstance(java_exe_real, str) and java_exe_real.startswith("ERROR_INCOMPATIBLE"):
                version_necesitada = java_exe_real.split(":")[1]
                QMessageBox.critical(
                    self, "Versión Incompatible Detectada", 
                    f"Análisis del archivo de arranque:\n"
                    f"➔ Esta instancia requiere estrictamente **Java {version_necesitada}**.\n\n"
                    f"Estado actual: Tienes otras versiones descargadas, pero ninguna coincide con la versión {version_necesitada}.\n\n"
                    f"Solución:\n"
                    f"1. Abre 'Ajustes / Java' y descarga **Java {version_necesitada}**.\n"
                    f"2. O de lo contrario, ve a 'Configurar Instancia' y fuerza un Java fijo de los que posees."
                )
                return

            if java_exe_real is None:
                QMessageBox.critical(self, "Entorno no encontrado", "No se pudo encontrar un entorno ejecutable válido.")
                return

            if not ejecutable:
                QMessageBox.critical(self, "Falta Ejecutable", "No se detectó ningún script de inicio (.bat) o archivo .jar principal.")
                return

            self.instancia_actual = nombre_carpeta
            self.ventana_consola = ConsoleWindow(nombre_carpeta, self)
            self.ventana_consola.consola.appendPlainText(f"[Launcher] Iniciando con binario: {java_exe_real}")
            self.ventana_consola.input_comando.returnPressed.connect(self.enviar_comando_servidor)
            self.ventana_consola.solicitar_stop.connect(self.detener_servidor_desde_consola)
            self.ventana_consola.show()

            env = QProcessEnvironment.systemEnvironment()
            env.insert("PATH", os.path.dirname(java_exe_real) + os.path.pathsep + env.value("PATH"))
            
            # Inyectamos JAVA_HOME (es el padre de la carpeta bin)
            java_home = os.path.dirname(os.path.dirname(java_exe_real))
            env.insert("JAVA_HOME", java_home)
            
            self.proceso_server.setProcessEnvironment(env)
            self.proceso_server.setWorkingDirectory(ruta_servidor)

            if ejecutable.endswith(".bat"):
                comando = "cmd.exe"
                argumentos = ["/c", ejecutable]
                # Solo añadimos nogui si no es el instalador inicial de un modpack (ZIP)
                if ejecutable != "startserver.bat":
                    argumentos.append("nogui")
            else:
                comando = java_exe_real
                # Forzamos nogui estrictamente como argumento independiente para el archivo .jar
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
        try: texto = data.decode("utf-8")
        except UnicodeDecodeError: texto = data.decode("cp1252", errors="replace")
        
        if self.ventana_consola:
            # Detección multilingüe de la pausa de Windows (.bat)
            prompts_pausa = [
                "Presione una tecla para continuar",
                "Press any key to continue",
                "Appuyez sur une touche pour continuer"
            ]
            
            if any(p in texto for p in prompts_pausa):
                self.proceso_server.write(b"\n")
            else:
                # Filtramos líneas que son ecos del comando pause para limpiar el log final
                if not texto.strip().endswith(">pause"):
                    self.ventana_consola.consola.appendPlainText(texto.rstrip())

    def servidor_terminado(self):
        if self.ventana_consola:
            # Obtenemos el código de salida para informar al usuario
            exit_code = self.proceso_server.exitCode()
            mensaje = "\n[Launcher] El servidor se ha detenido correctamente." if exit_code == 0 else f"\n[Launcher] EL SERVIDOR SE CERRÓ CON ERRORES (Código: {exit_code})"
            self.ventana_consola.consola.appendPlainText(mensaje)
            
            # Cambiamos el botón de detener para que ahora sirva para cerrar la ventana manualmente
            self.ventana_consola.btn_stop_consola.setText("❌ Cerrar Ventana de Terminal")
            self.ventana_consola.btn_stop_consola.setStyleSheet("background-color: #4a4a4a; color: white; padding: 6px;")
            try:
                self.ventana_consola.btn_stop_consola.clicked.disconnect()
                self.ventana_consola.btn_stop_consola.clicked.connect(self.ventana_consola.close)
            except: pass

        # Lógica de transición post-instalación (ZIP): de startserver.bat a run.bat
        if self.instancia_actual:
            ruta_servidor = os.path.join(self.ruta_instancias, self.instancia_actual)
            archivo_actual, java_actual = self.obtener_datos_instancia(ruta_servidor)
            if archivo_actual == "startserver.bat":
                if os.path.exists(os.path.join(ruta_servidor, "run.bat")):
                    self.guardar_datos_instancia(ruta_servidor, "run.bat", java_actual)
                    if self.ventana_consola:
                        self.ventana_consola.consola.appendPlainText("\n[Launcher] Configuración de arranque actualizada: se detectó 'run.bat' tras la instalación.")

        self.btn_iniciar.setText("🚀 Iniciar Servidor")
        self.instancia_actual = None
        self.actualizar_estado_botones()

    def error_proceso_servidor(self, error):
        if error != QProcess.ProcessError.FailedToStart:
            return
        detalle = self.proceso_server.errorString()
        if self.ventana_consola:
            self.ventana_consola.consola.appendPlainText(
                f"\n[Launcher] No se pudo iniciar el proceso: {detalle}"
            )
        QMessageBox.critical(self, "Error al iniciar", f"No se pudo iniciar el servidor:\n{detalle}")
        self.btn_iniciar.setText("🚀 Iniciar Servidor")
        self.instancia_actual = None
        self.actualizar_estado_botones()

    def closeEvent(self, event):
        if self.proceso_server.state() != QProcess.ProcessState.NotRunning:
            QMessageBox.warning(
                self,
                "Servidor en ejecución",
                "Detén el servidor y espera a que termine de guardar el mundo antes de cerrar el launcher.",
            )
            event.ignore()
            return

        if self.proceso_playit.state() != QProcess.ProcessState.NotRunning:
            self.proceso_playit.terminate()
            if not self.proceso_playit.waitForFinished(2000):
                self.proceso_playit.kill()
                self.proceso_playit.waitForFinished(1000)
        super().closeEvent(event)

    def keyPressEvent(self, event):
        """Captura la pulsación de teclas a nivel global en la ventana principal."""
        # Si el usuario presiona la tecla F5
        if event.key() == Qt.Key.Key_F5:
            # Volvemos a ejecutar la función que escanea la carpeta y refresca la UI
            self.cargar_instancias() 
            # Marcamos el evento como aceptado para que no se propague
            event.accept()
        else:
            # Para cualquier otra tecla, mantenemos el comportamiento normal
            super().keyPressEvent(event)
