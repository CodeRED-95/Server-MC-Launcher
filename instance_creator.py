import hashlib
import json
import os
import re
import shutil
import subprocess
import time
import urllib.request
import xml.etree.ElementTree as ET

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
)


USER_AGENT = "Server-MC-Launcher"


def _leer_url(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as respuesta:
        return respuesta.read()


class ServerCatalogWorker(QThread):
    completado = pyqtSignal(object)
    error = pyqtSignal(str)

    def run(self):
        try:
            manifest = json.loads(_leer_url(
                "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"
            ).decode("utf-8"))
            versiones_mc = [
                item for item in manifest.get("versions", []) if item.get("type") == "release"
            ]

            fabric_loaders = json.loads(_leer_url(
                "https://meta.fabricmc.net/v2/versions/loader"
            ).decode("utf-8"))
            fabric_installers = json.loads(_leer_url(
                "https://meta.fabricmc.net/v2/versions/installer"
            ).decode("utf-8"))

            forge_root = ET.fromstring(_leer_url(
                "https://maven.minecraftforge.net/net/minecraftforge/forge/maven-metadata.xml"
            ))
            forge_versions = [node.text for node in forge_root.findall(".//version") if node.text]

            neo_root = ET.fromstring(_leer_url(
                "https://maven.neoforged.net/releases/net/neoforged/neoforge/maven-metadata.xml"
            ))
            neo_versions = [node.text for node in neo_root.findall(".//version") if node.text]

            instalador_fabric = next(
                (item["version"] for item in fabric_installers if item.get("stable")),
                fabric_installers[0]["version"],
            )
            self.completado.emit({
                "minecraft": versiones_mc,
                "fabric": [item["version"] for item in fabric_loaders],
                "fabric_installer": instalador_fabric,
                "forge": forge_versions,
                "neoforge": neo_versions,
            })
        except Exception as error:
            self.error.emit(str(error))


class ServerInstallWorker(QThread):
    progreso = pyqtSignal(int)
    estado = pyqtSignal(str)
    log = pyqtSignal(str)
    finalizado = pyqtSignal(bool, str, str)

    def __init__(self, destino, nombre, grupo, tipo, version_mc, version_loader,
                 version_url, fabric_installer, java_exe=None):
        super().__init__()
        self.destino = destino
        self.nombre = nombre
        self.grupo = grupo
        self.tipo = tipo
        self.version_mc = version_mc
        self.version_loader = version_loader
        self.version_url = version_url
        self.fabric_installer = fabric_installer
        self.java_exe = java_exe
        self.ruta_instancia = os.path.join(destino, nombre)

    def _descargar(self, url, destino, progreso_inicio=10, progreso_fin=70):
        self.log.emit(f"Descargando {os.path.basename(destino)}...")
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=60) as respuesta, open(destino, "wb") as archivo:
            total = int(respuesta.headers.get("Content-Length", 0))
            descargado = 0
            while True:
                bloque = respuesta.read(64 * 1024)
                if not bloque:
                    break
                archivo.write(bloque)
                descargado += len(bloque)
                if total:
                    avance = descargado / total
                    self.progreso.emit(int(progreso_inicio + avance * (progreso_fin - progreso_inicio)))

    def _instalar_vanilla(self):
        self.estado.emit("Consultando archivos oficiales de Mojang...")
        self.log.emit("Consultando archivos oficiales de Mojang...")
        datos_version = json.loads(_leer_url(self.version_url).decode("utf-8"))
        servidor = datos_version.get("downloads", {}).get("server")
        if not servidor:
            raise RuntimeError("Mojang no publica un servidor para esta versión.")
        destino_jar = os.path.join(self.ruta_instancia, "server.jar")
        self._descargar(servidor["url"], destino_jar)
        sha1 = hashlib.sha1()
        with open(destino_jar, "rb") as archivo:
            for bloque in iter(lambda: archivo.read(1024 * 1024), b""):
                sha1.update(bloque)
        if servidor.get("sha1") and sha1.hexdigest() != servidor["sha1"]:
            raise RuntimeError("La verificación SHA-1 del servidor Vanilla falló.")
        return "server.jar"

    def _instalar_fabric(self):
        self.estado.emit("Descargando servidor Fabric oficial...")
        self.log.emit("Descargando servidor Fabric oficial...")
        url = (
            "https://meta.fabricmc.net/v2/versions/loader/"
            f"{self.version_mc}/{self.version_loader}/{self.fabric_installer}/server/jar"
        )
        archivo = "fabric-server-launch.jar"
        self._descargar(url, os.path.join(self.ruta_instancia, archivo))
        os.makedirs(os.path.join(self.ruta_instancia, "mods"), exist_ok=True)
        return archivo

    def _instalar_con_installer(self):
        if not self.java_exe or not os.path.isfile(self.java_exe):
            raise RuntimeError(
                "Forge y NeoForge requieren Java. Instala una versión portable desde Ajustes / Java."
            )
        if self.tipo == "Forge":
            base = "https://maven.minecraftforge.net/net/minecraftforge/forge"
            url = f"{base}/{self.version_loader}/forge-{self.version_loader}-installer.jar"
        else:
            base = "https://maven.neoforged.net/releases/net/neoforged/neoforge"
            url = f"{base}/{self.version_loader}/neoforge-{self.version_loader}-installer.jar"

        instalador = os.path.join(self.ruta_instancia, "loader-installer.jar")
        self.estado.emit(f"Descargando instalador oficial de {self.tipo}...")
        self.log.emit(f"Descargando instalador oficial de {self.tipo}...")
        self._descargar(url, instalador, 10, 50)
        self.estado.emit(f"Instalando {self.tipo}; este paso puede tardar varios minutos...")
        self.log.emit(f"Instalando {self.tipo}; este paso puede tardar varios minutos...")
        proceso = subprocess.Popen(
            [self.java_exe, "-jar", instalador, "--installServer", self.ruta_instancia],
            cwd=self.ruta_instancia,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            bufsize=1,
        )
        salida = []
        inicio = time.monotonic()
        while True:
            linea = proceso.stdout.readline()
            if linea:
                linea = linea.rstrip()
                salida.append(linea)
                if linea.strip():
                    self.log.emit(linea)
                    self.estado.emit(linea[:120])
            elif proceso.poll() is not None:
                break
            elif time.monotonic() - inicio > 600:
                proceso.kill()
                raise RuntimeError(f"La instalación de {self.tipo} tardó demasiado.")
        proceso.wait()
        try:
            os.remove(instalador)
        except OSError:
            pass
        if proceso.returncode != 0:
            detalle = "\n".join(salida).strip()
            raise RuntimeError(f"El instalador de {self.tipo} falló:\n{detalle[-1500:]}")
        os.makedirs(os.path.join(self.ruta_instancia, "mods"), exist_ok=True)
        for candidato in ("run.bat", "start.bat"):
            if os.path.isfile(os.path.join(self.ruta_instancia, candidato)):
                return candidato
        raise RuntimeError(f"{self.tipo} terminó sin crear un script de arranque.")

    def run(self):
        creada = False
        try:
            if os.path.exists(self.ruta_instancia):
                raise FileExistsError(f"Ya existe una instancia llamada '{self.nombre}'.")
            os.makedirs(self.ruta_instancia)
            creada = True
            self.progreso.emit(5)
            self.log.emit(f"Instancia: {self.nombre}")
            self.log.emit(f"Tipo: {self.tipo}")
            self.log.emit(f"Carpeta: {self.ruta_instancia}")

            if self.tipo == "Vanilla":
                archivo_arranque = self._instalar_vanilla()
            elif self.tipo == "Fabric":
                archivo_arranque = self._instalar_fabric()
            else:
                archivo_arranque = self._instalar_con_installer()

            config = {
                "archivo_arranque": archivo_arranque,
                "java_especifico": "AUTO",
                "grupo": self.grupo,
                "minecraft_version": self.version_mc,
                "loader": self.tipo,
                "loader_version": self.version_loader,
            }
            with open(os.path.join(self.ruta_instancia, "config_instancia.json"), "w", encoding="utf-8") as archivo:
                json.dump(config, archivo, indent=4)
            with open(os.path.join(self.ruta_instancia, "eula.txt"), "w", encoding="utf-8") as archivo:
                archivo.write("eula=false\n")

            self.progreso.emit(100)
            self.finalizado.emit(True, "Instancia creada correctamente.", self.ruta_instancia)
        except Exception as error:
            if creada:
                try:
                    shutil.rmtree(self.ruta_instancia)
                except OSError:
                    pass
            self.finalizado.emit(False, str(error), "")


class CreateServerDialog(QDialog):
    def __init__(self, ruta_instancias, grupos, java_exe=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Añadir instancia de servidor")
        self.resize(760, 660)
        self.ruta_instancias = ruta_instancias
        self.java_exe = java_exe
        self.catalogo = None
        self.worker_catalogo = None
        self.worker_instalacion = None

        self.txt_nombre = QLineEdit()
        self.txt_nombre.setPlaceholderText("Ej: Survival_1.21")
        self.combo_grupo = QComboBox()
        self.combo_grupo.setEditable(True)
        self.combo_grupo.addItems(sorted(set(grupos) | {"No agrupado"}))
        self.combo_tipo = QComboBox()
        self.combo_tipo.addItems(["Vanilla", "Fabric", "Forge", "NeoForge"])
        self.combo_minecraft = QComboBox()
        self.combo_minecraft.setEditable(True)
        self.combo_loader = QComboBox()
        self.lbl_loader = QLabel("Versión del loader:")

        formulario = QFormLayout()
        formulario.addRow("Nombre:", self.txt_nombre)
        formulario.addRow("Grupo:", self.combo_grupo)
        formulario.addRow("Tipo de servidor:", self.combo_tipo)
        formulario.addRow("Versión de Minecraft:", self.combo_minecraft)
        formulario.addRow(self.lbl_loader, self.combo_loader)

        self.lbl_estado = QLabel("Cargando catálogos oficiales...")
        self.barra = QProgressBar()
        self.lbl_log = QLabel("Log de creación:")
        self.log_instalacion = QPlainTextEdit()
        self.log_instalacion.setReadOnly(True)
        self.log_instalacion.setMinimumHeight(220)
        self.log_instalacion.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.btn_crear = QPushButton("Crear e instalar servidor")
        self.btn_crear.setEnabled(False)
        self.btn_cancelar = QPushButton("Cancelar")
        self.btn_cancelar.setEnabled(False)
        botones = QHBoxLayout()
        botones.addStretch()
        botones.addWidget(self.btn_crear)
        botones.addWidget(self.btn_cancelar)

        layout = QVBoxLayout(self)
        layout.addLayout(formulario)
        layout.addWidget(self.lbl_estado)
        layout.addWidget(self.barra)
        layout.addWidget(self.lbl_log)
        layout.addWidget(self.log_instalacion, 1)
        layout.addLayout(botones)

        self.combo_tipo.currentTextChanged.connect(self.actualizar_loaders)
        self.combo_minecraft.currentTextChanged.connect(self.actualizar_loaders)
        self.btn_crear.clicked.connect(self.crear)
        self.btn_cancelar.clicked.connect(self.reject)
        self.cargar_catalogos()

    def cargar_catalogos(self):
        self.worker_catalogo = ServerCatalogWorker()
        self.worker_catalogo.completado.connect(self.catalogos_cargados)
        self.worker_catalogo.error.connect(self.error_catalogo)
        self.worker_catalogo.start()

    def catalogos_cargados(self, catalogo):
        self.catalogo = catalogo
        self.combo_minecraft.clear()
        for version in catalogo["minecraft"]:
            self.combo_minecraft.addItem(version["id"], version["url"])
        self.lbl_estado.setText("Selecciona las versiones y crea la instancia.")
        self.btn_cancelar.setEnabled(True)
        self.actualizar_loaders()

    def error_catalogo(self, mensaje):
        self.lbl_estado.setText("No se pudieron cargar los catálogos.")
        self.btn_cancelar.setEnabled(True)
        QMessageBox.critical(self, "Error de catálogos", mensaje)

    def actualizar_loaders(self):
        if not self.catalogo:
            return
        tipo = self.combo_tipo.currentText()
        minecraft = self.combo_minecraft.currentText()
        self.combo_loader.clear()
        mostrar = tipo != "Vanilla"
        self.combo_loader.setEnabled(mostrar)
        self.lbl_loader.setEnabled(mostrar)

        if tipo == "Fabric":
            versiones = self.catalogo["fabric"]
        elif tipo == "Forge":
            versiones = [v for v in reversed(self.catalogo["forge"]) if v.startswith(minecraft + "-")]
        elif tipo == "NeoForge":
            prefijo = (minecraft[2:] if minecraft.startswith("1.") else minecraft) + "."
            versiones = [v for v in reversed(self.catalogo["neoforge"]) if v.startswith(prefijo)]
        else:
            versiones = []

        self.combo_loader.addItems(versiones)
        disponible = tipo == "Vanilla" or bool(versiones)
        self.btn_crear.setEnabled(disponible)
        if mostrar and not versiones:
            self.lbl_estado.setText(f"No hay versiones de {tipo} para Minecraft {minecraft}.")
        else:
            self.lbl_estado.setText("Listo para crear la instancia.")

    def crear(self):
        nombre = self.txt_nombre.text().strip()
        if not nombre:
            QMessageBox.warning(self, "Nombre requerido", "Escribe un nombre para la instancia.")
            return
        if any(caracter in nombre for caracter in '<>:"/\\|?*'):
            QMessageBox.warning(self, "Nombre inválido", "El nombre contiene caracteres no permitidos.")
            return
        version_url = self.combo_minecraft.currentData()
        if not version_url:
            QMessageBox.warning(
                self, "Versión inválida", "Selecciona una versión de Minecraft de la lista oficial."
            )
            return

        self.btn_crear.setEnabled(False)
        self.btn_cancelar.setEnabled(False)
        self.worker_instalacion = ServerInstallWorker(
            self.ruta_instancias,
            nombre,
            self.combo_grupo.currentText().strip() or "No agrupado",
            self.combo_tipo.currentText(),
            self.combo_minecraft.currentText(),
            self.combo_loader.currentText(),
            version_url,
            self.catalogo["fabric_installer"],
            self.java_exe,
        )
        self.worker_instalacion.progreso.connect(self.barra.setValue)
        self.worker_instalacion.estado.connect(self.lbl_estado.setText)
        self.worker_instalacion.log.connect(self.log_instalacion.appendPlainText)
        self.worker_instalacion.finalizado.connect(self.instalacion_finalizada)
        self.worker_instalacion.start()

    def instalacion_finalizada(self, exito, mensaje, ruta):
        self.btn_cancelar.setEnabled(True)
        if exito:
            QMessageBox.information(self, "Instancia creada", mensaje)
            self.accept()
        else:
            self.btn_crear.setEnabled(True)
            self.barra.setValue(0)
            self.lbl_estado.setText("Falló la instalación.")
            QMessageBox.critical(self, "No se pudo crear la instancia", mensaje)
