# Guía de Ingesta de Datos de Mercado

## Resumen

Este documento describe cómo poblar y mantener datos de mercado en Black Trade. El sistema incluye bootstrap histórico, ingesta en tiempo real (WebSocket/Polling), y verificación automática de datos.

## Arquitectura de Ingesta

### Componentes Principales

1. **DataBootstrap** (`backend/ingestion/bootstrap.py`): Población inicial de datos históricos
2. **DataIngestionTask** (`backend/tasks/data_ingestion_task.py`): Orquestador de ingesta en tiempo real
3. **WebSocketConsumer** (`backend/ingestion/websocket_consumer.py`): Consumo de datos en tiempo real vía WebSocket
4. **PollingConsumer** (`backend/ingestion/polling_consumer.py`): Consumo de datos vía REST polling (fallback)
5. **MessageProcessor** (`backend/ingestion/processor.py`): Procesamiento y persistencia de velas

### Flujo de Datos

```
Exchange (Binance) → Consumer (WebSocket/Polling) → Processor → Database (PostgreSQL)
                                                          ↓
                                                   Signal Computation
```

## Inicialización: Bootstrap de Datos Históricos

### Primer Poblado de Datos

Antes de iniciar la ingesta en tiempo real, es necesario poblar datos históricos para:
- Backtesting de estrategias
- Análisis técnico inicial
- Validación de señales

### Ejecutar Bootstrap

```bash
# Bootstrap con configuración por defecto (símbolos y timeframes desde .env)
python -m backend.ingestion.bootstrap

# Bootstrap con opciones personalizadas
python -m backend.ingestion.bootstrap \
    --symbols BTCUSDT,ETHUSDT \
    --timeframes 15m,1h,4h,1d \
    --days 90 \
    --verify
```

### Parámetros

- `--symbols`: Símbolos a poblar (comma-separated, default: desde `TRADING_PAIRS`)
- `--timeframes`: Timeframes a poblar (comma-separated, default: desde `TIMEFRAMES`)
- `--days`: Días de historia a obtener (opcional, usa defaults por timeframe si no se especifica)
- `--verify`: Ejecutar verificación después del bootstrap

### Días Requeridos por Timeframe

El bootstrap usa estos valores por defecto:

| Timeframe | Días Requeridos | Propósito |
|-----------|----------------|-----------|
| 1m        | 7 días         | Análisis de alta frecuencia |
| 5m        | 14 días        | Trading de corto plazo |
| 15m       | 30 días        | Trading intradiario |
| 1h        | 90 días        | Análisis de tendencias |
| 4h        | 180 días       | Análisis de mediano plazo |
| 1d        | 365 días       | Análisis de largo plazo |
| 1w        | 730 días       | Análisis macro |

### Ejemplo de Salida

```
======================================================================
Starting historical data bootstrap
Symbols: ['BTCUSDT']
Timeframes: ['15m', '1h', '4h', '1d']
======================================================================
Populating BTCUSDT 15m from 2024-01-01 to 2024-12-01
BTCUSDT 15m: 100%|████████████| 2880/2880 [02:15<00:00, 21.3candle/s]
✓ Completed BTCUSDT 15m: 2880 candles saved

Progress: 1/4 completed
...

======================================================================
Bootstrap complete
Success: 4/4
Errors: 0/4
======================================================================
```

## Ingesta en Tiempo Real

### Iniciar Ingesta Automática

La ingesta en tiempo real se inicia automáticamente cuando arranca el backend:

```bash
python -m uvicorn backend.app:app --reload
```

El scheduler (`backend/tasks/scheduler.py`) inicializa `DataIngestionTask` en el evento de startup.

### Modos de Ingesta

#### WebSocket (Recomendado)

- **Ventajas**: Tiempo real, baja latencia, eficiente
- **Configuración**: `INGESTION_MODE=websocket` (default)

#### Polling (Fallback)

- **Ventajas**: Más confiable si WebSocket falla
- **Desventajas**: Mayor latencia, más requests
- **Configuración**: `INGESTION_MODE=polling`

### Variables de Entorno

```bash
# Símbolos a ingerir
TRADING_PAIRS=BTCUSDT,ETHUSDT

# Timeframes a ingerir
TIMEFRAMES=15m,1h,4h,1d

# Modo de ingesta
INGESTION_MODE=websocket  # o 'polling'

# Intervalos de polling (si usa polling mode)
POLLING_INTERVAL_1h=3600
POLLING_INTERVAL_4h=14400
POLLING_INTERVAL_1d=86400
```

## Verificación de Datos

### Verificar Estado de Datos

El sistema incluye verificación automática de datos:

```python
from backend.ingestion.bootstrap import DataBootstrap

bootstrap = DataBootstrap()
report = bootstrap.verify_data('BTCUSDT', ['15m', '1h', '4h', '1d'])

print(f"Overall status: {report['overall_status']}")
for tf, data in report['timeframes'].items():
    print(f"{tf}: {data['status']} ({data['count']} candles)")
    for issue in data.get('issues', []):
        print(f"  ⚠ {issue}")
```

### Criterios de Verificación

- **Estado `ok`**: Datos completos y frescos
- **Estado `missing`**: No hay datos disponibles
- **Estado `stale`**: Los datos están desactualizados
- **Estado `incomplete`**: Faltan datos históricos requeridos

### Límites de Frescura

| Timeframe | Máximo Edad Esperada |
|-----------|---------------------|
| 1m        | 6 minutos           |
| 5m        | 30 minutos          |
| 15m       | 1 hora              |
| 1h        | 2 horas             |
| 4h        | 5 horas             |
| 1d        | 25 horas            |
| 1w        | 7 días              |

## Mantenimiento en Producción

### Monitoreo de Ingesta

El sistema registra métricas de ingesta en la tabla `ingestion_status`:

```sql
SELECT 
    symbol, 
    timeframe, 
    status, 
    last_ingested_at,
    ingestion_mode
FROM ingestion_status
ORDER BY last_ingested_at DESC;
```

### Alertas Recomendadas

1. **Datos faltantes**: Alertar si ningún símbolo tiene datos en las últimas 2 horas
2. **Datos desactualizados**: Alertar si la edad de los datos excede los límites de frescura
3. **Errores de ingesta**: Alertar si hay errores consecutivos en la ingesta

### Recuperación de Datos Perdidos

Si se pierden datos, se pueden repoblar con bootstrap:

```bash
# Repoblar últimos 7 días
python -m backend.ingestion.bootstrap \
    --symbols BTCUSDT \
    --timeframes 1h,4h,1d \
    --days 7
```

### Limpieza de Datos Antiguos (Opcional)

Para optimizar el almacenamiento, se pueden eliminar datos muy antiguos:

```sql
-- Eliminar velas de más de 2 años (ajustar según necesidades)
DELETE FROM ohlcv_candles 
WHERE timestamp < EXTRACT(EPOCH FROM NOW() - INTERVAL '2 years') * 1000;
```

## Scripts de Despliegue

### Script de Inicialización Completa

```bash
#!/bin/bash
# scripts/setup_ingestion.sh

echo "Setting up data ingestion..."

# 1. Verificar base de datos
python -c "from backend.db.session import engine; engine.connect()"

# 2. Bootstrap histórico
python -m backend.ingestion.bootstrap --verify

# 3. Verificar que los datos están presentes
python -c "
from backend.ingestion.bootstrap import DataBootstrap
bootstrap = DataBootstrap()
report = bootstrap.verify_data('BTCUSDT', ['15m', '1h', '4h', '1d'])
if report['overall_status'] != 'ok':
    print('WARNING: Data verification failed')
    exit(1)
"

# 4. Iniciar backend (ingesta se inicia automáticamente)
echo "Setup complete. Start backend with: uvicorn backend.app:app"
```

### Cron Job para Verificación (Opcional)

```bash
# Verificar datos cada hora
0 * * * * cd /path/to/Black_Trade && python -m backend.ingestion.bootstrap --verify >> /var/log/ingestion_verify.log 2>&1
```

## Troubleshooting

### Problema: "No data found" después del bootstrap

**Solución**: Verificar que el bootstrap se completó correctamente:
```bash
python -m backend.ingestion.bootstrap --verify
```

### Problema: WebSocket se desconecta frecuentemente

**Solución**: El sistema automáticamente hace fallback a polling. Verificar logs:
```bash
grep "Falling back to polling" logs/app.log
```

### Problema: Datos desactualizados

**Solución**: Verificar que la ingesta está corriendo:
```bash
# Ver estado de ingesta
ps aux | grep data_ingestion_task

# Verificar última ingesta
python -c "from backend.repositories.ingestion_repository import IngestionRepository; repo = IngestionRepository(); print(repo.get_status('BTCUSDT', '1h'))"
```

## Mejores Prácticas

1. **Ejecutar bootstrap antes del primer despliegue**: Asegura datos históricos suficientes
2. **Monitorear logs de ingesta**: Detectar problemas temprano
3. **Configurar alertas**: Para datos faltantes o desactualizados
4. **Backup de datos críticos**: Especialmente antes de limpiezas
5. **Verificar periódicamente**: Ejecutar verificación manualmente o vía cron

## Referencias

- `backend/ingestion/bootstrap.py`: Módulo de bootstrap
- `backend/tasks/data_ingestion_task.py`: Tarea de ingesta
- `backend/repositories/ohlcv_repository.py`: Repositorio de datos OHLCV
- `data/binance_client.py`: Cliente de Binance API

