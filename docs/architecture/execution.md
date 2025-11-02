# Arquitectura de Orquestación y Ejecución Automatizada

## Resumen

Este documento describe el sistema de orquestación que convierte recomendaciones validadas en órdenes, las ejecuta con control de estado, y registra toda la actividad para auditoría.

## Componentes Principales

### 1. Orquestador de Señales

#### 1.1 Signal Orchestrator
- **Ubicación**: `recommendation/orchestrator.py`
- **Responsabilidad**: Convertir `RecommendationResult` en órdenes ejecutables
- **Funciones**:
  - Validar recomendaciones contra límites de riesgo
  - Calcular tamaño de posición basado en capital disponible
  - Formatear órdenes según exchange
  - Verificar duplicidades (evitar órdenes opuestas simultáneas)

### 2. Módulo de Ejecución

#### 2.1 Execution Engine
- **Ubicación**: `backend/execution/engine.py`
- **Estados de Órdenes**:
  - `PENDING`: Orden creada, esperando ejecución
  - `SUBMITTED`: Enviada al exchange
  - `PARTIALLY_FILLED`: Parcialmente ejecutada
  - `FILLED`: Completamente ejecutada
  - `CANCELLED`: Cancelada
  - `REJECTED`: Rechazada por exchange o validación

#### 2.2 Order Queue
- **Implementación**: Cola persistente (Redis/SQLite/PostgreSQL)
- **Características**:
  - Priorización de órdenes
  - Reintentos automáticos con backoff
  - Manejo de slippage y timeouts
  - Prevención de duplicados

#### 2.3 Execution Manager
- **Responsabilidades**:
  - Envío de órdenes a exchange
  - Tracking de estado en tiempo real
  - Manejo de fills parciales
  - Reintentos ante fallos
  - Reconciliación con exchange

### 3. Reglas de Coordinación

#### 3.1 Capital Allocation
- Límites globales de capital por estrategia
- Prevención de sobreexposición
- Distribución proporcional según confianza

#### 3.2 Signal Coordination
- Prevención de órdenes BUY/SELL simultáneas
- Cierre de posiciones opuestas antes de nueva entrada
- Gestión de múltiples estrategias activas

#### 3.3 Risk Checks
- Verificación de límites antes de ejecutar
- Validación de position sizing
- Confirmación de disponibilidad de capital

### 4. Journal Transaccional

#### 4.1 Transaction Journal
- **Ubicación**: `backend/logging/journal.py`
- **Registro**:
  - Todas las órdenes (creación, envío, fills)
  - Cambios de estado
  - Errores y excepciones
  - Reintentos
  - Modificaciones manuales

#### 4.2 Auditoría
- **API**: `GET /api/execution/journal`
- **Queries**:
  - Historial de órdenes
  - Estado actual
  - Reconciliación con exchange
  - Alertas y errores

## Flujo de Ejecución

### Flujo Principal
```
1. RecommendationService → Genera RecommendationResult
2. Signal Orchestrator → Valida y convierte a Order
3. Execution Engine → Añade a cola
4. Execution Manager → Envía al exchange
5. Exchange → Ejecuta orden
6. WebSocket/Callback → Actualiza estado
7. Journal → Registra todo
8. Risk Engine → Actualiza exposición
```

### Manejo de Errores
```
Error en envío → Reintento con backoff
Error persistente → Alerta y pausa
Rechazo de exchange → Log y notificación
Timeout → Cancelación y reintento
```

## Estados y Transiciones

```
PENDING → SUBMITTED → FILLED
PENDING → SUBMITTED → PARTIALLY_FILLED → FILLED
PENDING → REJECTED
SUBMITTED → CANCELLED
SUBMITTED → REJECTED
```

## Referencias
- [Order Lifecycle](https://en.wikipedia.org/wiki/Order_(exchange))

