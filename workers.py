# workers.py
import os
import json
import zipfile
import re
import time
import urllib.request
import subprocess
import shutil
import hashlib
import tempfile
from PyQt6.QtCore import QThread, pyqtSignal


class PlayitDownloadWorker(QThread):
    progreso = pyqtSignal(int)
    estado = pyqtSignal(str)
    finalizado = pyqtSignal(bool, str, str)

    # Instalador oficial firmado de Windows 64-bit para Playit 1.0.10.
    DOWNLOAD_URL = (
        "https://github.com/playit-cloud/playit-agent/releases/download/"
        "v1.0.10/playit-windows-x86_64-signed.msi"
    )
    EXPECTED_SHA256 = "18c022281fcfe578fb0d614ac6dc1d36cd6885b4a5439b97655768cd2a82bdc1"

    def __init__(self, ruta_destino):
        super().__init__()
        self.ruta_destino = ruta_destino

    def run(self):
        ruta_temporal = os.path.join(tempfile.gettempdir(), "playit_install_64.msi")
        try:
            self.estado.emit("Playit: descargando instalador oficial firmado...")
            os.makedirs(os.path.dirname(ruta_temporal), exist_ok=True)
            ultimo_error = None
            for intento in range(1, 4):
                try:
                    req = urllib.request.Request(
                        self.DOWNLOAD_URL,
                        headers={"User-Agent": "Server-MC-Launcher"},
                    )
                    with urllib.request.urlopen(req, timeout=90) as respuesta, open(ruta_temporal, "wb") as archivo:
                        total = int(respuesta.headers.get("Content-Length", 0))
                        descargado = 0
                        while True:
                            bloque = respuesta.read(64 * 1024)
                            if not bloque:
                                break
                            archivo.write(bloque)
                            descargado += len(bloque)
                            if total:
                                self.progreso.emit(int(descargado / total * 100))
                    ultimo_error = None
                    break
                except Exception as error:
                    ultimo_error = error
                    if os.path.exists(ruta_temporal):
                        os.remove(ruta_temporal)
                    time.sleep(intento * 2)
            if ultimo_error:
                raise ultimo_error

            sha256 = hashlib.sha256()
            with open(ruta_temporal, "rb") as archivo:
                for bloque in iter(lambda: archivo.read(1024 * 1024), b""):
                    sha256.update(bloque)
            if sha256.hexdigest().lower() != self.EXPECTED_SHA256:
                raise RuntimeError("La verificación SHA-256 del instalador de Playit falló.")

            self.estado.emit("Playit: ejecutando instalación silenciosa...")
            msiexec = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "System32", "msiexec.exe")
            comando = [msiexec, "/i", ruta_temporal, "/qn", "/norestart", "ALLUSERS=1"]
            try:
                resultado = subprocess.run(
                    comando,
                    capture_output=True,
                    text=True,
                    timeout=600,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                    check=False,
                )
            except subprocess.TimeoutExpired as error:
                raise RuntimeError("La instalación silenciosa de Playit tardó demasiado.") from error

            if resultado.returncode not in (0, 3010):
                detalle = (resultado.stdout or "") + ("\n" if resultado.stdout and resultado.stderr else "") + (resultado.stderr or "")
                detalle = detalle.strip() or f"msiexec terminó con código {resultado.returncode}"
                raise RuntimeError(f"No se pudo instalar Playit: {detalle}")

            for _ in range(60):
                if os.path.isfile(self.ruta_destino):
                    break
                time.sleep(1)
            if not os.path.isfile(self.ruta_destino):
                raise RuntimeError(
                    "La instalación terminó, pero no se encontró playit.exe en "
                    f"{self.ruta_destino}"
                )

            self.progreso.emit(100)
            self.finalizado.emit(
                True,
                "Playit se instaló correctamente en C:\\Program Files\\playit_gg.",
                self.ruta_destino,
            )
        except Exception as error:
            if os.path.exists(ruta_temporal):
                try:
                    os.remove(ruta_temporal)
                except OSError:
                    pass
            self.finalizado.emit(False, str(error), "")


def _extraer_zip_seguro(zip_ref, destino, callback_progreso=None):
    """Extrae un ZIP impidiendo que una entrada escriba fuera del destino."""
    destino_real = os.path.abspath(destino)
    entradas = zip_ref.infolist()
    total = len(entradas)
    if not total:
        raise ValueError("El ZIP está vacío.")

    for entrada in entradas:
        ruta_destino = os.path.abspath(os.path.join(destino_real, entrada.filename))
        try:
            dentro_del_destino = os.path.commonpath([destino_real, ruta_destino]) == destino_real
        except ValueError:
            dentro_del_destino = False

        if not dentro_del_destino:
            raise ValueError(f"El ZIP contiene una ruta no segura: {entrada.filename}")

    for indice, entrada in enumerate(entradas, start=1):
        zip_ref.extract(entrada, destino_real)
        if callback_progreso and total:
            callback_progreso(indice, total)


def _detectar_archivo_arranque(ruta_instancia):
    candidatos = ("startserver.bat", "start.bat", "run.bat", "server.jar")
    for candidato in candidatos:
        if os.path.isfile(os.path.join(ruta_instancia, candidato)):
            return candidato

    for nombre in sorted(os.listdir(ruta_instancia)):
        if nombre.lower().endswith((".bat", ".jar")):
            return nombre
    return ""


class DownloaderWorker(QThread):
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
            self.estado.emit("Conectando con el servidor de descarga...")
            self.progreso.emit(5)

            req = urllib.request.Request(self.url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            with urllib.request.urlopen(req, timeout=60) as respuesta:
                total_size = respuesta.getheader('Content-Length')
                total_size = int(total_size) if total_size else None
                bytes_descargados = 0
                bloque_size = 1024 * 64
                
                with open(self.destino_zip, 'wb') as archivo_local:
                    while True:
                        bloque = respuesta.read(bloque_size)
                        if not bloque: break
                        archivo_local.write(bloque)
                        bytes_descargados += len(bloque)
                        if total_size:
                            porcentaje = int((bytes_descargados / total_size) * 80)
                            self.progreso.emit(5 + porcentaje)

            self.estado.emit("Extrayendo archivos de Java portable...")
            self.progreso.emit(85)

            if zipfile.is_zipfile(self.destino_zip):
                with zipfile.ZipFile(self.destino_zip, 'r') as zip_ref:
                    _extraer_zip_seguro(zip_ref, self.carpeta_extraccion)
            else:
                raise Exception("El archivo descargado no es un paquete ZIP válido.")

            if os.path.exists(self.destino_zip):
                os.remove(self.destino_zip)

            self.progreso.emit(100)
            self.finalizado.emit(True, "Entorno de Java portable instalado correctamente.")
        except Exception as e:
            if os.path.exists(self.destino_zip):
                try: os.remove(self.destino_zip)
                except Exception: pass
            self.finalizado.emit(False, str(e))

class ZipExtractionWorker(QThread):
    progreso = pyqtSignal(int)
    estado = pyqtSignal(str)
    finalizado = pyqtSignal(bool, str, str) # success, message, instance_path

    def __init__(self, zip_path, instance_name, destination_root_path, es_update=False):
        super().__init__()
        self.zip_path = zip_path
        self.instance_name = instance_name
        self.destination_root_path = destination_root_path
        self.instance_path = os.path.join(self.destination_root_path, self.instance_name)
        self.es_update = es_update

    def run(self):
        carpeta_creada = False
        try:
            if not self.es_update and os.path.exists(self.instance_path):
                self.finalizado.emit(False, f"La carpeta '{self.instance_name}' ya existe.", "")
                return

            config_data = {"archivo_arranque": "", "java_especifico": "AUTO"}
            ruta_json = os.path.join(self.instance_path, "config_instancia.json")
            if self.es_update and os.path.exists(ruta_json):
                try:
                    with open(ruta_json, "r", encoding="utf-8") as f:
                        data_existente = json.load(f)
                    if isinstance(data_existente, dict):
                        config_data = data_existente
                except (OSError, json.JSONDecodeError):
                    pass

            if not os.path.exists(self.instance_path):
                os.makedirs(self.instance_path)
                carpeta_creada = True

            self.estado.emit(f"Descomprimiendo '{os.path.basename(self.zip_path)}' en '{self.instance_name}'...")
            self.progreso.emit(0)

            with zipfile.ZipFile(self.zip_path, 'r') as zip_ref:
                _extraer_zip_seguro(
                    zip_ref,
                    self.instance_path,
                    lambda procesados, total: self.progreso.emit(int(procesados / total * 90)),
                )

            # Crear o actualizar config_instancia.json
            archivo_detectado = _detectar_archivo_arranque(self.instance_path)
            if not archivo_detectado:
                raise FileNotFoundError(
                    "No se encontró un archivo de arranque .bat o .jar en la raíz del ZIP."
                )
            config_data["archivo_arranque"] = archivo_detectado

            with open(ruta_json, "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=4)

            self.progreso.emit(100)
            self.finalizado.emit(True, "Servidor ZIP instalado correctamente.", self.instance_path)
        except Exception as e:
            if carpeta_creada:
                try:
                    shutil.rmtree(self.instance_path)
                except OSError:
                    pass
            self.finalizado.emit(False, f"Error al instalar desde ZIP: {e}", "")


class FTBDownloadWorker(QThread):
    progreso = pyqtSignal(int)
    estado = pyqtSignal(str)
    finalizado = pyqtSignal(bool, str)

    def __init__(self, url_instalador, ruta_destino_instancia, ruta_javas_raiz=None, id_modpack=None, id_version=None):
        super().__init__()
        self.url_instalador = url_instalador
        self.ruta_destino_instancia = ruta_destino_instancia
        self.ruta_javas_raiz = ruta_javas_raiz
        self.id_modpack = str(id_modpack) if id_modpack else ""
        self.id_version = str(id_version) if id_version else ""
        self.proceso = None

    def run(self):
        try:
            if not os.path.exists(self.ruta_destino_instancia):
                os.makedirs(self.ruta_destino_instancia)

            self.estado.emit("Descargando instalador nativo oficial (.exe)...")
            self.progreso.emit(20)
            
            # El instalador de FTB espera encontrar el ID del modpack y la versión en su propio nombre de archivo.
            # Formato esperado: serverinstall_<id_modpack>_<id_version>.exe
            nombre_ejecutable = f"serverinstall_{self.id_modpack}_{self.id_version}.exe"
            ruta_instalador_exe = os.path.join(self.ruta_destino_instancia, nombre_ejecutable)
            
            # Descargamos el ejecutable limpio de FTB
            req = urllib.request.Request(self.url_instalador, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            with urllib.request.urlopen(req, timeout=60) as response:
                with open(ruta_instalador_exe, 'wb') as out_file:
                    while True:
                        chunk = response.read(1024 * 64)
                        if not chunk: break
                        out_file.write(chunk)

            self.progreso.emit(45)
            self.estado.emit("Abriendo el asistente de instalación interactivo...")

            # Localizamos Java portable para inyectarlo al PATH
            java_bin_aux = None
            if self.ruta_javas_raiz and os.path.exists(self.ruta_javas_raiz):
                for raiz, dirs, archivos in os.walk(self.ruta_javas_raiz):
                    if "java.exe" in archivos:
                        java_bin_aux = raiz
                        break

            env_instalacion = os.environ.copy()
            if java_bin_aux:
                # Inyectamos JAVA_HOME y PATH para que el instalador de Forge/Fabric no falle
                java_home = os.path.dirname(java_bin_aux)
                env_instalacion["JAVA_HOME"] = java_home
                env_instalacion["PATH"] = java_bin_aux + os.pathsep + env_instalacion.get("PATH", "")
            
            # Forzamos al instalador a modo no interactivo para evitar deadlocks en entornos sin TTY
            env_instalacion["CI"] = "true"
            env_instalacion["PTERM_NO_INTERACTIVE"] = "true"
            env_instalacion["PTERM_NO_COLOR"] = "true"

            # SEGÚN EL REPO DE FTB: 
            # Uso: ftb-server-installer <modpack_id> [version_id] --path [ruta] --auto
            # --auto: Acepta todas las preguntas (EULA, Java, etc.) automáticamente.
            # --path: Especifica dónde instalar.
            
            # Evitamos pasar argumentos vacíos si no hay IDs definidos
            argumentos = [ruta_instalador_exe, "--auto"]
            if self.id_modpack:
                argumentos.append(self.id_modpack)
                if self.id_version:
                    argumentos.append(self.id_version)
            argumentos.extend(["--path", self.ruta_destino_instancia])

            proceso = subprocess.Popen(
                argumentos,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, # Unifica errores con la salida regular
                env=env_instalacion,
                text=True,
                bufsize=1, # Line buffered
                cwd=self.ruta_destino_instancia, # Se ejecuta dentro de la carpeta destino
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
                encoding='utf-8', errors='replace'
            )
            self.proceso = proceso

            ansi_cleaner = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
            buffer_linea = ""
            lower_linea = ""

            while True:
                # Leemos de a 1 caracter para no bloquearnos en los prompts [Y/n] que no tienen \n
                char = proceso.stdout.read(1)
                if not char:
                    if proceso.poll() is not None:
                        # Si hay algo en el buffer antes de cerrar, lo mostramos
                        if buffer_linea.strip():
                            linea_final = ansi_cleaner.sub('', buffer_linea).strip()
                            if linea_final: self.estado.emit(f"FTB: {linea_final}")
                        break
                    continue
                
                buffer_linea += char
                
                # Procesamos si hay salto de línea o si el buffer parece un prompt (termina en : o ?)
                if char in ('\n', '\r') or buffer_linea.endswith(':') or buffer_linea.endswith('?'):
                    linea_sin_ansi = ansi_cleaner.sub('', buffer_linea).strip()
                    lower_linea = linea_sin_ansi.lower()

                    if linea_sin_ansi and not all(c in '.#= █' for c in linea_sin_ansi):
                        self.estado.emit(f"FTB: {linea_sin_ansi}")

                    # INTERACCIÓN AUTOMÁTICA: Detectamos preguntas del instalador
                    palabras_interaccion = [
                        "agree to the eula", "install java", "continue?", 
                        "confirm installation", "install path", "[y/n]"
                    ]
                    
                    if any(p in lower_linea for p in palabras_interaccion):
                        # Pequeña pausa para asegurar que el instalador esté listo para recibir el comando
                        time.sleep(0.2)
                        self.enviar_entrada("y")

                    # Actualizaciones de progreso
                    if "modpack files downloaded" in lower_linea:
                        self.progreso.emit(90)
                        self.estado.emit("¡Archivos base listos! Finalizando...")

                    # Limpiamos el buffer para la siguiente parte del texto
                    buffer_linea = ""

            # Esperamos que finalice de escribir todos los archivos en disco
            proceso.wait()
            self.progreso.emit(95)

            # Limpieza del instalador para no dejar basura ejecutable
            if os.path.exists(ruta_instalador_exe):
                try: 
                    time.sleep(1) # Pequeña pausa para asegurar que Windows liberó el archivo
                    os.remove(ruta_instalador_exe)
                except Exception: 
                    pass

            if proceso.returncode == 0:
                self.finalizado.emit(True, "Servidor de FTB instalado correctamente con todas sus dependencias.")
            else:
                self.finalizado.emit(False, f"El instalador falló (Código: {proceso.returncode}). Revisa el log para ver el error de Java o Red.")

        except OSError as e:
            mensaje_error = str(e)
            if getattr(e, 'winerror', None) == 740:
                mensaje_error = "[Error 740] Se requieren permisos de Administrador.\n\nPor favor, cierra el programa y ejecútalo como Administrador (Click derecho -> Ejecutar como administrador) para poder instalar servidores de FTB."
            self.finalizado.emit(False, mensaje_error)
        except Exception as e:
            self.finalizado.emit(False, str(e))

    def enviar_entrada(self, texto):
        """Permite enviar comandos manuales al stdin del instalador."""
        if self.proceso and self.proceso.poll() is None:
            try:
                self.proceso.stdin.write(texto + "\n")
                self.proceso.stdin.flush()
            except Exception: pass
