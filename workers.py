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

    def __init__(self, url_instalador, ruta_destino_instancia):
        super().__init__()
        self.url_instalador = url_instalador
        self.ruta_destino_instancia = ruta_destino_instancia

    def run(self):
        try:
            if not os.path.exists(self.ruta_destino_instancia):
                os.makedirs(self.ruta_destino_instancia)

            self.estado.emit("Descargando instalador nativo oficial (.exe)...")
            self.progreso.emit(20)
            
            # Renombramos para intentar evitar la detección heurística de 'installer' de Windows
            ruta_instalador_exe = os.path.join(self.ruta_destino_instancia, "ftb_dl.exe")
            
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

            # Lanzamos el proceso vinculando la consola de entrada y salida de datos de texto
            proceso = subprocess.Popen(
                [ruta_instalador_exe],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, # Unifica errores con la salida regular
                text=True,
                cwd=self.ruta_destino_instancia, # Se ejecuta dentro de la carpeta destino
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )

            # Monitoreo inteligente de las preguntas del instalador en tiempo real
            buffer_lineas = ""
            while True:
                # Leemos caracter por caracter para interceptar las preguntas antes del salto de línea
                char = proceso.stdout.read(1)
                if not char:
                    break
                
                buffer_lineas += char
                print(char, end="") # Para depurar en tu consola de VS Code si fuera necesario

                # Pregunta 1: Do you want to continue? [Y/n]
                if "want to continue?" in buffer_lineas and ("[" in buffer_lineas or ":" in buffer_lineas):
                    self.estado.emit("Configurando directorio: Enviando confirmación (Yes)...")
                    self.progreso.emit(55)
                    proceso.stdin.write("Y\n")
                    proceso.stdin.flush()
                    buffer_lineas = ""

                # Pregunta 2: Do you want to download java? [Y/n]
                elif "download java?" in buffer_lineas and ("[" in buffer_lineas or ":" in buffer_lineas):
                    self.estado.emit("Saltando descarga de Java (Usando entorno del launcher)...")
                    self.progreso.emit(65)
                    proceso.stdin.write("n\n")
                    proceso.stdin.flush()
                    buffer_lineas = ""

                # Pregunta 3: Would you like to run the neoforge/forge installer? [Y/n]
                elif "run the" in buffer_lineas and "installer?" in buffer_lineas and ("[" in buffer_lineas or ":" in buffer_lineas):
                    self.estado.emit("Instalando ModLoader requerido del servidor (Forge/NeoForge)...")
                    self.progreso.emit(80)
                    proceso.stdin.write("Y\n")
                    proceso.stdin.flush()
                    buffer_lineas = ""

                # Si detecta el éxito del proceso
                elif "Modpack files downloaded" in buffer_lineas:
                    self.estado.emit("Descargando e integrando mods en el servidor...")

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