# Runbook: Gestión de Alertas

## Resumen

Este runbook describe cómo interpretar y responder a las alertas generadas por el sistema de observabilidad.

## Tipos de Alertas

### Alertas de Sistema

#### HIGH_LATENCY
**Severidad**: WARNING / CRITICAL  
**Trigger**: P95 > 1s o P99 > 2s

**Acciones**:
1. Verificar carga del sistema
2. Revisar endpoints específicos que causan latencia
3. Escalar recursos si necesario
4. Ver runbook: [Alta Latencia](./incident_response.md#5-alta-latencia-del-sistema)

#### HIGH_ERROR_RATE
**Severidad**: CRITICAL  
**Trigger**: Error rate > 5%

**Acciones**:
1. Revisar logs de errores
2. Verificar estado de dependencias (DB, APIs externas)
3. Implementar circuit breakers si necesario
4. Ver runbook: [Errores Persistentes](./incident_response.md#3-errores-persistentes-de-ejecución-de-órdenes)

#### HIGH_CPU / HIGH_MEMORY
**Severidad**: WARNING  
**Trigger**: CPU > 80% o Memory > 2GB

**Acciones**:
1. Identificar procesos que consumen recursos
2. Revisar queries de base de datos
3. Optimizar código si necesario
4. Escalar recursos

### Alertas de Trading

#### ORDER_EXECUTION_FAILURE
**Severidad**: WARNING  
**Trigger**: Order rejection rate > 10%

**Acciones**:
1. Verificar conectividad con exchange
2. Revisar credenciales API
3. Verificar límites de rate limits
4. Revisar formato de órdenes
5. Ver runbook: [Errores de Ejecución](./incident_response.md#3-errores-persistentes-de-ejecución-de-órdenes)

#### RISK_LIMIT_VIOLATION
**Severidad**: CRITICAL  
**Trigger**: Violación de límites de riesgo

**Acciones**:
1. Verificar estado de riesgo actual
2. Pausar trading automático
3. Cancelar órdenes pendientes
4. Evaluar cierre de posiciones
5. Ver runbook: [Violación de Riesgo](./incident_response.md#2-violación-crítica-de-límites-de-riesgo)

#### STRATEGY_DEGRADATION
**Severidad**: WARNING  
**Trigger**: Performance de estrategia degrada significativamente

**Acciones**:
1. Verificar métricas de estrategia
2. Revisar recomendaciones recientes
3. Deshabilitar estrategia si necesario
4. Ver runbook: [Degradación de Estrategias](./incident_response.md#4-degradación-de-estrategias)

### Alertas de Infraestructura

#### SERVICE_DOWN
**Severidad**: CRITICAL  
**Trigger**: Servicio no responde

**Acciones**:
1. Verificar estado del servicio
2. Revisar logs
3. Reiniciar servicio si necesario
4. Ver runbook: [Sistema Inoperativo](./incident_response.md#1-sistema-completamente-inoperativo)

#### DATABASE_CONNECTION
**Severidad**: CRITICAL  
**Trigger**: No se puede conectar a base de datos

**Acciones**:
1. Verificar estado de base de datos
2. Verificar pool de conexiones
3. Revisar configuración de red
4. Escalar a DBA si necesario

## Configuración de Alertas

### Thresholds por Defecto

```python
{
    'latency_p95_ms': 1000.0,
    'latency_p99_ms': 2000.0,
    'error_rate_percent': 5.0,
    'cpu_usage_percent': 80.0,
    'memory_usage_mb': 2048.0,
    'order_rejection_rate_percent': 10.0,
}
```

### Ajustar Thresholds

Las alertas se pueden ajustar mediante variables de entorno o configuración:

```bash
export ALERT_LATENCY_P95_MS=1500
export ALERT_ERROR_RATE_PERCENT=3.0
```

## Canales de Notificación

### Slack
- **Canal**: `#alerts-trading`
- **Formato**: Rich messages con colores por severidad
- **Frecuencia**: Inmediata para CRITICAL, batch para WARNING

### PagerDuty
- **Solo para**: Alertas CRITICAL
- **Escalación**: Después de 15 minutos sin acknowledge

### Email
- **Destinatarios**: Equipo de trading, risk managers
- **Frecuencia**: Inmediata para CRITICAL

## Resolución de Alertas

### Auto-Resolución
Las alertas se auto-resuelven cuando la métrica vuelve al rango normal por más de 5 minutos.

### Resolución Manual
```python
from backend.observability.alerts import get_alert_manager, AlertType

alert_manager = get_alert_manager()
alert_manager.resolve_alert(AlertType.HIGH_LATENCY)
```

## Mejores Prácticas

1. **No ignorar alertas**: Todas las alertas deben ser investigadas
2. **Documentar respuesta**: Registrar acciones tomadas
3. **Ajustar thresholds**: Si alerta es ruidosa, ajustar threshold
4. **Revisar tendencias**: No solo valores puntuales, sino tendencias
5. **Automatizar respuestas**: Para alertas comunes, automatizar acciones

## Referencias

- [Incident Response Runbook](./incident_response.md)
- [Operations Manual](../operations.md)

