# launcher.py
import os
import json
import struct
import zipfile
import ctypes
from PyQt6.QtWidgets import (QMainWindow, QPushButton, QVBoxLayout, QHBoxLayout, 
                             QWidget, QListWidget, QListWidgetItem, QLabel, 
                             QDialog, QMessageBox)
from PyQt6.QtCore import QProcess, QProcessEnvironment, Qt, QSize, QFileSystemWatcher
from PyQt6.QtGui import QIcon

from components import ConsoleWindow, ConfigGlobalDialog, ConfigInstanciaDialog, FTBDownloaderDialog

class ServerLauncher(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Minecraft Server Launcher Grid Pro")
        self.resize(1000, 600)

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
        
        estilo_botones = "QPushButton { padding: 8px; font-size: 10pt; font-weight: bold; }"
        self.btn_iniciar.setStyleSheet(estilo_botones)
        self.btn_config_instancia.setStyleSheet(estilo_botones)
        self.btn_config_global.setStyleSheet(estilo_botones)
        self.btn_descargar_ftb.setStyleSheet(estilo_botones)

        layout_botones = QHBoxLayout()
        layout_botones.addWidget(self.btn_iniciar, stretch=2)
        layout_botones.addWidget(self.btn_config_instancia, stretch=1)
        layout_botones.addWidget(self.btn_config_global, stretch=1)
        layout_botones.addWidget(self.btn_descargar_ftb, stretch=1)

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
        self.btn_descargar_ftb.clicked.connect(self.abrir_descargador_ftb)
        self.lista_servidores.currentItemChanged.connect(self.actualizar_estado_botones)
        
        self.proceso_server.readyRead.connect(self.leer_consola)
        self.proceso_server.finished.connect(self.servidor_terminado)

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
            except Exception: pass
        
        if not self.ruta_instancias or not os.path.exists(self.ruta_instancias):
            self.ruta_instancias = os.path.join(os.path.dirname(__file__), "instancias")
            if not os.path.exists(self.ruta_instancias): os.makedirs(self.ruta_instancias)
        
        if not self.ruta_javas_raiz:
            self.ruta_javas_raiz = os.path.join(os.path.dirname(__file__), "javas")
            if not os.path.exists(self.ruta_javas_raiz): os.makedirs(self.ruta_javas_raiz)
                
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

    def actualizar_estado_botones(self):
        tiene_seleccion = self.lista_servidores.currentItem() is not None
        en_ejecucion = self.proceso_server.state() == QProcess.ProcessState.Running
        self.btn_config_instancia.setEnabled(tiene_seleccion and not en_ejecucion)
        self.btn_config_global.setEnabled(not en_ejecucion)
        self.btn_descargar_ftb.setEnabled(not en_ejecucion)
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
        
        for raiz, directorios, archivos in os.walk(self.ruta_javas_raiz):
            if "java.exe" in archivos:
                ruta_exe = os.path.join(raiz, "java.exe")
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
        jar_principal = os.path.join(ruta_servidor, "server.jar")
        if not os.path.exists(jar_principal):
            for f in os.listdir(ruta_servidor):
                if f.endswith(".jar") and ("forge" in f or "fabric" in f or "paper" in f or "server" in f):
                    jar_principal = os.path.join(ruta_servidor, f)
                    break
                    
        if os.path.exists(jar_principal):
            version_requerida = self.detectar_version_java_de_jar(jar_principal)
            
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
            self.proceso_server.setProcessEnvironment(env)
            self.proceso_server.setWorkingDirectory(ruta_servidor)

            if ejecutable.endswith(".bat"):
                comando = "cmd.exe"
                # Añadimos nogui al final de la ejecución por lotes
                argumentos = ["/c", ejecutable, "nogui"]
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

        self.btn_iniciar.setText("🚀 Iniciar Servidor")
        self.instancia_actual = None
        self.actualizar_estado_botones()
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