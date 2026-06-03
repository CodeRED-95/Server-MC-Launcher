# workers.py
import os
import zipfile
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