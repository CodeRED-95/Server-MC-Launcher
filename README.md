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
- `make_installer_icon.py`: convierte `assets/app_icon.png` a `.ico` para el instalador

## Crear el ejecutable

Ejecuta:

```bat
build_exe.bat
```

El script hace lo siguiente:

0. Convierte `assets/app_icon.png` a `assets/installer_icon.ico` para Inno Setup
1. Compila el proyecto con `PyInstaller` usando `launcher.spec`
2. Genera una carpeta de aplicación dentro de `dist\Server MC Launcher`
3. Elimina la carpeta `build` al finalizar

Si tienes un entorno virtual en `.venv`, el script lo usa automáticamente. Si no existe, usa `py -m PyInstaller`.

## Crear el instalador

1. Ejecuta primero `build_exe.bat`
2. Abre `installer.iss` con Inno Setup
3. Compila el script para generar el instalador

El instalador toma el `.exe` desde `dist\ServerMCLauncher.exe`.
El instalador toma toda la carpeta de aplicación desde `dist\Server MC Launcher` y además copia `instancias`, `java` y `tools` dentro de `{app}`.
El instalador usa `assets/installer_icon.ico` como icono del asistente, generado desde `assets/app_icon.png`.

## Notas

- El icono de la app se carga desde `assets/app_icon.png`
- El instalador usa `assets/installer_icon.ico` como icono del asistente y el programa instalado conserva el icono de la app
- El archivo `.ico` del instalador se genera desde el mismo `assets/app_icon.png`
- Si agregas más recursos que deban viajar con el programa, recuerda incluirlos en `launcher.spec` y, si corresponde, en `installer.iss`
- `Instancias` y `java` se instalan dentro de `Server MC Launcher`, no en temporales
- El ejecutable y el instalador están configurados para no pedir elevación de administrador
- Para compatibilidad, el instalador crea `instancias` y `javas` como enlaces de carpeta hacia `Instancias` y `java`
