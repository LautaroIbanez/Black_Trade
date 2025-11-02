# Manual de Operaciones - Trading Automatizado

## Resumen

Este documento describe los protocolos de operación para el sistema de trading automatizado, incluyendo monitoreo, intervención manual, y protocolos de emergencia.

## Arquitectura de Ejecución

### Flujo Automatizado

```
1. RecommendationService → Genera recomendación
2. Signal Orchestrator → Valida y convierte a Order
3. Execution Coordinator → Verifica reglas de coordinación
4. Execution Engine → Envía orden a exchange
5. Exchange → Ejecuta orden
6. Journal → Registra todo para auditoría
```

### Componentes Clave

- **Signal Orchestrator**: Convierte recomendaciones en órdenes
- **Execution Coordinator**: Coordina múltiples estrategias
- **Execution Engine**: Gestiona ciclo de vida de órdenes
- **Transaction Journal**: Registro completo para auditoría

## Monitoreo en Tiempo Real

### Métricas Clave a Monitorear

1. **Estado de Órdenes**:
   - Órdenes pendientes
   - Órdenes activas (submitted/partially_filled)
   - Tasa de llenado
   - Tiempo promedio de ejecución

2. **Exposición de Capital**:
   - Exposición total
   - Exposición por estrategia
   - Capital disponible

3. **Riesgo**:
   - Drawdown actual
   - VaR
   - Límites de riesgo
   - P&L diario

4. **Coordinación**:
   - Conflictos entre estrategias
   - Órdenes bloqueadas
   - Capital por estrategia

### Endpoints de Monitoreo

```bash
# Estado general
GET /api/execution/stats

# Órdenes pendientes
GET /api/execution/orders?status=pending

# Exposición por estrategia
GET /api/execution/coordination/strategy/{strategy_name}

# Journal completo
GET /api/execution/journal
```

## Intervención Manual

### Cuándo Intervenir

1. **Violación de Límites de Riesgo**: Cuando se violan límites críticos
2. **Errores Persistentes**: Cuando hay errores repetidos en ejecución
3. **Condiciones de Mercado**: Eventos de mercado inusuales
4. **Órdenes Bloqueadas**: Cuando coordinación bloquea órdenes legítimas

### Acciones Manuales Disponibles

#### 1. Cancelar Órdenes

```bash
POST /api/execution/orders/{order_id}/cancel
{
  "reason": "Manual intervention - market conditions"
}
```

#### 2. Revisar Journal

```bash
# Ver historial de un orden
GET /api/execution/journal/{order_id}

# Ver todas las entradas recientes
GET /api/execution/journal?limit=100
```

#### 3. Ajustar Límites de Riesgo

```bash
POST /api/risk/limits
{
  "max_exposure_pct": 70.0,
  "max_drawdown_pct": 15.0
}
```

#### 4. Pausar Estrategia

```python
# Deshabilitar estrategia temporalmente
from backend.services.strategy_registry import strategy_registry
strategy_registry.disable_strategy("EMA_RSI")
```

## Protocolos de Emergencia

### Procedimiento 1: Violación de Drawdown

**Cuándo**: Drawdown > límite máximo

**Pasos**:
1. ✅ **Automático**: Sistema envía alerta
2. ✅ **Automático**: Risk engine bloquea nuevas órdenes
3. 🔴 **Manual**: Revisar posiciones abiertas
4. 🔴 **Manual**: Decidir si cerrar posiciones
5. 🔴 **Manual**: Revisar y ajustar estrategias

**Acción Inmediata**:
```bash
# Ver estado de riesgo
curl http://localhost:8000/api/risk/status

# Cancelar todas las órdenes pendientes
# (implementar endpoint si necesario)

# Revisar posiciones
curl http://localhost:8000/api/risk/positions
```

### Procedimiento 2: Pérdida Diaria Excedida

**Cuándo**: Daily P&L < -límite diario

**Pasos**:
1. ✅ **Automático**: Sistema envía alerta crítica
2. ✅ **Automático**: Trading se detiene
3. 🔴 **Manual**: Revisar causas (errores, condiciones de mercado)
4. 🔴 **Manual**: Decidir si reanudar trading
5. 🔴 **Manual**: Ajustar límites si necesario

**Acción Inmediata**:
```bash
# Ver pérdidas del día
curl http://localhost:8000/api/risk/status | jq '.metrics.daily_pnl'

# Revisar órdenes del día
curl http://localhost:8000/api/execution/journal?entry_type=order_filled

# Revisar errores
curl http://localhost:8000/api/execution/journal?entry_type=error
```

### Procedimiento 3: Errores Persistentes de Ejecución

**Cuándo**: Múltiples órdenes rechazadas o errores de exchange

**Pasos**:
1. ✅ **Automático**: Sistema registra errores en journal
2. ✅ **Automático**: Reintentos con backoff
3. 🔴 **Manual**: Revisar conectividad con exchange
4. 🔴 **Manual**: Verificar credenciales API
5. 🔴 **Manual**: Revisar límites de rate limits
6. 🔴 **Manual**: Contactar exchange si problema persistente

**Acción Inmediata**:
```bash
# Ver órdenes rechazadas
curl http://localhost:8000/api/execution/orders?status=rejected

# Ver errores recientes
curl http://localhost:8000/api/execution/journal?entry_type=error

# Verificar conectividad
curl http://localhost:8000/api/risk/status
```

### Procedimiento 4: Condiciones de Mercado Anómalas

**Cuándo**: Volatilidad extrema, gaps grandes, falta de liquidez

**Pasos**:
1. 🔴 **Manual**: Detectar condiciones anómalas (monitoreo externo)
2. 🔴 **Manual**: Pausar trading automático
3. 🔴 **Manual**: Revisar posiciones existentes
4. 🔴 **Manual**: Considerar cierre de posiciones
5. 🔴 **Manual**: Esperar condiciones normales

**Acción Inmediata**:
```python
# Pausar todas las estrategias
from backend.services.strategy_registry import strategy_registry
for strategy_name in strategy_registry.get_enabled_strategies():
    strategy_registry.disable_strategy(strategy_name.name)

# Cancelar todas las órdenes pendientes
# (implementar bulk cancel si necesario)
```

## Reglas de Coordinación

### Prevención de Duplicidades

El sistema previene automáticamente:
- Órdenes BUY y SELL simultáneas para el mismo símbolo
- Múltiples órdenes del mismo lado muy cercanas en precio
- Sobreexposición por estrategia

### Límites por Estrategia

Configurar límites de capital por estrategia:

```python
max_capital_per_strategy = {
    'EMA_RSI': 30.0,  # 30% del capital total
    'Momentum': 20.0,
    'Breakout': 15.0,
}
```

### Máximo de Órdenes Simultáneas

Por defecto: 5 órdenes pendientes máximo.

Ajustar según capacidad de procesamiento y riesgo.

## Auditoría y Journal

### Acceso al Journal

El journal registra todas las acciones:
- Creación de órdenes
- Envíos y fills
- Cancelaciones
- Intervenciones manuales
- Errores

### Consultas Comunes

```bash
# Historial completo de un orden
GET /api/execution/journal/{order_id}

# Todas las intervenciones manuales
GET /api/execution/journal?entry_type=manual_intervention

# Errores del último día
GET /api/execution/journal?entry_type=error&limit=50

# Órdenes de una estrategia específica
# (requiere filtrado adicional en respuesta)
```

### Exportar Journal

```python
from backend.logging.journal import transaction_journal

# Exportar a JSON
transaction_journal.export_json('journal_export.json')
```

## Monitoreo Continuo

### Checklist Diario

- [ ] Revisar métricas de riesgo (exposición, drawdown)
- [ ] Verificar estado de órdenes pendientes
- [ ] Revisar journal para errores
- [ ] Confirmar reconciliación con exchange
- [ ] Verificar alertas recibidas

### Checklist Semanal

- [ ] Revisar performance de estrategias
- [ ] Analizar tasa de llenado de órdenes
- [ ] Revisar ajustes de límites necesarios
- [ ] Exportar journal para backup
- [ ] Revisar logs de errores

### Alertas Configuradas

- **Email**: Todas las violaciones de límites
- **Slack**: Alertas críticas (drawdown, pérdidas diarias)
- **WebSocket**: Actualizaciones en tiempo real al frontend

## Troubleshooting

### Problema: Órdenes no se ejecutan

1. Verificar estado de órdenes: `GET /api/execution/orders?status=pending`
2. Revisar coordinación: Verificar si están bloqueadas
3. Verificar límites de riesgo: `GET /api/risk/status`
4. Revisar journal para errores: `GET /api/execution/journal?entry_type=error`

### Problema: Órdenes rechazadas frecuentemente

1. Verificar tamaño de posición (puede ser muy pequeño/grande)
2. Verificar precios (pueden estar fuera de rango)
3. Verificar disponibilidad de capital
4. Revisar límites de exchange (min order size, etc.)

### Problema: Capital no se actualiza

1. Verificar conexión con exchange
2. Revisar sincronización de balances
3. Verificar que fills se están registrando correctamente
4. Reconciliar manualmente con exchange

## Referencias

- [Arquitectura de Ejecución](./architecture/execution.md)
- [Risk Management Setup](./RISK_MANAGEMENT_SETUP.md)
- [API Documentation](../backend/api/routes/execution.py)

