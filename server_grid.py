import math
import os

from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QListWidget,
    QListWidgetItem,
    QScrollArea,
    QFrame,
    QToolButton,
    QVBoxLayout,
    QWidget,
)


class ServerGroupSection(QWidget):
    item_selected = pyqtSignal(object, object)

    CARD_WIDTH = 125
    CARD_HEIGHT = 135

    def __init__(self, nombre, expandido=True, parent=None):
        super().__init__(parent)
        self.nombre = nombre

        self.header = QToolButton()
        self.header.setCheckable(True)
        self.header.setChecked(expandido)
        self.header.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self.header.setStyleSheet(
            "QToolButton { text-align: left; border: none; border-bottom: 1px solid #404040; "
            "padding: 6px; color: #d8dee9; font-weight: bold; }"
        )

        self.lista = QListWidget()
        self.lista.setViewMode(QListWidget.ViewMode.IconMode)
        self.lista.setIconSize(QSize(64, 64))
        self.lista.setGridSize(QSize(self.CARD_WIDTH, self.CARD_HEIGHT))
        self.lista.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.lista.setMovement(QListWidget.Movement.Static)
        self.lista.setWrapping(True)
        self.lista.setWordWrap(True)
        self.lista.setSpacing(2)
        self.lista.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.lista.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.lista.setStyleSheet("""
            QListWidget { background: transparent; border: none; outline: none; }
            QListWidget::item {
                background-color: #242424; color: white; border-radius: 3px;
                padding: 5px; margin: 2px;
            }
            QListWidget::item:selected { background-color: #b92727; }
            QListWidget::item:hover { background-color: #3a3a3a; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 4)
        layout.setSpacing(2)
        layout.addWidget(self.header)
        layout.addWidget(self.lista)

        self.header.toggled.connect(self._cambiar_expansion)
        self.lista.currentItemChanged.connect(self.item_selected.emit)
        self.aplicar_tema("oscuro")
        self._cambiar_expansion(expandido)

    def aplicar_tema(self, tema):
        if tema == "claro":
            fondo, tarjeta, hover, texto, borde, seleccion = (
                "#f4f6f8", "#ffffff", "#e5eaf0", "#1f2937", "#cbd5e1", "#2563eb"
            )
        else:
            fondo, tarjeta, hover, texto, borde, seleccion = (
                "#181a1f", "#252830", "#343944", "#eef2f7", "#3b414c", "#c43d4d"
            )
        self.header.setStyleSheet(
            f"QToolButton {{ text-align: left; border: none; border-bottom: 1px solid {borde}; "
            f"padding: 7px; color: {texto}; font-weight: bold; }}"
        )
        self.lista.setStyleSheet(f"""
            QListWidget {{ background: {fondo}; border: none; outline: none; }}
            QListWidget::item {{
                background-color: {tarjeta}; color: {texto}; border-radius: 6px;
                padding: 6px; margin: 3px;
            }}
            QListWidget::item:selected {{ background-color: {seleccion}; color: white; }}
            QListWidget::item:hover {{ background-color: {hover}; }}
        """)

    def _cambiar_expansion(self, expandido):
        self.header.setText(f"{'▼' if expandido else '▶'}  {self.nombre}")
        self.lista.setVisible(expandido)
        if expandido:
            self.ajustar_altura()

    def agregar_servidor(self, nombre, ruta_icono=None):
        item = QListWidgetItem(nombre)
        item.setTextAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        if ruta_icono and os.path.isfile(ruta_icono):
            item.setIcon(QIcon(ruta_icono))
        else:
            item.setIcon(QIcon.fromTheme("folder-remote"))
        self.lista.addItem(item)

    def ajustar_altura(self):
        ancho = max(self.lista.viewport().width(), self.width(), self.CARD_WIDTH)
        columnas = max(1, ancho // self.CARD_WIDTH)
        filas = max(1, math.ceil(self.lista.count() / columnas))
        self.lista.setFixedHeight(filas * self.CARD_HEIGHT + 8)


class GroupedServerGrid(QScrollArea):
    currentItemChanged = pyqtSignal(object, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setStyleSheet("QScrollArea { background-color: #1e1e1e; border-radius: 6px; }")

        self.contenido = QWidget()
        self.layout_grupos = QVBoxLayout(self.contenido)
        self.layout_grupos.setContentsMargins(6, 6, 6, 6)
        self.layout_grupos.setSpacing(2)
        self.layout_grupos.addStretch()
        self.setWidget(self.contenido)

        self.secciones = {}
        self._item_actual = None
        self._estados_expansion = {}
        self.tema = "oscuro"

    def currentItem(self):
        return self._item_actual

    def grupos(self):
        return list(self.secciones)

    def set_servidores(self, servidores):
        seleccionado = self._item_actual.text() if self._item_actual else None
        self._estados_expansion.update(
            {nombre: seccion.header.isChecked() for nombre, seccion in self.secciones.items()}
        )
        self._limpiar()

        agrupados = {}
        for servidor in servidores:
            grupo = servidor.get("grupo") or "No agrupado"
            agrupados.setdefault(grupo, []).append(servidor)

        nombres_grupo = sorted(agrupados, key=lambda nombre: (nombre != "No agrupado", nombre.lower()))
        for nombre_grupo in nombres_grupo:
            seccion = ServerGroupSection(
                nombre_grupo,
                expandido=self._estados_expansion.get(nombre_grupo, True),
            )
            seccion.aplicar_tema(self.tema)
            seccion.item_selected.connect(self._seleccionar_item)
            for servidor in sorted(agrupados[nombre_grupo], key=lambda item: item["nombre"].lower()):
                seccion.agregar_servidor(servidor["nombre"], servidor.get("icono"))
            self.layout_grupos.insertWidget(self.layout_grupos.count() - 1, seccion)
            self.secciones[nombre_grupo] = seccion

            if seleccionado:
                coincidencias = seccion.lista.findItems(seleccionado, Qt.MatchFlag.MatchExactly)
                if coincidencias:
                    seccion.lista.setCurrentItem(coincidencias[0])

        self._ajustar_alturas()

    def _limpiar(self):
        self._item_actual = None
        while self.layout_grupos.count() > 1:
            item_layout = self.layout_grupos.takeAt(0)
            widget = item_layout.widget()
            if widget:
                widget.deleteLater()
        self.secciones.clear()

    def _seleccionar_item(self, actual, anterior):
        if actual is None:
            return
        previo_global = self._item_actual
        self._item_actual = actual
        emisor = self.sender()
        for seccion in self.secciones.values():
            if seccion is not emisor:
                seccion.lista.blockSignals(True)
                seccion.lista.clearSelection()
                seccion.lista.setCurrentItem(None)
                seccion.lista.blockSignals(False)
        self.currentItemChanged.emit(actual, previo_global or anterior)

    def _ajustar_alturas(self):
        for seccion in self.secciones.values():
            seccion.ajustar_altura()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._ajustar_alturas()

    def aplicar_tema(self, tema):
        self.tema = tema
        fondo = "#f4f6f8" if tema == "claro" else "#181a1f"
        self.setStyleSheet(f"QScrollArea {{ background-color: {fondo}; border-radius: 8px; }}")
        self.contenido.setStyleSheet(f"background-color: {fondo};")
        for seccion in self.secciones.values():
            seccion.aplicar_tema(tema)
