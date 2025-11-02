# Arquitectura de Ingesta en Tiempo Real

## Resumen

Este documento describe la arquitectura del sistema de ingesta en tiempo real que reemplaza el sistema basado en CSV por un pipeline resiliente con almacenamiento transaccional.

## Componentes Principales

### 1. Capa de Ingesta

#### 1.1 WebSocket Stream Consumer
- **Ubicación**: `backend/ingestion/websocket_consumer.py`
- **Responsabilidad**: Mantener conexión WebSocket con Binance para recibir actualizaciones de klines en tiempo real
- **Características**:
  - Reconexión automática con backoff exponencial
  - Buffer de mensajes para manejar latencia de red
  - Parsing y validación de mensajes
  - Encolado en cola persistente (Redis/Disk)

#### 1.2 REST Polling Fallback
- **Ubicación**: `backend/ingestion/polling_consumer.py`
- **Responsabilidad**: Polling periódico cuando WebSocket no está disponible
- **Características**:
  - Intervalos configurables por timeframe
  - Detección de cambios incrementales
  - Manejo de rate limits de Binance API

#### 1.3 Message Queue/Buffer
- **Implementación**: Redis Queue o cola en disco (SQLite/PostgreSQL)
- **Responsabilidad**: Buffer persistente de mensajes antes de procesamiento
- **Garantías**:
  - At-least-once delivery
  - Ordenamiento por timestamp
  - Retención temporal para recuperación ante fallos

### 2. Capa de Almacenamiento

#### 2.1 Base de Datos
- **Motor**: PostgreSQL con extensión TimescaleDB
- **Justificación**:
  - Optimizado para time-series data
  - Compresión automática de datos históricos
  - Queries eficientes por rangos temporales
  - Transacciones ACID

#### 2.2 Esquema de Datos

**Tabla: ohlcv_candles**
```sql
CREATE TABLE ohlcv_candles (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    timestamp BIGINT NOT NULL,  -- Unix timestamp en ms
    open DECIMAL(20, 8) NOT NULL,
    high DECIMAL(20, 8) NOT NULL,
    low DECIMAL(20, 8) NOT NULL,
    close DECIMAL(20, 8) NOT NULL,
    volume DECIMAL(30, 8) NOT NULL,
    quote_volume DECIMAL(30, 8),
    trades INTEGER,
    taker_buy_base DECIMAL(30, 8),
    taker_buy_quote DECIMAL(30, 8),
    close_time BIGINT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(symbol, timeframe, timestamp)
);

-- Índices
CREATE INDEX idx_ohlcv_symbol_timeframe_timestamp ON ohlcv_candles(symbol, timeframe, timestamp DESC);
CREATE INDEX idx_ohlcv_timestamp ON ohlcv_candles(timestamp DESC);

-- Hypertable de TimescaleDB
SELECT create_hypertable('ohlcv_candles', 'timestamp', chunk_time_interval => INTERVAL '7 days');
```

**Tabla: ingestion_status**
```sql
CREATE TABLE ingestion_status (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    last_ingested_timestamp BIGINT,
    last_ingested_at TIMESTAMP WITH TIME ZONE,
    ingestion_mode VARCHAR(20),  -- 'websocket', 'polling', 'backfill'
    status VARCHAR(20),  -- 'active', 'paused', 'error'
    error_message TEXT,
    latency_ms INTEGER,  -- Última latencia medida
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(symbol, timeframe)
);
```

**Tabla: ingestion_metrics**
```sql
CREATE TABLE ingestion_metrics (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    metric_type VARCHAR(50) NOT NULL,  -- 'latency', 'error_rate', 'throughput'
    metric_value DECIMAL(20, 4),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_metrics_symbol_timeframe_timestamp ON ingestion_metrics(symbol, timeframe, timestamp DESC);
SELECT create_hypertable('ingestion_metrics', 'timestamp', chunk_time_interval => INTERVAL '1 day');
```

### 3. Capa de Repositorios

#### 3.1 OHLCV Repository
- **Ubicación**: `backend/repositories/ohlcv_repository.py`
- **Interfaz**:
  - `save_candle(candle: Dict) -> None`
  - `save_batch(candles: List[Dict]) -> None`
  - `get_latest(symbol: str, timeframe: str) -> Optional[Dict]`
  - `get_range(symbol: str, timeframe: str, start: int, end: int) -> List[Dict]`
  - `to_dataframe(symbol: str, timeframe: str, limit: int = None) -> pd.DataFrame`

#### 3.2 Ingestion Status Repository
- **Ubicación**: `backend/repositories/ingestion_repository.py`
- **Interfaz**:
  - `update_status(symbol: str, timeframe: str, status: Dict) -> None`
  - `get_status(symbol: str, timeframe: str) -> Optional[Dict]`
  - `get_all_statuses() -> List[Dict]`

### 4. Capa de Procesamiento

#### 4.1 Message Processor
- **Ubicación**: `backend/ingestion/processor.py`
- **Responsabilidad**: Procesar mensajes de cola y persistir en BD
- **Características**:
  - Validación de datos
  - Deduplicación
  - Batching para eficiencia
  - Manejo de errores con retry

#### 4.2 Scheduler/Tasks
- **Ubicación**: `backend/tasks/`
- **Jobs**:
  - `data_ingestion_task.py`: Orquesta ingesta continua
  - `gap_filling_task.py`: Detecta y rellena gaps
  - `validation_task.py`: Valida integridad de datos
  - `backfill_task.py`: Backfill histórico cuando necesario

### 5. Capa de Monitoreo

#### 5.1 Métricas Estructuradas
- **Formato**: Prometheus-compatible
- **Métricas**:
  - `ingestion_latency_seconds` (histogram)
  - `ingestion_errors_total` (counter)
  - `ingestion_candles_processed_total` (counter)
  - `ingestion_queue_size` (gauge)
  - `ingestion_status` (gauge)

#### 5.2 Logging Estructurado
- **Formato**: JSON con structlog
- **Campos**:
  - timestamp, level, logger, message
  - symbol, timeframe, latency_ms
  - error_type, error_message (si aplica)

## Flujo de Datos

### Flujo Principal (WebSocket)
```
Binance WebSocket → WebSocketConsumer → MessageQueue → Processor → PostgreSQL/TimescaleDB
                                      ↓
                                   Metrics/Logs
```

### Flujo Fallback (REST Polling)
```
Scheduler → PollingConsumer → Binance REST API → Processor → PostgreSQL/TimescaleDB
                              ↓
                           Metrics/Logs
```

### Flujo de Consulta
```
API Request → OHLCVRepository → PostgreSQL → DataFrame → Response
```

## Migración desde CSV

### Fase 1: Migración de Datos Existentes
1. Script de migración: `backend/scripts/migrate_csv_to_db.py`
2. Lee todos los CSV existentes
3. Inserta en PostgreSQL con deduplicación
4. Valida integridad post-migración

### Fase 2: Dual-Write (Transición)
1. Escribir simultáneamente a CSV y BD
2. Validar consistencia
3. Gradualmente desactivar escritura a CSV

### Fase 3: Solo BD
1. Remover dependencias de CSV
2. Actualizar todos los servicios para usar repositorios
3. Mantener CSV como backup/export opcional

## Configuración

### Variables de Entorno
```bash
# Base de Datos
DATABASE_URL=postgresql://user:pass@localhost:5432/black_trade
TIMESCALEDB_ENABLED=true

# Ingesta
INGESTION_MODE=websocket  # o 'polling'
WEBSOCKET_RECONNECT_DELAY=5
POLLING_INTERVAL_1m=60
POLLING_INTERVAL_1h=300

# Queue
REDIS_URL=redis://localhost:6379/0
QUEUE_BATCH_SIZE=100

# Monitoreo
METRICS_ENABLED=true
METRICS_PORT=9090
LOG_LEVEL=INFO
```

## Resiliencia

### Reconexión Automática
- Backoff exponencial: 1s, 2s, 4s, 8s, 16s, max 60s
- Límite de reintentos antes de cambiar a polling

### Manejo de Errores
- Errores transitorios: retry con backoff
- Errores persistentes: alerta y switch a polling
- Errores de validación: log y skip

### Recuperación ante Fallos
- Cola persistente mantiene mensajes
- Processor reanuda desde último timestamp procesado
- Gap detection task rellena períodos perdidos

## Performance

### Optimizaciones
- Batching de inserts (100-1000 candles por batch)
- Prepared statements
- Compresión de TimescaleDB
- Índices optimizados para queries por timeframe

### Escalabilidad
- Processor puede ejecutarse en múltiples workers
- Particionamiento por símbolo/timeframe
- Distribución horizontal con sharding si necesario

## Referencias
- [Binance WebSocket Streams](https://binance-docs.github.io/apidocs/spot/en/#websocket-market-streams)
- [TimescaleDB Documentation](https://docs.timescale.com/)
- [Prometheus Metrics](https://prometheus.io/docs/concepts/metric_types/)

