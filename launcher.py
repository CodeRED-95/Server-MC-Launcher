# launcher.py
import os
import json
import struct
import zipfile
import ctypes
import re
from PyQt6.QtWidgets import (QMainWindow, QPushButton, QVBoxLayout, QHBoxLayout,
                             QWidget, QLabel,
                             QDialog, QMessageBox, QFileDialog, QGroupBox,
                             QCheckBox, QPlainTextEdit, QProgressBar, QInputDialog,
                             QComboBox, QApplication)
from PyQt6.QtCore import QProcess, QProcessEnvironment, Qt, QFileSystemWatcher
from PyQt6.QtGui import QIcon

from components import ConsoleWindow, ConfigGlobalDialog, ConfigInstanciaDialog, FTBDownloaderDialog, ZipInstallerDialog
from server_grid import GroupedServerGrid
from workers import PlayitDownloadWorker
from instance_creator import CreateServerDialog

class ServerLauncher(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Minecraft Server Launcher Grid Pro")
        self.resize(1120, 650)

        self.ARCHIVO_CONFIG_GLOBAL = os.path.join(os.path.dirname(__file__), "config.json")
        self.RUTA_ICONO_APP = os.path.join(os.path.dirname(__file__), "assets", "app_icon.png")
        self.RUTA_PLAYIT_INTERNO = os.path.join(os.path.dirname(__file__), "tools", "playit", "playit.exe")
        self.ruta_instancias = ""
        self.ruta_javas_raiz = ""
        self.ruta_playit = ""
        self.playit_auto = True
        self.tema = "oscuro"
        
        self.cargar_configuracion_global()
        if os.path.isfile(self.RUTA_PLAYIT_INTERNO) and not os.path.isfile(self.ruta_playit):
            self.ruta_playit = self.RUTA_PLAYIT_INTERNO
            self.guardar_configuracion_global()
        if os.path.exists(self.RUTA_ICONO_APP):
            self.setWindowIcon(QIcon(self.RUTA_ICONO_APP))

        self.lbl_instancias = QLabel("Instancias de Servidores disponibles:")
        self.lbl_instancias.setStyleSheet("font-weight: bold; font-size: 11pt;")
        
        self.lista_servidores = GroupedServerGrid()
        
        self.btn_iniciar = QPushButton("🚀 Iniciar Servidor")
        self.btn_agregar_instancia = QPushButton("➕ Añadir Instancia")
        self.btn_config_instancia = QPushButton("🛠️ Configurar Instancia")
        self.btn_agrupar_instancia = QPushButton("🏷 Agrupar / Mover")
        self.btn_config_global = QPushButton("⚙️ Ajustes / Java")
        self.btn_descargar_ftb = QPushButton("🔥 Descargar FTB")
        self.btn_instalar_zip = QPushButton("📦 Instalar desde ZIP")
        self.btn_seleccionar_playit = QPushButton("📁 Elegir playit.exe")
        self.btn_instalar_playit = QPushButton("⬇ Instalar / Actualizar Playit")
        self.btn_playit = QPushButton("▶ Iniciar Playit")
        self.lbl_estado_playit = QLabel("Playit: detenido")
        self.lbl_claim_playit = QLabel()
        self.lbl_claim_playit.setOpenExternalLinks(True)
        self.lbl_claim_playit.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        self.lbl_claim_playit.setVisible(False)
        self.chk_playit_auto = QCheckBox("Ejecutar junto al servidor")
        self.chk_playit_auto.setChecked(self.playit_auto)
        self.log_playit = QPlainTextEdit()
        self.log_playit.setReadOnly(True)
        self.log_playit.setMaximumHeight(150)
        self.log_playit.setPlaceholderText("Aquí aparecerá la salida de Playit y el enlace de registro.")
        self.log_playit.setStyleSheet(
            "background-color: #151515; color: #9cdcfe; font-family: Consolas; font-size: 8pt;"
        )
        self.progreso_playit = QProgressBar()
        self.progreso_playit.setValue(0)
        self.progreso_playit.setVisible(False)
        self.worker_playit = None
        self.detencion_playit_solicitada = False

        self.combo_tema = QComboBox()
        self.combo_tema.addItem("🌙 Tema oscuro", "oscuro")
        self.combo_tema.addItem("☀ Tema claro", "claro")
        indice_tema = self.combo_tema.findData(self.tema)
        self.combo_tema.setCurrentIndex(max(0, indice_tema))
        
        estilo_botones = "QPushButton { padding: 8px; font-size: 10pt; font-weight: bold; }"
        self.btn_iniciar.setStyleSheet(estilo_botones)
        self.btn_agregar_instancia.setStyleSheet(estilo_botones)
        self.btn_config_instancia.setStyleSheet(estilo_botones)
        self.btn_agrupar_instancia.setStyleSheet(estilo_botones)
        self.btn_config_global.setStyleSheet(estilo_botones)
        self.btn_descargar_ftb.setStyleSheet(estilo_botones)
        self.btn_instalar_zip.setStyleSheet(estilo_botones)
        self.btn_seleccionar_playit.setStyleSheet(estilo_botones)
        self.btn_instalar_playit.setStyleSheet(estilo_botones)
        self.btn_playit.setStyleSheet(estilo_botones)

        grupo_servidor = QGroupBox("Servidor")
        layout_servidor = QVBoxLayout(grupo_servidor)
        layout_servidor.addWidget(self.btn_agregar_instancia)
        layout_servidor.addWidget(self.btn_iniciar)
        layout_servidor.addWidget(self.btn_config_instancia)
        layout_servidor.addWidget(self.btn_agrupar_instancia)

        grupo_instalacion = QGroupBox("Instalación")
        layout_instalacion = QVBoxLayout(grupo_instalacion)
        layout_instalacion.addWidget(self.btn_descargar_ftb)
        layout_instalacion.addWidget(self.btn_instalar_zip)

        grupo_playit = QGroupBox("Red pública con Playit")
        layout_playit = QVBoxLayout(grupo_playit)
        layout_playit.addWidget(self.lbl_estado_playit)
        layout_playit.addWidget(self.lbl_claim_playit)
        layout_playit.addWidget(self.chk_playit_auto)
        layout_playit.addWidget(self.btn_instalar_playit)
        layout_playit.addWidget(self.btn_seleccionar_playit)
        layout_playit.addWidget(self.btn_playit)
        layout_playit.addWidget(self.progreso_playit)
        layout_playit.addWidget(self.log_playit)

        barra_lateral = QWidget()
        barra_lateral.setFixedWidth(285)
        layout_lateral = QVBoxLayout(barra_lateral)
        layout_lateral.setContentsMargins(8, 0, 0, 0)
        layout_lateral.addWidget(grupo_servidor)
        layout_lateral.addWidget(grupo_instalacion)
        layout_lateral.addWidget(grupo_playit)
        layout_lateral.addStretch()
        layout_lateral.addWidget(QLabel("Apariencia:"))
        layout_lateral.addWidget(self.combo_tema)
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
        self.btn_agregar_instancia.clicked.connect(self.abrir_creador_instancia)
        self.btn_config_global.clicked.connect(self.abrir_configuracion_global)
        self.btn_config_instancia.clicked.connect(self.abrir_configuracion_instancia)
        self.btn_agrupar_instancia.clicked.connect(self.agrupar_instancia)
        self.btn_descargar_ftb.clicked.connect(self.abrir_descargador_ftb)
        self.btn_instalar_zip.clicked.connect(self.abrir_instalador_zip)
        self.btn_seleccionar_playit.clicked.connect(self.seleccionar_ejecutable_playit)
        self.btn_instalar_playit.clicked.connect(self.instalar_playit)
        self.btn_playit.clicked.connect(self.controlar_playit)
        self.chk_playit_auto.toggled.connect(self.guardar_preferencia_playit)
        self.combo_tema.currentIndexChanged.connect(self.cambiar_tema)
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

        self.aplicar_tema(self.tema)
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
                    self.tema = data.get("tema", "oscuro")
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
            "tema": self.tema,
        }
        with open(self.ARCHIVO_CONFIG_GLOBAL, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    def guardar_preferencia_playit(self, activado):
        self.playit_auto = activado
        self.guardar_configuracion_global()

    def cambiar_tema(self):
        self.tema = self.combo_tema.currentData() or "oscuro"
        self.aplicar_tema(self.tema)
        self.guardar_configuracion_global()

    def aplicar_tema(self, tema):
        if tema == "claro":
            estilo = """
                QWidget { background-color: #f4f6f8; color: #1f2937; }
                QMainWindow, QDialog { background-color: #eef2f6; }
                QGroupBox { border: 1px solid #b8c2cf; border-radius: 7px; margin-top: 10px; padding-top: 8px; font-weight: bold; }
                QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
                QPushButton { background-color: #ffffff; border: 1px solid #b8c2cf; border-radius: 6px; padding: 8px; }
                QPushButton:hover { background-color: #e2e8f0; border-color: #2563eb; }
                QPushButton:pressed { background-color: #cbd5e1; }
                QPushButton:disabled { color: #94a3b8; background-color: #e5e7eb; }
                QLineEdit, QComboBox, QPlainTextEdit { background-color: #ffffff; color: #111827; border: 1px solid #b8c2cf; border-radius: 5px; padding: 5px; }
                QProgressBar { border: 1px solid #b8c2cf; border-radius: 4px; text-align: center; background: #ffffff; }
                QProgressBar::chunk { background-color: #2563eb; border-radius: 3px; }
            """
        else:
            estilo = """
                QWidget { background-color: #181a1f; color: #eef2f7; }
                QMainWindow, QDialog { background-color: #13151a; }
                QGroupBox { border: 1px solid #3b414c; border-radius: 7px; margin-top: 10px; padding-top: 8px; font-weight: bold; }
                QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
                QPushButton { background-color: #282c34; border: 1px solid #414754; border-radius: 6px; padding: 8px; }
                QPushButton:hover { background-color: #343944; border-color: #61afef; }
                QPushButton:pressed { background-color: #20232a; }
                QPushButton:disabled { color: #727985; background-color: #20232a; }
                QLineEdit, QComboBox, QPlainTextEdit { background-color: #20232a; color: #eef2f7; border: 1px solid #414754; border-radius: 5px; padding: 5px; }
                QProgressBar { border: 1px solid #414754; border-radius: 4px; text-align: center; background: #20232a; }
                QProgressBar::chunk { background-color: #61afef; border-radius: 3px; }
            """
        app = QApplication.instance()
        if app:
            app.setStyleSheet(estilo)
        self.lista_servidores.aplicar_tema(tema)
        self.log_playit.setStyleSheet(
            "background-color: #ffffff; color: #1f2937; font-family: Consolas; font-size: 8pt;"
            if tema == "claro" else
            "background-color: #101217; color: #98c379; font-family: Consolas; font-size: 8pt;"
        )

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

    def instalar_playit(self):
        if self.worker_playit and self.worker_playit.isRunning():
            return
        self.btn_instalar_playit.setEnabled(False)
        self.progreso_playit.setValue(0)
        self.progreso_playit.setVisible(True)
        self.worker_playit = PlayitDownloadWorker(self.RUTA_PLAYIT_INTERNO)
        self.worker_playit.progreso.connect(self.progreso_playit.setValue)
        self.worker_playit.estado.connect(self.lbl_estado_playit.setText)
        self.worker_playit.finalizado.connect(self.playit_instalado)
        self.worker_playit.start()

    def playit_instalado(self, exito, mensaje, ruta):
        self.btn_instalar_playit.setEnabled(True)
        if exito:
            self.ruta_playit = ruta
            self.guardar_configuracion_global()
            self.lbl_estado_playit.setText("Playit: instalado y listo")
            self.log_playit.appendPlainText(f"[Launcher] {mensaje}")
            QMessageBox.information(self, "Playit instalado", mensaje)
        else:
            self.progreso_playit.setValue(0)
            self.lbl_estado_playit.setText("Playit: error de instalación")
            QMessageBox.critical(self, "No se pudo instalar Playit", mensaje)

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
        if not self.playit_interactivo_compatible(self.ruta_playit):
            mensaje = (
                "El ejecutable instalado es el daemon 1.x y necesita un frontend IPC.\n\n"
                "Pulsa 'Instalar / Actualizar Playit' para instalar el agente portable interactivo compatible."
            )
            self.lbl_estado_playit.setText("Playit: versión incompatible")
            self.log_playit.appendPlainText(f"[Launcher] {mensaje}")
            if mostrar_error:
                QMessageBox.warning(self, "Playit incompatible", mensaje)
            return

        self.log_playit.clear()
        self.lbl_claim_playit.clear()
        self.lbl_claim_playit.setVisible(False)
        self.detencion_playit_solicitada = False
        self.log_playit.appendPlainText("[Launcher] Iniciando Playit...")
        self.proceso_playit.setWorkingDirectory(os.path.dirname(self.ruta_playit))
        self.proceso_playit.start(self.ruta_playit, ["--stdout"])

    def playit_interactivo_compatible(self, ruta):
        comprobacion = QProcess(self)
        comprobacion.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        comprobacion.start(ruta, ["version"])
        if not comprobacion.waitForFinished(3000):
            comprobacion.kill()
            comprobacion.waitForFinished(1000)
            return False
        return comprobacion.exitStatus() == QProcess.ExitStatus.NormalExit and comprobacion.exitCode() == 0

    def detener_playit(self):
        if (self.proceso_playit.state() != QProcess.ProcessState.NotRunning
                and not self.detencion_playit_solicitada):
            self.detencion_playit_solicitada = True
            self.log_playit.appendPlainText("[Launcher] Deteniendo Playit...")
            self.proceso_playit.terminate()

    def leer_salida_playit(self):
        data = self.proceso_playit.readAll().data()
        try:
            texto = data.decode("utf-8")
        except UnicodeDecodeError:
            texto = data.decode("cp1252", errors="replace")
        texto = re.sub(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])", "", texto)
        if texto.strip():
            self.log_playit.appendPlainText(texto.rstrip())
            claim = re.search(r"https://playit\.gg/claim/[A-Za-z0-9_-]+", texto)
            if claim:
                url = claim.group(0)
                self.lbl_claim_playit.setText(f'<a href="{url}">Vincular este agente en Playit</a>')
                self.lbl_claim_playit.setVisible(True)
                self.lbl_estado_playit.setText("Playit: pendiente de vinculación")

    def actualizar_estado_playit(self, estado):
        ejecutando = estado != QProcess.ProcessState.NotRunning
        self.btn_seleccionar_playit.setEnabled(not ejecutando)
        descargando = self.worker_playit is not None and self.worker_playit.isRunning()
        self.btn_instalar_playit.setEnabled(not ejecutando and not descargando)
        self.btn_playit.setText("■ Detener Playit" if ejecutando else "▶ Iniciar Playit")
        if estado == QProcess.ProcessState.Starting:
            self.lbl_estado_playit.setText("Playit: iniciando...")
        elif estado == QProcess.ProcessState.Running:
            self.lbl_estado_playit.setText("Playit: en ejecución")
        else:
            if not self.lbl_estado_playit.text().endswith("incompatible"):
                self.lbl_estado_playit.setText("Playit: detenido")
            self.detencion_playit_solicitada = False

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
                if not isinstance(data, dict):
                    data = {}
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

    def abrir_creador_instancia(self):
        javas = self.escanear_versiones_en_carpeta_javas()
        java_exe = javas[max(javas)] if javas else None
        dialogo = CreateServerDialog(
            self.ruta_instancias,
            self.obtener_grupos_instancias(),
            java_exe=java_exe,
            parent=self,
        )
        if dialogo.exec() == QDialog.DialogCode.Accepted:
            self.cargar_instancias()

    def abrir_configuracion_instancia(self):
        item = self.lista_servidores.currentItem()
        if not item: return
        
        nombre_carpeta = item.text()
        ruta_servidor = os.path.join(self.ruta_instancias, nombre_carpeta)
        archivo_actual, java_actual = self.obtener_datos_instancia(ruta_servidor)

        dialogo = ConfigInstanciaDialog(
            nombre_carpeta,
            ruta_servidor,
            archivo_actual,
            java_actual,
            self.ruta_javas_raiz,
            grupos_disponibles=self.obtener_grupos_instancias(),
            parent=self,
        )
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
                grupo=dialogo.grupo_instancia,
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
        servidores = []
        if os.path.exists(self.ruta_instancias):
            try:
                for f in os.listdir(self.ruta_instancias):
                    ruta_sub = os.path.join(self.ruta_instancias, f)
                    if os.path.isdir(ruta_sub):
                        ruta_icon = os.path.join(ruta_sub, "icon.png")
                        grupo = "No agrupado"
                        ruta_config = os.path.join(ruta_sub, "config_instancia.json")
                        if os.path.isfile(ruta_config):
                            try:
                                with open(ruta_config, "r", encoding="utf-8") as archivo:
                                    datos = json.load(archivo)
                                grupo = datos.get("grupo", "No agrupado") or "No agrupado"
                            except (OSError, json.JSONDecodeError, AttributeError):
                                pass
                        servidores.append({
                            "nombre": f,
                            "grupo": grupo,
                            "icono": ruta_icon if os.path.isfile(ruta_icon) else None,
                        })
            except Exception: pass
        self.lista_servidores.set_servidores(servidores)
        self.actualizar_estado_botones()

    def obtener_grupos_instancias(self):
        grupos = set(self.lista_servidores.grupos())
        grupos.add("No agrupado")
        return sorted(grupos)

    def agrupar_instancia(self):
        item = self.lista_servidores.currentItem()
        if not item:
            return
        grupos = self.obtener_grupos_instancias()
        grupo, aceptado = QInputDialog.getItem(
            self,
            "Agrupar instancia",
            f"Grupo para '{item.text()}':",
            grupos,
            editable=True,
        )
        grupo = grupo.strip()
        if not aceptado or not grupo:
            return

        ruta_instancia = os.path.join(self.ruta_instancias, item.text())
        archivo, java = self.obtener_datos_instancia(ruta_instancia)
        self.guardar_datos_instancia(ruta_instancia, archivo, java, grupo=grupo)
        self.cargar_instancias()

    def actualizar_estado_botones(self, *_args):
        tiene_seleccion = self.lista_servidores.currentItem() is not None
        en_ejecucion = self.proceso_server.state() != QProcess.ProcessState.NotRunning
        self.btn_iniciar.setEnabled(tiene_seleccion or en_ejecucion)
        self.btn_config_instancia.setEnabled(tiene_seleccion and not en_ejecucion)
        self.btn_agrupar_instancia.setEnabled(tiene_seleccion and not en_ejecucion)
        self.btn_agregar_instancia.setEnabled(not en_ejecucion)
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
