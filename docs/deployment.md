# Guía de Deployment - Black Trade

## Resumen

Esta guía describe cómo desplegar Black Trade en producción, con ingesta automática de datos y sin dependencia de archivos CSV.

## Arquitectura

### Componentes Principales

1. **Backend API** (FastAPI)
   - Servidor principal
   - Endpoints REST y WebSocket
   - Servicios de trading

2. **Ingesta de Datos**
   - WebSocket consumer (tiempo real)
   - Polling consumer (fallback)
   - Pipeline de procesamiento

3. **Base de Datos**
   - PostgreSQL con TimescaleDB (opcional)
   - Migraciones automáticas

4. **Scheduler**
   - APScheduler para tareas periódicas
   - Ingesta automática de datos

## Requisitos Previos

### Software

- Python 3.9+
- PostgreSQL 12+ (TimescaleDB opcional)
- Redis (opcional, para rate limiting distribuido)

### Variables de Entorno

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/black_trade

# Trading
TRADING_PAIRS=BTCUSDT,ETHUSDT
TIMEFRAMES=15m,1h,4h,1d
INGESTION_MODE=websocket  # or 'polling'

# Binance API (opcional, solo si se usa exchange real)
BINANCE_API_KEY=your_api_key
BINANCE_API_SECRET=your_api_secret
BINANCE_TESTNET=false

# Observability
OTLP_ENDPOINT=http://localhost:4317
ENABLE_TRACING=true
ENABLE_METRICS=true

# Security
SLACK_WEBHOOK_URL=https://hooks.slack.com/...
PAGERDUTY_INTEGRATION_KEY=your_key
```

## Instalación

### 1. Clonar Repositorio

```bash
git clone <repository_url>
cd Black_Trade
```

### 2. Instalar Dependencias

```bash
pip install -r requirements.txt
```

### 3. Configurar Base de Datos

```bash
# Crear base de datos
createdb black_trade

# O con usuario específico
psql -U postgres
CREATE DATABASE black_trade;
CREATE USER black_trade_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE black_trade TO black_trade_user;
```

### 4. Configurar Variables de Entorno

Crear archivo `.env`:

```bash
cp .env.example .env
# Editar .env con tus valores
```

### 5. Inicializar Base de Datos

Las migraciones se ejecutan automáticamente al arrancar el backend, pero puedes ejecutarlas manualmente:

```bash
python backend/db/init_db.py
```

## Ejecución

### Modo Desarrollo

```bash
# Backend
uvicorn backend.app:app --reload --host 0.0.0.0 --port 8000

# Frontend (en otra terminal)
cd frontend
npm install
npm run dev
```

### Modo Producción

#### Opción 1: Con Gunicorn

```bash
gunicorn backend.app:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --timeout 120
```

#### Opción 2: Con Docker

```dockerfile
# Dockerfile de ejemplo
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
docker build -t black-trade .
docker run -d \
    --name black-trade \
    -p 8000:8000 \
    --env-file .env \
    black-trade
```

#### Opción 3: Con Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  db:
    image: timescale/timescaledb:latest-pg14
    environment:
      POSTGRES_USER: black_trade
      POSTGRES_PASSWORD: secure_password
      POSTGRES_DB: black_trade
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  backend:
    build: .
    environment:
      DATABASE_URL: postgresql://black_trade:secure_password@db:5432/black_trade
      INGESTION_MODE: websocket
    depends_on:
      - db
    ports:
      - "8000:8000"

volumes:
  postgres_data:
```

```bash
docker-compose up -d
```

## Ingesta Automática de Datos

### Configuración

La ingesta se inicia automáticamente al arrancar el backend. Configura el modo en `.env`:

```bash
INGESTION_MODE=websocket  # WebSocket en tiempo real (recomendado)
# o
INGESTION_MODE=polling    # Polling REST (fallback)
```

### Símbolos y Timeframes

Configurar en variables de entorno:

```bash
TRADING_PAIRS=BTCUSDT,ETHUSDT,ADAUSDT
TIMEFRAMES=15m,1h,4h,1d
```

### Verificar Ingesta

```bash
# Verificar estado
curl http://localhost:8000/api/chart/status

# Ver logs
tail -f logs/app.log
```

## Migraciones de Base de Datos

### Automáticas

Las migraciones se ejecutan automáticamente al arrancar el backend.

### Manuales

```bash
# Ejecutar todas las migraciones
python backend/db/init_db.py

# Ejecutar migración específica
python backend/db/migrations/001_initial_schema.py upgrade
python backend/db/migrations/002_strategy_results.py upgrade
python backend/db/migrations/003_risk_metrics.py upgrade
```

## Endpoints Principales

### Health Check
```bash
GET /api/health
```

### Datos de Mercado
```bash
GET /api/chart/{symbol}/{timeframe}
GET /api/chart/status
```

### Recomendaciones
```bash
GET /api/recommendation?profile=balanced
```

### Riesgo
```bash
GET /api/risk/status
GET /api/risk/exposure
```

### Ejecución
```bash
GET /api/execution/orders
POST /api/execution/orders
```

## Monitoreo

### Métricas
```bash
GET /api/metrics
```

### Health Detallado
```bash
GET /api/health/detailed
```

## Troubleshooting

### La ingesta no inicia

1. Verificar logs:
   ```bash
   tail -f logs/app.log
   ```

2. Verificar conexión a base de datos:
   ```bash
   psql $DATABASE_URL -c "SELECT 1;"
   ```

3. Verificar variables de entorno:
   ```bash
   echo $INGESTION_MODE
   echo $TRADING_PAIRS
   ```

### No hay datos disponibles

1. Verificar ingesta:
   ```bash
   curl http://localhost:8000/api/chart/status
   ```

2. Verificar base de datos:
   ```bash
   psql $DATABASE_URL -c "SELECT COUNT(*) FROM ohlcv_candles;"
   ```

3. Reiniciar ingesta:
   ```bash
   # El backend reiniciará automáticamente, o:
   # Reiniciar el proceso del backend
   ```

### Errores de migración

1. Verificar que PostgreSQL está corriendo
2. Verificar permisos de usuario
3. Ejecutar migraciones manualmente:
   ```bash
   python backend/db/init_db.py
   ```

## Migración desde CSV

Si tienes datos históricos en CSV, puedes migrarlos:

```bash
python backend/scripts/migrate_csv_to_db.py
```

Este script:
- Busca archivos CSV en `data/ohlcv/`
- Migra datos a base de datos
- Mantiene integridad de timestamps

## Producción

### Checklist Pre-Producción

- [ ] Variables de entorno configuradas
- [ ] Base de datos inicializada
- [ ] Migraciones ejecutadas
- [ ] Ingesta funcionando
- [ ] Health checks pasando
- [ ] Logs configurados
- [ ] Backups configurados
- [ ] Monitoreo activo
- [ ] Alertas configuradas

### Recomendaciones

1. **Base de Datos**
   - Usar TimescaleDB para mejor performance
   - Configurar backups automatizados
   - Monitorear espacio en disco

2. **Ingesta**
   - Usar WebSocket mode (más eficiente)
   - Monitorear latencia de datos
   - Configurar alertas si ingesta falla

3. **Escalabilidad**
   - Usar múltiples workers (Gunicorn)
   - Considerar Redis para rate limiting
   - Load balancer para alta disponibilidad

4. **Seguridad**
   - TLS/HTTPS obligatorio
   - Secrets en secret manager
   - Rate limiting activo
   - Logs de auditoría

## Referencias

- [Architecture Documentation](./architecture/realtime_ingestion.md)
- [Operations Manual](./operations.md)
- [Security Checklist](./compliance/security-checklist.md)



