# Arquitectura de Gestión de Riesgo con Capital Real

## Resumen

Este documento describe el sistema de gestión de riesgo que se conecta a cuentas reales o simuladas, actualiza capital, drawdowns y límites en tiempo real, y proporciona sizing dinámico basado en capital disponible.

## Componentes Principales

### 1. Adaptadores de Exchange

#### 1.1 Interfaz Base
- **Ubicación**: `backend/integrations/base.py`
- **Responsabilidad**: Definir interfaz común para todos los exchanges
- **Métodos**:
  - `get_balance() -> Dict`: Obtener balance de cuenta
  - `get_positions() -> List[Dict]`: Obtener posiciones abiertas
  - `get_fills() -> List[Dict]`: Obtener fills/trades recientes
  - `get_account_status() -> Dict`: Estado general de cuenta

#### 1.2 Binance Adapter
- **Ubicación**: `backend/integrations/binance_adapter.py`
- **Características**:
  - REST API para balances y posiciones
  - WebSocket para actualizaciones en tiempo real
  - Soporte para spot y futures (futuro)
  - Manejo de rate limits y errores

#### 1.3 Simulated Adapter
- **Ubicación**: `backend/integrations/simulated_adapter.py`
- **Características**:
  - Simula cuenta para backtesting/papel
  - Mantiene estado de capital y posiciones
  - Registra todas las operaciones
  - Útil para pruebas sin riesgo

### 2. Motor de Risk Management

#### 2.1 Risk Engine
- **Ubicación**: `backend/risk/engine.py`
- **Responsabilidades**:
  - Calcular exposición total del portafolio
  - Calcular Value at Risk (VaR)
  - Tracking de drawdown en tiempo real
  - Cálculo de position sizing dinámico
  - Verificación de límites de riesgo

#### 2.2 Cálculo de Exposición
```python
Exposición Total = Sum(Posición_i × Precio_i × Leverage_i)
Exposición % = (Exposición Total / Capital Total) × 100
```

#### 2.3 Value at Risk (VaR)
- **Método**: Historical Simulation
- **Confianza**: 95% y 99%
- **Horizonte**: 1 día y 1 semana
- **Cálculo**: Basado en volatilidad histórica y correlaciones

#### 2.4 Drawdown Tracking
- **Current Drawdown**: Desde último pico de equity
- **Maximum Drawdown**: Máximo histórico
- **Drawdown Duration**: Tiempo desde último pico
- **Recovery Period**: Tiempo para recuperar pico anterior

#### 2.5 Position Sizing Dinámico
- **Kelly Criterion**: Para sizing óptimo teórico
- **Fixed Fractional**: Porcentaje fijo de capital
- **Volatility-based**: Ajustado por volatilidad del activo
- **Risk-based**: Basado en stop loss y riesgo máximo

### 3. Sistema de Alertas

#### 3.1 Alert Manager
- **Ubicación**: `backend/risk/alerts.py`
- **Canales**:
  - Email (SMTP)
  - Slack (Webhooks)
  - WebSocket (tiempo real a frontend)
  - Logging estructurado

#### 3.2 Tipos de Alertas
- **Límite de Exposición**: Cuando exposición > umbral
- **Drawdown Crítico**: Cuando drawdown > límite
- **Violación de VaR**: Cuando pérdida potencial > VaR
- **Posición Grande**: Cuando posición > límite por activo
- **Límite de Pérdida Diaria**: Cuando pérdidas del día > límite

### 4. API y Dashboards

#### 4.1 Endpoints de Risk
- **GET /api/risk/status**: Estado actual de riesgo
- **GET /api/risk/exposure**: Exposición por activo/estrategia
- **GET /api/risk/var**: VaR actual y histórico
- **GET /api/risk/drawdown**: Drawdown actual y histórico
- **GET /api/risk/limits**: Límites configurados
- **POST /api/risk/limits**: Actualizar límites

#### 4.2 Métricas en Tiempo Real
- **Capital Total**: Capital disponible
- **Exposición Total**: Exposición actual
- **Unrealized PnL**: PnL no realizado
- **Drawdown Actual**: Drawdown desde último pico
- **VaR 1D/1W**: Value at Risk
- **Position Sizing Recomendado**: Tamaño de posición sugerido

### 5. Persistencia de Datos

#### 5.1 Modelos de Base de Datos
```sql
-- Balances históricos
CREATE TABLE account_balances (
    id SERIAL PRIMARY KEY,
    account_id VARCHAR(50) NOT NULL,
    asset VARCHAR(10) NOT NULL,
    free_balance DECIMAL(30, 8),
    locked_balance DECIMAL(30, 8),
    total_balance DECIMAL(30, 8),
    usd_value DECIMAL(30, 8),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Posiciones
CREATE TABLE positions (
    id SERIAL PRIMARY KEY,
    account_id VARCHAR(50) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL,  -- 'long' or 'short'
    size DECIMAL(30, 8) NOT NULL,
    entry_price DECIMAL(20, 8) NOT NULL,
    current_price DECIMAL(20, 8),
    unrealized_pnl DECIMAL(30, 8),
    strategy_name VARCHAR(100),
    entry_time TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Métricas de riesgo
CREATE TABLE risk_metrics (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    total_capital DECIMAL(30, 8),
    total_exposure DECIMAL(30, 8),
    exposure_pct DECIMAL(10, 4),
    var_1d_95 DECIMAL(30, 8),
    var_1d_99 DECIMAL(30, 8),
    var_1w_95 DECIMAL(30, 8),
    var_1w_99 DECIMAL(30, 8),
    current_drawdown_pct DECIMAL(10, 4),
    max_drawdown_pct DECIMAL(10, 4),
    unrealized_pnl DECIMAL(30, 8),
    daily_pnl DECIMAL(30, 8)
);
```

## Flujo de Operación

### Flujo Principal
```
1. Adapter → Obtiene balances/posiciones del exchange
2. Risk Engine → Calcula métricas de riesgo
3. Verificación de Límites → Compara con límites configurados
4. Alertas → Genera alertas si se violan límites
5. Position Sizing → Calcula tamaño recomendado para nuevas posiciones
6. Persistencia → Guarda métricas en BD
7. API → Expone métricas para frontend
```

### Actualización en Tiempo Real
- **WebSocket**: Para balances y posiciones
- **Polling**: Para métricas que no tienen WebSocket
- **Event-driven**: Cuando hay cambios significativos

## Configuración de Límites

### Límites por Defecto
```python
RISK_LIMITS = {
    'max_exposure_pct': 80.0,      # Máximo 80% de capital expuesto
    'max_position_pct': 25.0,      # Máximo 25% por posición
    'max_drawdown_pct': 20.0,      # Máximo 20% drawdown
    'daily_loss_limit_pct': 5.0,   # Máximo 5% pérdida diaria
    'var_limit_1d_95': 0.03,       # VaR 1D 95% no debe exceder 3% del capital
    'var_limit_1w_95': 0.10,       # VaR 1W 95% no debe exceder 10% del capital
}
```

### Límites por Estrategia
Cada estrategia puede tener sus propios límites:
```python
STRATEGY_LIMITS = {
    'EMA_RSI': {
        'max_exposure_pct': 30.0,
        'max_position_pct': 15.0,
    },
    'Momentum': {
        'max_exposure_pct': 20.0,
        'max_position_pct': 10.0,
    },
}
```

## Referencias
- [Value at Risk (VaR)](https://en.wikipedia.org/wiki/Value_at_risk)
- [Kelly Criterion](https://en.wikipedia.org/wiki/Kelly_criterion)
- [Position Sizing](https://www.investopedia.com/terms/p/positionsizing.asp)

