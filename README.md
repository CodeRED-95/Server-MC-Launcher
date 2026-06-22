# Minecraft Server Launcher Grid Pro

Aplicación de escritorio en Python/PyQt para crear, configurar y lanzar instancias de servidores de Minecraft.

## Funciones principales

- Crear instancias desde ZIP.
- Descargar servidores FTB desde el catálogo oficial.
- Configurar Java por instancia o usar autodetección.
- Agrupar instancias.
- Cambiar iconos por instancia.
- Administrar mods instalados.
- Buscar y descargar mods desde Modrinth.
- Buscar y descargar mods desde CurseForge con API key.
- Integración con Playit para red pública.
- Tema oscuro y tema claro.

## Requisitos

- Windows 64-bit.
- Python 3.10 o superior.
- Dependencias de PyQt6 y módulos estándar del proyecto.
- Java portable o instalada para ejecutar las instancias.

## Cómo ejecutar

```bash
python main.py
```

## Java y detección automática

El launcher analiza el servidor y sus librerías para elegir la versión de Java adecuada.
Esto evita errores como:

- `Unsupported major.minor version 65.0`

Ese error normalmente significa que el servidor fue lanzado con una versión de Java demasiado vieja para el pack o el loader.

## Mods

En la pestaña de configuración de una instancia puedes:

- Ver la lista de mods instalados.
- Ver nombre, versión y archivo `.jar`.
- Eliminar uno o varios mods seleccionados.
- Abrir la carpeta de mods.
- Descargar mods desde Modrinth o CurseForge.

### CurseForge

CurseForge requiere una API key para buscar y descargar.
Si no la introduces, el buscador no podrá consultar resultados.

## Estructura general

- `main.py`: punto de entrada.
- `launcher.py`: ventana principal y ejecución de servidores.
- `components.py`: diálogos y ventanas de instalación/configuración.
- `workers.py`: tareas en segundo plano para descargas e instalación.

## Notas

- La autodetección de Java prioriza la compatibilidad del servidor.
- Para Forge o NeoForge modernos, el launcher puede requerir Java 17 o 21 según las clases encontradas en `server.jar` y `libraries/`.
- Si una instancia usa un loader más moderno, no fuerces una Java inferior.

