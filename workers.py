# workers.py
import os
import zipfile
import subprocess
from PyQt6.QtCore import QThread, pyqtSignal

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
            
            with zipfile.ZipFile(self.destino_zip, 'r') as zip_ref:
                lista_archivos = zip_ref.namelist()
                total_archivos = len(lista_archivos)
                
                if not os.path.exists(self.carpeta_extraccion):
                    os.makedirs(self.carpeta_extraccion)

                for i, archivo in enumerate(lista_archivos):
                    zip_ref.extract(archivo, self.carpeta_extraccion)
                    if total_archivos > 0:
                        self.progreso.emit(int(((i + 1) / total_archivos) * 100))

            if os.path.exists(self.destino_zip):
                os.remove(self.destino_zip)

            self.finalizado.emit(True, "Java instalado y configurado correctamente.")
        except Exception as e:
            self.finalizado.emit(False, str(e))


# Modifica esta clase dentro de workers.py

class FTBDownloadWorker(QThread):
    """Hilo para descargar y ejecutar el instalador universal de servidores de FTB."""
    progreso = pyqtSignal(int)
    estado = pyqtSignal(str)
    finalizado = pyqtSignal(bool, str)

    def __init__(self, url_instalador, ruta_destino_instancia, id_modpack, id_version):
        super().__init__()
        self.url_instalador = url_instalador
        self.ruta_destino_instancia = ruta_destino_instancia
        self.id_modpack = id_modpack
        self.id_version = id_version

    def run(self):
        try:
            import urllib.request
            import subprocess
            if not os.path.exists(self.ruta_destino_instancia):
                os.makedirs(self.ruta_destino_instancia)

            self.estado.emit("Descargando instalador universal (JAR)...")
            self.progreso.emit(15)
            
            # Descargamos el archivo como .jar en lugar de .exe
            ruta_instalador_jar = os.path.join(self.ruta_destino_instancia, "ftb_installer.jar")
            
            req = urllib.request.Request(self.url_instalador, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response, open(ruta_instalador_jar, 'wb') as out_file:
                out_file.write(response.read())
            
            self.progreso.emit(40)
            self.estado.emit("Instalando archivos del servidor vía Java (Un momento)...")

            # Ejecutamos el instalador usando "java -jar" de manera universal
            comando = [
                "java", "-jar", ruta_instalador_jar,
                str(self.id_modpack),
                str(self.id_version),
                "--path", self.ruta_destino_instancia,
                "--silent"
            ]
            
            proceso = subprocess.run(
                comando, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                text=True, 
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            self.progreso.emit(90)
            
            if os.path.exists(ruta_instalador_jar):
                os.remove(ruta_instalador_jar)

            if proceso.returncode == 0:
                self.finalizado.emit(True, "Servidor de FTB descargado e instalado correctamente.")
            else:
                self.finalizado.emit(False, f"El instalador falló. Verifique que tenga Java instalado en su PATH.\\nDetalle: {proceso.stderr}")

        except Exception as e:
            self.finalizado.emit(False, str(e))