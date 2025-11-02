# UI Guidelines y Patrones de Interacción

## Resumen

Este documento define las pautas de diseño y patrones de interacción para la interfaz de Black Trade, enfocada en guiar al operador con contexto, priorización y control en tiempo real.

## Principios de Diseño

### 1. Orientado a Acción
- **Principio**: Cada pantalla debe guiar al usuario hacia acciones concretas
- **Aplicación**: Botones claros, CTAs prominentes, flujos lineales
- **Ejemplo**: Dashboard principal muestra oportunidades priorizadas con botón "Ejecutar" visible

### 2. Contexto en Tiempo Real
- **Principio**: Toda la información debe estar actualizada y contextual
- **Aplicación**: Actualizaciones automáticas, indicadores de estado, timestamps
- **Ejemplo**: Estado de órdenes actualizado automáticamente, alertas en tiempo real

### 3. Priorización Visual
- **Principio**: La información más importante debe destacarse
- **Aplicación**: Jerarquía visual clara, colores semafóricos, ordenamiento por relevancia
- **Ejemplo**: Alertas críticas en rojo, oportunidades con mejor R:R destacadas

### 4. Control Transparente
- **Principio**: El usuario debe entender y controlar el sistema
- **Aplicación**: Confirmaciones para acciones críticas, estado visible, logs de auditoría
- **Ejemplo**: Confirmar antes de pausar estrategias, mostrar razón de bloqueos

## User Journeys

### Journey 1: Trading Diario Matutino

**Objetivo**: Revisar estado del sistema y prepararse para el día de trading

**Pasos**:
1. Login → Dashboard principal
2. Revisar alertas del día (si las hay)
3. Verificar estado de riesgo (drawdown, exposición)
4. Revisar posiciones abiertas
5. Activar estrategias para el día
6. Establecer límites de riesgo si necesario

**Componentes clave**:
- Alert Banner (top)
- Risk Overview Card
- Open Positions List
- Strategy Toggle Panel

### Journey 2: Ejecutar Oportunidad

**Objetivo**: Identificar y ejecutar una oportunidad de trading

**Pasos**:
1. Ver oportunidad priorizada en dashboard
2. Revisar detalles (confianza, R:R, estrategias)
3. Confirmar entrada, SL y TP
4. Ejecutar orden
5. Monitorear estado de ejecución
6. Ver confirmación de fill

**Componentes clave**:
- Opportunity Card
- Order Confirmation Modal
- Execution Status Tracker
- Success Notification

### Journey 3: Gestión de Riesgo

**Objetivo**: Ajustar límites de riesgo y responder a alertas

**Pasos**:
1. Recibir alerta de riesgo
2. Revisar métricas detalladas
3. Evaluar situación
4. Ajustar límites o pausar estrategias
5. Confirmar cambios
6. Monitorear normalización

**Componentes clave**:
- Alert Notification (modal/toast)
- Risk Metrics Detail Panel
- Risk Limits Editor
- Strategy Controls

### Journey 4: Monitoreo Continuo

**Objetivo**: Supervisar sistema durante trading activo

**Pasos**:
1. Dashboard en segundo plano/visible
2. Recibir notificaciones push de eventos importantes
3. Revisar estado cuando hay notificación
4. Tomar acción si es necesario
5. Continuar monitoreo

**Componentes clave**:
- Live Dashboard
- Push Notifications
- Status Indicators
- Quick Actions Panel

## Componentes Clave

### 1. Dashboard Principal

**Propósito**: Vista centralizada del estado del sistema y oportunidades

**Secciones**:
- **Header**: Alertas críticas, estado general
- **Oportunidades Priorizadas**: Lista de señales ordenadas por R:R
- **Estado de Ejecución**: Órdenes activas y recientes
- **Riesgo**: Métricas de riesgo en tiempo real
- **Estrategias**: Estado y controles de estrategias activas

**Estados**:
- Normal: Todo operativo
- Warning: Alertas no críticas
- Critical: Requiere atención inmediata
- Paused: Trading pausado

### 2. Opportunity Card

**Propósito**: Mostrar oportunidad de trading con contexto completo

**Información mostrada**:
- Símbolo y precio actual
- Señal (BUY/SELL) con confianza
- Entry range, Stop Loss, Take Profit
- Risk:Reward ratio
- Estrategias que apoyan
- Botón de acción (Ejecutar/Revisar)

**Estados**:
- Available: Lista para ejecutar
- Executing: Orden en proceso
- Filled: Ejecutada
- Expired: Oportunidad expirada

### 3. Execution Tracker

**Propósito**: Seguir estado de órdenes en tiempo real

**Información mostrada**:
- Estado actual (Pending/Submitting/Filled/Rejected)
- Progreso visual
- Detalles de fill (precio, cantidad, tiempo)
- Acciones disponibles (Cancelar si pendiente)

**Actualización**: WebSocket en tiempo real

### 4. Risk Overview

**Propósito**: Vista rápida de métricas de riesgo críticas

**Métricas mostradas**:
- Drawdown actual (con límite)
- Exposición total
- Daily P&L
- VaR

**Indicadores visuales**:
- Color semáforo (verde/amarillo/rojo)
- Barras de progreso para límites
- Alertas si cerca de límites

### 5. Strategy Controls

**Propósito**: Activar/desactivar y configurar estrategias

**Controles**:
- Toggle on/off por estrategia
- Indicador de estado (activa/pausada)
- Métricas de performance
- Botón para ajustar parámetros

**Confirmación**: Modal de confirmación para acciones críticas

### 6. Alert System

**Propósito**: Notificar eventos importantes

**Tipos de alertas**:
- **Toast notifications**: Para eventos informativos
- **Modal alerts**: Para acciones requeridas
- **Banner alerts**: Para alertas persistentes

**Prioridades**:
- Critical (rojo): Requiere acción inmediata
- Warning (amarillo): Requiere atención
- Info (azul): Informativo

## Patrones de Interacción

### 1. Confirmación de Acciones Críticas

**Cuándo usar**: Para acciones que pueden afectar trading o riesgo

**Implementación**:
- Modal de confirmación con:
  - Descripción clara de la acción
  - Consecuencias potenciales
  - Botones "Cancelar" y "Confirmar"
  - Checkbox para "No volver a preguntar" (para admins)

**Ejemplos**:
- Pausar estrategia
- Ajustar límites de riesgo
- Cancelar orden grande
- Ejecutar orden manual

### 2. Actualización en Tiempo Real

**Cuándo usar**: Para información que cambia frecuentemente

**Implementación**:
- WebSocket para datos críticos (órdenes, riesgo)
- Polling para datos menos críticos (métricas)
- Indicador de "última actualización"
- Transiciones suaves para cambios

**Ejemplos**:
- Estado de órdenes
- Métricas de riesgo
- Oportunidades disponibles
- Posiciones abiertas

### 3. Feedback Inmediato

**Cuándo usar**: Para todas las acciones del usuario

**Implementación**:
- Loading states en botones
- Mensajes de éxito/error
- Confirmaciones visuales
- Indicadores de progreso

**Ejemplos**:
- "Ejecutando orden..." → "Orden ejecutada"
- "Guardando cambios..." → "Cambios guardados"
- Spinner durante requests

### 4. Priorización Visual

**Cuándo usar**: Para destacar información importante

**Implementación**:
- Tamaño de fuente
- Colores (semáforo)
- Posición en pantalla
- Animaciones sutiles (pulse para alertas)

**Ejemplos**:
- Oportunidades ordenadas por R:R
- Alertas críticas arriba
- Métricas de riesgo destacadas

### 5. Contexto Progresivo

**Cuándo usar**: Para información detallada sin saturar

**Implementación**:
- Vista resumida por defecto
- Expansión al click/hover
- Tooltips para información adicional
- Modals para detalles completos

**Ejemplos**:
- Oportunidad card → Modal de detalles
- Risk metric → Detalle expandido
- Strategy → Configuración

## Estados de UI

### Estado Normal
- Todo operativo
- Colores neutros/verdes
- Acciones disponibles
- Sin alertas críticas

### Estado Warning
- Alertas no críticas
- Colores amarillos
- Acciones con advertencias
- Banner de alerta visible

### Estado Critical
- Requiere atención
- Colores rojos
- Acciones limitadas (solo críticas)
- Modal de alerta bloqueante

### Estado Paused
- Trading pausado
- Colores grises
- Solo lectura para la mayoría
- Banner de pausa visible

## Responsive Design

### Desktop (1920x1080+)
- Dashboard completo con todas las secciones visibles
- Sidebar para navegación
- Múltiples columnas

### Tablet (768px - 1920px)
- Dashboard con scroll vertical
- Sidebar colapsable
- Cards apiladas

### Mobile (< 768px)
- Vista simplificada
- Navegación por tabs
- Focus en información crítica

## Accesibilidad

### Contraste
- Ratio mínimo 4.5:1 para texto
- Indicadores de color + texto/símbolos

### Navegación por Teclado
- Tab order lógico
- Atajos de teclado para acciones comunes
- Focus visible

### Screen Readers
- Labels descriptivos
- ARIA attributes donde necesario
- Mensajes de estado anunciados

## Referencias

- [Material Design Guidelines](https://material.io/design)
- [Ant Design Patterns](https://ant.design/docs/spec/introduce)
- [Trading UI Best Practices](./trading-ui-best-practices.md)

