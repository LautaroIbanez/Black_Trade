# Setup de Observabilidad y Monitoreo

## Resumen

Este documento describe cómo configurar el sistema completo de observabilidad, incluyendo OpenTelemetry, métricas, alertas y dashboards.

## Componentes

### 1. OpenTelemetry

#### Instalación
```bash
pip install opentelemetry-api opentelemetry-sdk
pip install opentelemetry-instrumentation-fastapi
pip install opentelemetry-instrumentation-requests
pip install opentelemetry-instrumentation-sqlalchemy
pip install opentelemetry-exporter-otlp-proto-grpc
```

#### Configuración
```bash
# Variables de entorno
export OTLP_ENDPOINT=http://localhost:4317
export ENABLE_TRACING=true
export ENABLE_METRICS=true
export SERVICE_VERSION=1.0.0
```

#### Inicialización
El sistema se inicializa automáticamente en `backend/app.py`:
```python
from backend.observability.telemetry import init_telemetry

telemetry_manager = init_telemetry(
    service_name="black-trade",
    otlp_endpoint=os.getenv("OTLP_ENDPOINT"),
    enable_tracing=True,
    enable_metrics=True,
)
```

### 2. Métricas

El sistema recopila métricas automáticamente mediante middleware. Las métricas incluyen:
- Latencia de API (P50, P95, P99)
- Throughput (requests/s, orders/min)
- Error rates
- Recursos del sistema (CPU, memoria)
- Métricas de trading (P&L, drawdown, etc.)

**Endpoint de métricas**:
```bash
GET /api/metrics
```

### 3. Alertas

#### Configuración de Slack
```bash
export SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

#### Configuración de PagerDuty
```bash
export PAGERDUTY_INTEGRATION_KEY=your-integration-key
```

#### Configuración de Email
```bash
export SMTP_HOST=smtp.gmail.com
export SMTP_PORT=587
export SMTP_USERNAME=your-email@gmail.com
export SMTP_PASSWORD=your-app-password
export SMTP_FROM=alerts@blacktrade.com
export SMTP_TO_EMAILS=team@blacktrade.com
```

#### Inicialización de Alertas
```python
from backend.observability.alerts import ObservabilityAlertManager

alert_manager = ObservabilityAlertManager(
    slack_webhook=os.getenv("SLACK_WEBHOOK_URL"),
    pagerduty_integration_key=os.getenv("PAGERDUTY_INTEGRATION_KEY"),
)
```

### 4. Autenticación y Autorización

El sistema incluye un sistema de roles y permisos básico:

**Roles disponibles**:
- `viewer`: Solo lectura
- `trader`: Puede crear órdenes
- `risk_manager`: Puede gestionar límites de riesgo
- `admin`: Acceso completo

**Uso en endpoints**:
```python
from backend.auth.permissions import get_auth_service, Permission

@app.get("/api/risk/limits")
async def get_limits(
    user: User = Depends(get_auth_service().require_permission(Permission.READ_RISK_METRICS))
):
    ...
```

**Crear usuario**:
```python
from backend.auth.permissions import init_auth_service, Role

auth_service = init_auth_service()
token, user = auth_service.create_user("trader1", Role.TRADER)
```

### 5. Grafana Setup

#### Instalación de Grafana
```bash
# Docker
docker run -d -p 3000:3000 grafana/grafana

# O instalación nativa
# Ver https://grafana.com/docs/grafana/latest/installation/
```

#### Configurar Data Source

1. Abrir Grafana: http://localhost:3000
2. Ir a Configuration > Data Sources
3. Añadir Prometheus (si usas Prometheus) o direct API
4. Configurar endpoint

#### Importar Dashboards

Los dashboards se pueden crear manualmente o importar desde JSON. Ver [Dashboards Runbook](./runbooks/dashboards.md) para detalles.

### 6. Metabase Setup

#### Instalación de Metabase
```bash
# Docker
docker run -d -p 3000:3000 \
  -e "MB_DB_TYPE=postgres" \
  -e "MB_DB_DBNAME=metabase" \
  -e "MB_DB_PORT=5432" \
  -e "MB_DB_USER=metabase" \
  -e "MB_DB_PASS=password" \
  metabase/metabase
```

#### Configurar Conexión a Base de Datos

1. Abrir Metabase: http://localhost:3000
2. Configurar conexión a PostgreSQL
3. Conectar a base de datos `black_trade`

#### Crear Reportes

Ver [Dashboards Runbook](./runbooks/dashboards.md) para ejemplos de reportes.

## Verificación

### 1. Verificar Telemetría
```bash
# Health check
curl http://localhost:8000/api/health

# Métricas
curl http://localhost:8000/api/metrics
```

### 2. Verificar Alertas
```python
from backend.observability.alerts import ObservabilityAlertManager
from backend.observability.metrics import get_metrics_collector

alert_manager = ObservabilityAlertManager()
metrics_collector = get_metrics_collector()

# Simular alerta
metrics = metrics_collector.get_metrics()
metrics.api_latency_p95 = 1500  # Trigger alert
alerts = alert_manager.check_metrics(metrics)
```

### 3. Verificar Autenticación
```bash
# Sin token (debe fallar)
curl http://localhost:8000/api/risk/status

# Con token
curl http://localhost:8000/api/risk/status \
  -H "Authorization: Bearer token_user_0"
```

## Troubleshooting

### OpenTelemetry no envía datos
- Verificar que `OTLP_ENDPOINT` esté correcto
- Verificar que el collector OTLP esté corriendo
- Revisar logs para errores de conexión

### Alertas no se envían
- Verificar configuración de webhooks/keys
- Revisar logs del sistema
- Verificar que thresholds estén configurados

### Métricas no se actualizan
- Verificar que middleware esté activo
- Revisar que métricas se estén registrando
- Verificar conectividad con sistema de métricas

## Referencias

- [Runbook: Incident Response](./runbooks/incident_response.md)
- [Runbook: Alertas](./runbooks/alerts.md)
- [Runbook: Dashboards](./runbooks/dashboards.md)
- [Operations Manual](./operations.md)

