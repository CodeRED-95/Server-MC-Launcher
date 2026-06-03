# workers.py
import os
import zipfile
import time
import urllib.request
import subprocess
from PyQt6.QtCore import QThread, pyqtSignal

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
            with urllib.request.urlopen(req) as respuesta:
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
                    zip_ref.extractall(self.carpeta_extraccion)
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
            with urllib.request.urlopen(req) as response:
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

            # SEGÚN EL REPO DE FTB: 
            # Uso: ftb-server-installer <modpack_id> [version_id] --path [ruta] --auto
            # --auto: Acepta todas las preguntas (EULA, Java, etc.) automáticamente.
            # --path: Especifica dónde instalar.
            
            # Evitamos pasar argumentos vacíos si no hay IDs definidos
            argumentos = [ruta_instalador_exe]
            if self.id_modpack:
                argumentos.append(self.id_modpack)
                if self.id_version:
                    argumentos.append(self.id_version)
            argumentos.extend(["--path", self.ruta_destino_instancia, "--auto"])

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

            # Ahora solo leemos la salida para informar al usuario del progreso, 
            # ya no necesitamos escribir en stdin gracias a --auto
            while True:
                linea = proceso.stdout.readline()
                if not linea:
                    break
                
                linea_limpia = linea.strip()
                lower_linea = linea_limpia.lower()
                
                # Emitir siempre la línea para que el usuario vea progreso real
                if linea_limpia:
                    # Filtramos líneas que son solo progreso visual (muchos puntos o barras)
                    if not all(c in '.#= █' for c in linea_limpia):
                        # Mostramos el mensaje del instalador directamente en la UI
                        self.estado.emit(f"FTB: {linea_limpia}")

                # Actualizaciones lógicas de la barra de progreso
                if "modpack files downloaded" in lower_linea:
                    self.progreso.emit(90)
                    self.estado.emit("¡Archivos base listos! Finalizando...")

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
                self.finalizado.emit(False, "El instalador finalizó con errores o fue cancelado.")

        except OSError as e:
            mensaje_error = str(e)
            if getattr(e, 'winerror', None) == 740:
                mensaje_error = "[Error 740] Se requieren permisos de Administrador.\n\nPor favor, cierra el programa y ejecútalo como Administrador (Click derecho -> Ejecutar como administrador) para poder instalar servidores de FTB."
            self.finalizado.emit(False, mensaje_error)
        except Exception as e:
            self.finalizado.emit(False, str(e))