# Runbook: Dashboards y KPIs

## Resumen

Este documento describe los dashboards de monitoreo y los KPIs clave del sistema.

## KPIs Principales

### Latencia
- **P50**: Latencia mediana de requests
- **P95**: 95% de requests bajo este tiempo
- **P99**: 99% de requests bajo este tiempo
- **Objetivo**: P95 < 500ms, P99 < 1s

### Throughput
- **Requests por segundo**: Tasa de requests al API
- **Órdenes por minuto**: Tasa de creación de órdenes
- **Objetivo**: Soportar picos de 100 req/s

### Errores
- **Error rate**: Porcentaje de requests con error
- **Order rejection rate**: Porcentaje de órdenes rechazadas
- **Objetivo**: < 1% error rate, < 5% order rejection

### Trading
- **Total P&L**: Profit and Loss acumulado
- **Daily P&L**: P&L del día actual
- **Win rate**: Porcentaje de trades ganadores
- **Sharpe ratio**: Ratio de Sharpe

### Riesgo
- **Current drawdown**: Drawdown actual
- **Max drawdown**: Drawdown máximo histórico
- **Exposure**: Exposición actual (%)
- **VaR 1d 95%**: Value at Risk 1 día 95% confianza

### Estrategias
- **Performance por estrategia**: P&L, win rate, trades
- **Generation time**: Tiempo de generación de recomendaciones
- **Order count**: Número de órdenes por estrategia

## Dashboards de Grafana

### Dashboard 1: Sistema General

**Paneles**:
1. Latency (P50, P95, P99) - Time series
2. Request rate - Time series
3. Error rate - Time series
4. CPU Usage - Time series
5. Memory Usage - Time series

**Query Prometheus** (ejemplo):
```promql
# Latency P95
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Request rate
rate(http_requests_total[5m])

# Error rate
rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m])
```

### Dashboard 2: Trading Performance

**Paneles**:
1. Total P&L - Single stat
2. Daily P&L - Time series
3. Win rate - Gauge
4. Sharpe ratio - Single stat
5. Drawdown - Time series
6. Exposure % - Gauge

**Fuente de datos**: API `/api/metrics` o base de datos directa

### Dashboard 3: Órdenes y Ejecución

**Paneles**:
1. Órdenes por estado - Pie chart
2. Order rejection rate - Time series
3. Orders per minute - Time series
4. Average execution time - Time series
5. Orders by strategy - Bar chart

### Dashboard 4: Estrategias

**Paneles**:
1. Performance por estrategia - Table
2. Win rate por estrategia - Bar chart
3. Trades por estrategia - Bar chart
4. Generation time por estrategia - Time series

## Dashboards de Metabase

### Reporte 1: Análisis de Performance Diario

**Métricas**:
- P&L diario
- Número de trades
- Win rate
- Drawdown máximo del día
- Órdenes ejecutadas vs rechazadas

**Filtros**:
- Fecha
- Estrategia
- Símbolo

### Reporte 2: Análisis de Riesgo

**Métricas**:
- Exposición actual
- VaR histórica
- Drawdown actual vs máximo
- Límites de riesgo vs actual

**Visualizaciones**:
- Línea de tiempo de exposición
- Gauge de drawdown
- Tabla de límites

### Reporte 3: Auditoría de Órdenes

**Datos**:
- Todas las órdenes con estados
- Tiempo de ejecución
- Usuario/estrategia que generó
- Fills y precios

**Filtros**:
- Fecha
- Estado
- Estrategia
- Usuario

## Acceso a Métricas

### API Endpoint
```bash
GET /api/metrics
```

Respuesta:
```json
{
  "timestamp": "2024-01-01T00:00:00",
  "latency": {
    "p50_ms": 45.2,
    "p95_ms": 120.5,
    "p99_ms": 250.0
  },
  "throughput": {
    "requests_per_second": 10.5,
    "orders_per_minute": 2.3
  },
  "errors": {
    "error_rate_percent": 0.5,
    "order_rejection_rate_percent": 3.2
  },
  "trading": {
    "total_pnl": 1500.0,
    "daily_pnl": 50.0,
    "win_rate": 0.65,
    "sharpe_ratio": 1.2
  },
  "risk": {
    "current_drawdown": 2.5,
    "max_drawdown": 5.0,
    "exposure_percent": 45.0,
    "var_1d_95": 0.02
  },
  "strategy_performance": {
    "EMA_RSI": {
      "generation_count": 100,
      "avg_generation_time_ms": 50.0,
      "order_count": 25,
      "pnl": 500.0
    }
  }
}
```

### Health Check
```bash
GET /api/health
GET /api/health/detailed
```

## Configuración de Alertas en Dashboards

### Grafana Alerts
1. Crear alerta en panel
2. Configurar threshold
3. Configurar notificación (Slack/PagerDuty)
4. Definir evaluación frequency

### Metabase Alerts
1. Configurar alerta en pregunta
2. Definir condición
3. Configurar email/Slack
4. Programar frecuencia de verificación

## Mejores Prácticas

1. **Dashboard en tiempo real**: Mantener dashboard visible durante trading hours
2. **Alertas visuales**: Usar colores para indicar estado (verde/amarillo/rojo)
3. **Retención de datos**: Mantener al menos 30 días de historial
4. **Revisión diaria**: Revisar dashboards al inicio del día
5. **Documentación**: Documentar cualquier anomalía observada

## Referencias

- [OpenTelemetry Setup](../OBSERVABILITY_SETUP.md)
- [Incident Response](./incident_response.md)

