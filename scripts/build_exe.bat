@echo off
REM Script para compilar GraphUG como ejecutable .exe con PyInstaller
REM Uso: build_exe.bat [clean]

setlocal enabledelayedexpansion

echo.
echo ========================================
echo   GraphUG EXE Builder (PyInstaller)
echo ========================================
echo.

REM Verificar si se debe limpiar
if "%1"=="clean" (
    echo Limpiando directorios de compilacion anterior...
    if exist dist (
        rmdir /s /q dist
        echo   - Directorio dist eliminado
    )
    if exist build (
        rmdir /s /q build
        echo   - Directorio build eliminado
    )
    echo.
)

REM Verificar si PyInstaller está instalado
echo Verificando PyInstaller...
pip list | find /i "pyinstaller" >nul
if errorlevel 1 (
    echo PyInstaller no esta instalado. Instalando...
    pip install pyinstaller
    if errorlevel 1 (
        echo ERROR: Fallo al instalar PyInstaller
        exit /b 1
    )
)

REM Compilar
echo.
echo Compilando GraphUG...
echo.
set SPEC_FILE=GraphUG.spec
if not exist "%SPEC_FILE%" (
    set SPEC_FILE=main.spec
)

if not exist "%SPEC_FILE%" (
    echo ERROR: No se encontró GraphUG.spec ni main.spec
    exit /b 1
)

pyinstaller %SPEC_FILE%

if errorlevel 1 (
    echo.
    echo ERROR: Fallo durante la compilacion
    exit /b 1
)

echo.
echo ========================================
echo   Compilacion exitosa!
echo ========================================
echo.
echo Ejecutable: dist\GraphUG.exe
echo.
echo Para distribuir la aplicacion, comparte la carpeta dist/ completa
echo.
pause

