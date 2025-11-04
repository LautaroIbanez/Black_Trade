# Script para reiniciar PostgreSQL
# Ejecutar como administrador: Click derecho en PowerShell -> "Ejecutar como administrador"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Reiniciando servicio PostgreSQL" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

$serviceName = "postgresql-x64-18"

# Verificar si el servicio existe
$service = Get-Service -Name $serviceName -ErrorAction SilentlyContinue

if (-not $service) {
    Write-Host "ERROR: Servicio '$serviceName' no encontrado" -ForegroundColor Red
    Write-Host "Servicios PostgreSQL disponibles:" -ForegroundColor Yellow
    Get-Service | Where-Object {$_.Name -like "*postgres*"} | Select-Object Name, DisplayName, Status | Format-Table
    exit 1
}

Write-Host ""
Write-Host "Servicio encontrado: $($service.DisplayName)" -ForegroundColor Green
Write-Host "Estado actual: $($service.Status)" -ForegroundColor Yellow

# Reiniciar el servicio
try {
    Write-Host ""
    Write-Host "Deteniendo servicio..." -ForegroundColor Yellow
    Stop-Service -Name $serviceName -Force
    
    Write-Host "Esperando 2 segundos..." -ForegroundColor Yellow
    Start-Sleep -Seconds 2
    
    Write-Host "Iniciando servicio..." -ForegroundColor Yellow
    Start-Service -Name $serviceName
    
    Write-Host "Esperando 3 segundos para que el servicio se inicie completamente..." -ForegroundColor Yellow
    Start-Sleep -Seconds 3
    
    # Verificar estado
    $service.Refresh()
    if ($service.Status -eq 'Running') {
        Write-Host ""
        Write-Host "[OK] Servicio reiniciado exitosamente!" -ForegroundColor Green
        Write-Host "Estado: $($service.Status)" -ForegroundColor Green
    } else {
        Write-Host ""
        Write-Host "[ADVERTENCIA] Servicio no esta corriendo. Estado: $($service.Status)" -ForegroundColor Yellow
    }
} catch {
    Write-Host ""
    Write-Host "ERROR: No se pudo reiniciar el servicio" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host ""
    Write-Host "NOTA: Este script requiere permisos de administrador." -ForegroundColor Yellow
    Write-Host "Ejecuta PowerShell como administrador y vuelve a intentar." -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Reinicio completado" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
