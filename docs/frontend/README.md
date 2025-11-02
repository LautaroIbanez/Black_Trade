# Frontend - Black Trade Trading Interface

## Resumen

Este documento describe la interfaz de usuario de Black Trade, diseñada para guiar al operador con contexto, priorización y control en tiempo real.

## Arquitectura

### Stack Tecnológico
- **React 18**: Framework UI
- **Vite**: Build tool y dev server
- **WebSocket**: Actualizaciones en tiempo real
- **CSS Modules**: Estilos componentizados

### Estructura de Componentes

```
frontend/src/
├── components/
│   ├── TradingDashboard.jsx    # Dashboard principal de trading
│   ├── OpportunityCard.jsx     # Card de oportunidad de trading
│   ├── RiskOverview.jsx        # Vista de métricas de riesgo
│   ├── ExecutionTracker.jsx    # Seguimiento de órdenes
│   ├── StrategyControls.jsx    # Controles de estrategias
│   ├── NotificationSystem.jsx  # Sistema de notificaciones
│   └── ...
├── services/
│   ├── api.js                  # Cliente API REST
│   └── websocket.js            # Cliente WebSocket
└── App.jsx                     # Componente raíz
```

## Componentes Principales

### TradingDashboard

Dashboard principal que combina todas las vistas importantes:

- **Oportunidades Priorizadas**: Lista de señales ordenadas por R:R
- **Riesgo Overview**: Métricas de riesgo en tiempo real
- **Execution Tracker**: Estado de órdenes activas
- **Strategy Controls**: Gestión de estrategias

**Características**:
- Auto-refresh cada 30 segundos
- Integración con WebSocket para actualizaciones en tiempo real
- Alertas visuales para condiciones críticas

### OpportunityCard

Muestra una oportunidad de trading con toda la información relevante:

- Símbolo y precio actual
- Señal (BUY/SELL) con nivel de confianza
- Entry range, Stop Loss, Take Profit
- Risk:Reward ratio
- Estrategias que apoyan la señal
- Botones de acción (Ejecutar/Ver Detalles)

**Estados**:
- `available`: Lista para ejecutar
- `executing`: Orden en proceso
- `filled`: Ejecutada
- `expired`: Expirada

### RiskOverview

Vista rápida de métricas de riesgo críticas:

- Drawdown actual con indicador visual
- Exposición total
- Daily P&L
- VaR

**Indicadores visuales**:
- Verde: Seguro (< 70% del límite)
- Amarillo: Advertencia (70-90%)
- Rojo: Crítico (> 90%)

### ExecutionTracker

Seguimiento en tiempo real del estado de órdenes:

- Lista de órdenes activas
- Estado actual (Pending/Submitted/Filled/etc.)
- Progreso de ejecución
- Acciones disponibles (Cancelar)

**Actualización**: WebSocket + polling cada 5 segundos

### StrategyControls

Panel para gestionar estrategias:

- Toggle on/off por estrategia
- Métricas de performance (P&L, Win Rate, Trades)
- Confirmación antes de cambios

### NotificationSystem

Sistema de notificaciones en tiempo real:

- Notificaciones toast para eventos importantes
- Tipos: Success, Error, Warning, Info
- Auto-dismiss después de 5 segundos
- Posicionamiento fijo (top-right)

## Flujos de Usuario

### Ejecutar Oportunidad

1. Usuario ve oportunidad en dashboard
2. Click en "Ejecutar"
3. Modal de confirmación muestra detalles
4. Usuario confirma cantidad y tipo de orden
5. Orden se envía al backend
6. Notificación confirma envío
7. ExecutionTracker muestra progreso
8. Notificación cuando orden se ejecuta

### Gestionar Riesgo

1. Alerta visual si métricas cerca de límites
2. Click en RiskOverview para detalles
3. Usuario puede ajustar límites (si tiene permisos)
4. Cambios se guardan y reflejan inmediatamente

### Pausar Estrategia

1. Usuario va a StrategyControls
2. Click en toggle para pausar estrategia
3. Confirmación modal
4. Estrategia se desactiva
5. Oportunidades de esa estrategia desaparecen

## Integración con Backend

### API REST

Todos los endpoints están en `services/api.js`:

- `getRiskStatus()`: Obtener métricas de riesgo
- `getMetrics()`: Obtener métricas del sistema
- `getExecutionOrders()`: Listar órdenes
- `createOrder()`: Crear nueva orden
- `cancelOrder()`: Cancelar orden
- `updateRiskLimits()`: Actualizar límites
- `toggleStrategy()`: Activar/desactivar estrategia

### WebSocket

El servicio WebSocket (`services/websocket.js`) se conecta automáticamente y escucha:

- `order_update`: Actualización de estado de orden
- `risk_update`: Actualización de métricas de riesgo
- `alert`: Alertas del sistema
- `order_filled`: Notificación de orden ejecutada

## Responsive Design

El dashboard se adapta a diferentes tamaños de pantalla:

- **Desktop (> 1024px)**: Grid de 2 columnas
- **Tablet (768-1024px)**: Grid de 1 columna, sidebar colapsable
- **Mobile (< 768px)**: Vista simplificada, navegación por tabs

## Próximos Pasos

### Mejoras Planificadas

1. **Autenticación**: Integrar login y gestión de tokens
2. **Historial**: Vista de órdenes históricas y performance
3. **Configuración**: Panel para ajustar preferencias
4. **Testing**: Tests unitarios y de integración
5. **Accesibilidad**: Mejorar soporte para screen readers

### Optimizaciones

1. **Lazy Loading**: Cargar componentes bajo demanda
2. **Caching**: Cachear datos que no cambian frecuentemente
3. **Debouncing**: Evitar requests excesivos
4. **Error Handling**: Mejor manejo de errores de red

## Desarrollo

### Setup

```bash
cd frontend
npm install
npm run dev
```

### Build

```bash
npm run build
```

### Testing

```bash
npm test
```

## Referencias

- [UI Guidelines](../ui-guidelines.md)
- [User Journeys](../user-journeys.md)
- [Backend API Documentation](../api/recommendation.md)

