# Server MC Launcher

Launcher de escritorio para administrar y abrir un servidor de Minecraft desde una interfaz de PyQt6.

## Requisitos

- Python 3.11 o superior
- `PyQt6`
- `PyInstaller`
- Inno Setup para generar el instalador `.exe` de instalación

## Estructura principal

- `main.py`: punto de entrada de la aplicación
- `launcher.py`: ventana principal del launcher
- `assets/`: iconos y recursos de la interfaz
- `launcher.spec`: configuración de PyInstaller
- `build_exe.bat`: compila el ejecutable y limpia `build`
- `installer.iss`: script de Inno Setup para el instalador

## Crear el ejecutable

Ejecuta:

```bat
build_exe.bat
```

El script hace lo siguiente:

1. Compila el proyecto con `PyInstaller` usando `launcher.spec`
2. Genera el ejecutable dentro de `dist`
3. Elimina la carpeta `build` al finalizar

Si tienes un entorno virtual en `.venv`, el script lo usa automáticamente. Si no existe, usa `py -m PyInstaller`.

## Crear el instalador

1. Ejecuta primero `build_exe.bat`
2. Abre `installer.iss` con Inno Setup
3. Compila el script para generar el instalador

El instalador toma el `.exe` desde `dist\ServerMCLauncher.exe`.
Por compatibilidad, el script no fuerza `SetupIconFile`; si quieres un icono del instalador, conviene usar un `.ico` pequeño en lugar de un `.png`.

## Notas

- El icono de la app se carga desde `assets/app_icon.png`
- El instalador usa el icono del programa instalado, no un icono propio del asistente
- Si agregas más recursos que deban viajar con el programa, recuerda incluirlos en `launcher.spec` y, si corresponde, en `installer.iss`
