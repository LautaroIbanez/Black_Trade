# Setup Guide: Gestión de Riesgo con Capital Real

Este documento describe cómo configurar y usar el sistema de gestión de riesgo que se conecta a cuentas reales o simuladas.

## Requisitos Previos

### Exchange Account (Para Producción)

1. **Binance Account**: Cuenta con API keys habilitadas
   - API Key con permisos de lectura
   - API Secret (mantener seguro)
   - **NO usar permisos de trading** en producción inicialmente

### Dependencias

```bash
pip install -r requirements.txt
```

## Configuración

### Variables de Entorno

```bash
# Exchange (Binance)
BINANCE_API_KEY=your_api_key
BINANCE_API_SECRET=your_api_secret
BINANCE_TESTNET=true  # Usar testnet para pruebas

# Alertas
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password
SMTP_FROM=your_email@gmail.com
SMTP_TO_EMAILS=alerts@example.com

SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL

# Risk Limits
MAX_EXPOSURE_PCT=80.0
MAX_POSITION_PCT=25.0
MAX_DRAWDOWN_PCT=20.0
DAILY_LOSS_LIMIT_PCT=5.0
```

### Inicialización de Base de Datos

```bash
# Ejecutar migración para tablas de risk metrics
python -m backend.db.migrations.003_risk_metrics upgrade
```

## Uso

### Modo Simulado (Paper Trading)

```python
from backend.integrations.simulated_adapter import SimulatedAdapter
from backend.risk.engine import RiskEngine, RiskLimits

# Crear adapter simulado
adapter = SimulatedAdapter(initial_capital=10000.0)

# Configurar límites
limits = RiskLimits(
    max_exposure_pct=80.0,
    max_position_pct=25.0,
    max_drawdown_pct=20.0,
)

# Crear risk engine
engine = RiskEngine(adapter, limits)

# Obtener métricas
metrics = engine.get_risk_metrics()
print(f"Capital: ${metrics.total_capital:,.2f}")
print(f"Exposición: {metrics.exposure_pct:.2f}%")
```

### Modo Real (Binance)

```python
from backend.integrations.binance_adapter import BinanceAdapter
from backend.risk.engine import RiskEngine, RiskLimits

# Crear adapter (usa variables de entorno)
adapter = BinanceAdapter(testnet=True)  # Usar testnet primero

# Crear risk engine
engine = RiskEngine(adapter)

# Obtener métricas en tiempo real
metrics = engine.get_risk_metrics()
```

### Monitoreo Continuo

```python
from backend.risk.monitor import RiskMonitor
from backend.risk.alerts import AlertManager
import asyncio

# Crear alert manager
alerts = AlertManager()

# Crear monitor
monitor = RiskMonitor(
    risk_engine=engine,
    alert_manager=alerts,
    check_interval=60,  # Verificar cada 60 segundos
)

# Iniciar monitoreo
async def main():
    await monitor.start()
    # Mantener ejecutándose...
    await asyncio.sleep(3600)  # Ejecutar por 1 hora
    await monitor.stop()

asyncio.run(main())
```

## API Endpoints

### GET /api/risk/status

Obtener estado actual de riesgo:

```bash
curl http://localhost:8000/api/risk/status
```

Respuesta:
```json
{
  "metrics": {
    "total_capital": 10000.0,
    "equity": 10250.0,
    "exposure_pct": 45.5,
    "current_drawdown_pct": 2.5,
    ...
  },
  "limit_checks": {
    "exposure": {"violated": false, ...},
    "drawdown": {"violated": false, ...},
    ...
  },
  "status": "healthy"
}
```

### POST /api/risk/position-size

Calcular tamaño de posición recomendado:

```bash
curl -X POST http://localhost:8000/api/risk/position-size \
  -H "Content-Type: application/json" \
  -d '{
    "entry_price": 50000.0,
    "stop_loss": 49000.0,
    "risk_amount": 100.0,
    "method": "risk_based"
  }'
```

### GET /api/risk/exposure

Obtener desglose de exposición:

```bash
curl http://localhost:8000/api/risk/exposure
```

## Límites de Riesgo

### Límites Globales

Configurados en `RiskLimits`:

- **max_exposure_pct**: Máximo % de capital expuesto (default: 80%)
- **max_position_pct**: Máximo % por posición (default: 25%)
- **max_drawdown_pct**: Máximo drawdown permitido (default: 20%)
- **daily_loss_limit_pct**: Límite de pérdida diaria (default: 5%)

### Límites por Estrategia

```python
strategy_limits = {
    'EMA_RSI': {
        'max_exposure_pct': 30.0,
        'max_position_pct': 15.0,
    },
    'Momentum': {
        'max_exposure_pct': 20.0,
        'max_position_pct': 10.0,
    },
}

engine = RiskEngine(adapter, strategy_limits=strategy_limits)
```

## Alertas

### Configuración de Email

1. Usar Gmail con App Password:
   - Generar App Password en Google Account
   - Usar como `SMTP_PASSWORD`

2. O usar otro SMTP:
   ```bash
   SMTP_HOST=smtp.mailgun.org
   SMTP_PORT=587
   ```

### Configuración de Slack

1. Crear Webhook en Slack:
   - Slack App → Incoming Webhooks
   - Copiar Webhook URL

2. Configurar:
   ```bash
   SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
   ```

### Tipos de Alertas

- **Limit Violations**: Cuando se viola cualquier límite
- **Critical Drawdown**: Drawdown > límite crítico
- **Daily Loss Limit**: Pérdida diaria > límite
- **VaR Violation**: VaR excede límites

## Position Sizing

### Métodos Disponibles

1. **risk_based** (default): Basado en riesgo máximo por trade
2. **fixed_fractional**: Porcentaje fijo de capital
3. **volatility**: Ajustado por volatilidad
4. **kelly**: Kelly Criterion (simplificado)

### Ejemplo

```python
sizing = engine.calculate_position_size(
    entry_price=50000.0,
    stop_loss=49000.0,
    risk_amount=100.0,  # Arriesgar $100
    strategy_name='EMA_RSI',
    method='risk_based',
)

print(f"Tamaño recomendado: {sizing['position_size']} BTC")
print(f"Valor posición: ${sizing['position_value']:,.2f}")
```

## Troubleshooting

### Error: "Binance API credentials required"

Verificar que `BINANCE_API_KEY` y `BINANCE_API_SECRET` estén configurados.

### Alertas no se envían

1. Verificar configuración de SMTP/Slack
2. Revisar logs para errores
3. Probar manualmente:
   ```python
   from backend.risk.alerts import AlertManager
   alerts = AlertManager()
   alerts.send_email_alert("Test", "Test message")
   ```

### VaR siempre es 0

VaR requiere historial de retornos. Esperar a que se acumule suficiente historial (mínimo 100 puntos).

## Próximos Pasos

1. **Integración con Trading**: Conectar risk engine con ejecución de órdenes
2. **Auto-Close**: Cerrar posiciones automáticamente cuando se violan límites
3. **Dashboard**: Visualización en tiempo real en frontend
4. **Backtesting**: Validar límites con datos históricos

## Referencias

- [Arquitectura de Risk Management](./architecture/risk_management.md)
- [Binance API Documentation](https://binance-docs.github.io/apidocs/spot/en/#account-information)

