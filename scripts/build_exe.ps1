#!/usr/bin/env pwsh
<#
.SYNOPSIS
Script para compilar GraphUG como ejecutable .exe con PyInstaller

.DESCRIPTION
Automatiza el proceso de empaquetación del proyecto GraphUG
incluyendo dependencias, icono y configuración necesaria.

.PARAMETER Clean
Si se proporciona, limpia los directorios de compilación antes de empaquetar

.EXAMPLE
.\build_exe.ps1
.\build_exe.ps1 -Clean
#>

param(
    [switch]$Clean
)

$specFile = if (Test-Path "GraphUG.spec") { "GraphUG.spec" } elseif (Test-Path "main.spec") { "main.spec" } else { $null }

Write-Host "╔════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║     GraphUG EXE Builder (PyInstaller)  ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Verificar que PyInstaller está instalado
$pyinstallerCheck = pip list | Select-String "pyinstaller"
if (-not $pyinstallerCheck) {
    Write-Host "❌ PyInstaller no está instalado." -ForegroundColor Red
    Write-Host "Instalando PyInstaller..." -ForegroundColor Yellow
    pip install pyinstaller
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Error al instalar PyInstaller" -ForegroundColor Red
        exit 1
    }
}

# Limpiar directorios previos si se pide
if ($Clean) {
    Write-Host "🧹 Limpiando directorios de compilación anterior..." -ForegroundColor Yellow
    if (Test-Path "dist") {
        Remove-Item -Recurse -Force "dist" -ErrorAction SilentlyContinue
        Write-Host "   ✓ Directorio dist eliminado" -ForegroundColor Green
    }
    if (Test-Path "build") {
        Remove-Item -Recurse -Force "build" -ErrorAction SilentlyContinue
        Write-Host "   ✓ Directorio build eliminado" -ForegroundColor Green
    }
}

# Verificar que el archivo .spec existe
if (-not $specFile) {
    Write-Host "❌ No se encontró GraphUG.spec ni main.spec en el directorio actual" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "🔨 Compilando GraphUG..." -ForegroundColor Yellow
Write-Host ""

# Ejecutar PyInstaller
pyinstaller $specFile

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✅ ¡Compilación exitosa!" -ForegroundColor Green
    Write-Host ""
    Write-Host "📦 El ejecutable se encuentra en:" -ForegroundColor Cyan
    Write-Host "   dist\GraphUG.exe" -ForegroundColor White
    Write-Host ""
    Write-Host "📁 Toda la carpeta dist/ contiene la aplicación lista para distribuir" -ForegroundColor Cyan
    Write-Host ""

    # Mostrar tamaño del ejecutable
    if (Test-Path "dist\GraphUG.exe") {
        $fileSize = (Get-Item "dist\GraphUG.exe").Length / 1MB
        Write-Host "📊 Tamaño del ejecutable: $([math]::Round($fileSize, 2)) MB" -ForegroundColor Magenta
    }
} else {
    Write-Host ""
    Write-Host "❌ Error durante la compilación" -ForegroundColor Red
    exit 1
}

