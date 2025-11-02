# Setup Guide: Real-Time Data Ingestion

Este documento describe cómo configurar y usar el sistema de ingesta en tiempo real que reemplaza el sistema basado en CSV.

## Requisitos Previos

### Base de Datos

1. **PostgreSQL 12+** instalado y ejecutándose
2. **TimescaleDB extension** (opcional pero recomendado para time-series):
   ```bash
   # Instalar TimescaleDB
   # Ver: https://docs.timescale.com/install/latest/self-hosted/
   
   # Conectar a PostgreSQL y habilitar extensión
   psql -U postgres -d black_trade
   CREATE EXTENSION IF NOT EXISTS timescaledb;
   ```

### Dependencias Python

```bash
pip install -r requirements.txt
```

## Configuración

### Variables de Entorno

Crear archivo `.env` o exportar variables:

```bash
# Base de Datos
DATABASE_URL=postgresql://user:password@localhost:5432/black_trade

# Ingesta
INGESTION_MODE=websocket  # o 'polling'
TRADING_PAIRS=BTCUSDT,ETHUSDT
TIMEFRAMES=15m,1h,4h,1d

# Opcional
DB_ECHO=false
WEBSOCKET_RECONNECT_DELAY=5
```

### Inicialización de Base de Datos

```bash
# Crear base de datos
createdb black_trade

# Ejecutar migraciones
python -m backend.db.migrations.001_initial_schema upgrade

# O usar SQLAlchemy para crear tablas
python -c "from backend.db.session import init_db, enable_timescaledb_hypertable; init_db(); enable_timescaledb_hypertable()"
```

## Migración desde CSV

Si tienes datos existentes en CSV, migrarlos a la base de datos:

```bash
python backend/scripts/migrate_csv_to_db.py
```

Este script:
- Lee todos los CSV en `data/ohlcv/`
- Parsea símbolos y timeframes del nombre de archivo
- Inserta en PostgreSQL con deduplicación
- Valida integridad

## Uso

### Iniciar Ingesta en Tiempo Real

#### Modo WebSocket (Recomendado)

```bash
python -m backend.tasks.data_ingestion_task websocket
```

O con variables de entorno:
```bash
INGESTION_MODE=websocket python -m backend.tasks.data_ingestion_task
```

#### Modo Polling (Fallback)

```bash
python -m backend.tasks.data_ingestion_task polling
```

### Tareas de Mantenimiento

#### Rellenar Gaps

```bash
python -m backend.tasks.gap_filling_task
```

Detecta y rellena gaps en datos históricos.

## Integración con Sistema Existente

### Actualizar SyncService para usar Repositorio

El `SyncService` actual puede actualizarse para escribir simultáneamente a CSV y BD (dual-write) durante la transición:

```python
from backend.repositories.ohlcv_repository import OHLCVRepository

repo = OHLCVRepository()

# En lugar de guardar solo CSV:
# sync_service._save_to_csv(candles, symbol, timeframe)

# Guardar también en BD:
repo.save_batch(candles)
```

### Actualizar Aplicación para Leer de BD

En lugar de:
```python
df = sync_service.load_ohlcv_data(symbol, timeframe)
```

Usar:
```python
from backend.repositories.ohlcv_repository import OHLCVRepository

repo = OHLCVRepository()
df = repo.to_dataframe(symbol, timeframe, limit=1000)
```

## Monitoreo

### Métricas Prometheus

Si está habilitado, las métricas están disponibles en:
- `http://localhost:9090/metrics` (si se configura servidor Prometheus)

Métricas principales:
- `ingestion_candles_processed_total`: Contador de candles procesados
- `ingestion_latency_seconds`: Histograma de latencia
- `ingestion_errors_total`: Contador de errores
- `ingestion_status`: Estado de ingesta por símbolo/timeframe

### Consultar Estado de Ingesta

```python
from backend.repositories.ingestion_repository import IngestionRepository

repo = IngestionRepository()
statuses = repo.get_all_statuses()

for status in statuses:
    print(f"{status['symbol']} {status['timeframe']}: {status['status']}")
    print(f"  Last ingested: {status['last_ingested_at']}")
    print(f"  Latency: {status['latency_ms']}ms")
```

## Troubleshooting

### Error: "TimescaleDB extension not found"

TimescaleDB es opcional. El sistema funcionará sin él usando PostgreSQL estándar. Para habilitar:
1. Instalar TimescaleDB según documentación oficial
2. Ejecutar `CREATE EXTENSION timescaledb;` en la base de datos

### Error: "Connection refused" al conectar a PostgreSQL

Verificar:
- PostgreSQL está ejecutándose
- `DATABASE_URL` es correcto
- Credenciales son válidas
- Firewall permite conexión

### WebSocket se desconecta frecuentemente

- Verificar conexión a internet
- Revisar rate limits de Binance
- Considerar usar modo polling como fallback
- Revisar logs para errores específicos

### Datos no aparecen en base de datos

1. Verificar que ingesta está ejecutándose
2. Revisar logs para errores
3. Verificar estado de ingesta: `repo.get_all_statuses()`
4. Verificar que símbolos/timeframes están correctamente configurados

## Próximos Pasos

1. **Integración completa**: Actualizar todos los servicios para usar repositorios
2. **Dashboard de monitoreo**: Crear dashboard Grafana para métricas
3. **Alertas**: Configurar alertas para errores de ingesta
4. **Optimización**: Ajustar batch sizes y timeouts según carga
5. **Escalabilidad**: Considerar múltiples workers para procesamiento

## Referencias

- [Arquitectura de Ingesta](./architecture/realtime_ingestion.md)
- [Documentación Binance WebSocket](https://binance-docs.github.io/apidocs/spot/en/#websocket-market-streams)
- [TimescaleDB Documentation](https://docs.timescale.com/)

