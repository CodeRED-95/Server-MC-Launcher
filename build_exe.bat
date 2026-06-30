@echo off
setlocal enabledelayedexpansion

set "PROJECT_DIR=%~dp0"
set "SPEC_FILE=%PROJECT_DIR%launcher.spec"
set "DIST_DIR=%PROJECT_DIR%dist"
set "BUILD_DIR=%PROJECT_DIR%build"
set "PYTHON_EXE="

echo Building executable...
if exist "%PROJECT_DIR%.venv\Scripts\python.exe" (
    set "PYTHON_EXE=%PROJECT_DIR%.venv\Scripts\python.exe"
) else (
    where python >nul 2>&1
    if not errorlevel 1 (
        set "PYTHON_EXE=python"
    ) else (
        where py >nul 2>&1
        if not errorlevel 1 (
            set "PYTHON_EXE=py"
        )
    )
)

if not defined PYTHON_EXE (
    echo.
    echo No se encontro Python.
    echo Instala Python o crea un entorno virtual en .venv.
    exit /b 1
)

"%PYTHON_EXE%" "%PROJECT_DIR%make_installer_icon.py"
if errorlevel 1 (
    echo.
    echo No se pudo generar el icono del instalador.
    exit /b 1
)

"%PYTHON_EXE%" -m PyInstaller --noconfirm --clean "%SPEC_FILE%"
if errorlevel 1 (
    echo.
    echo Build failed.
    exit /b 1
)

echo Cleaning build folder...
if exist "%BUILD_DIR%" rmdir /s /q "%BUILD_DIR%"

echo Done.
echo EXE available in "%DIST_DIR%".
endlocal
