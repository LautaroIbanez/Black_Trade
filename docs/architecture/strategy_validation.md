# Arquitectura de Validación Continua de Estrategias

## Resumen

Este documento describe el sistema de validación continua que asegura que las estrategias no dependan de parámetros estáticos, cuentan con validación constante, y mitigan el riesgo de sobreajuste y degradación silenciosa.

## Componentes Principales

### 1. Configuración Dinámica de Estrategias

Las estrategias deben ser completamente parametrizables:
- **Parámetros técnicos**: Ventanas de indicadores, umbrales de señales
- **Gestión de riesgo**: Stop loss, take profit, position sizing
- **Filtros**: Volumen, volatilidad, condiciones de mercado

### 2. Pipeline Walk-Forward

#### 2.1 Separación Temporal
- **In-Sample (Training)**: Datos para optimización
- **Out-of-Sample (Validation)**: Datos para validación
- **Rolling Window**: Ventana móvil para validación continua

#### 2.2 Optimización
- **Grid Search**: Búsqueda exhaustiva en espacio de parámetros
- **Bayesian Optimization**: Optimización probabilística (futuro)
- **Walk-Forward Analysis**: Validación en múltiples períodos

### 3. Métricas Robustas

#### 3.1 Métricas de Retorno
- **Total Return %**: Retorno total del período
- **Annualized Return**: Retorno anualizado
- **Compounded Annual Growth Rate (CAGR)**: Tasa de crecimiento anual compuesta

#### 3.2 Métricas de Riesgo
- **Maximum Drawdown**: Pérdida máxima desde pico
- **Calmar Ratio**: Return / Max Drawdown (anualizado)
- **Sharpe Ratio**: (Return - Risk Free) / Volatility
- **Sortino Ratio**: Similar a Sharpe pero solo penaliza downside volatility

#### 3.3 Métricas de Trading
- **Win Rate**: Porcentaje de trades ganadores
- **Profit Factor**: Gross Profit / Gross Loss
- **Expectancy**: Valor esperado por trade
- **Average Win/Loss Ratio**: Ratio promedio de ganancias vs pérdidas

### 4. Evaluación Automática

#### 4.1 Datasets Sintéticos
- Generación de series temporales sintéticas con características controladas
- Testing bajo diferentes regímenes de mercado (trending, ranging, volatile)

#### 4.2 Datasets Históricos
- Múltiples períodos históricos
- Diferentes símbolos y timeframes
- Condiciones de mercado variadas

#### 4.3 Reportes Comparativos
- Comparación entre versiones de estrategias
- Tracking de degradación de performance
- Alertas automáticas

### 5. Persistencia de Resultados

#### 5.1 Resultados de Backtests
- Métricas completas por período
- Parámetros utilizados
- Trades generados (opcional, para análisis detallado)

#### 5.2 Parámetros Óptimos
- Histórico de optimizaciones
- Parámetros por período de validación
- Tracking de cambios en parámetros óptimos

## Flujo de Validación

```
1. Datos → Split (Train/Validation)
2. Optimización en Train → Parámetros óptimos
3. Validación en Validation → Métricas OOS
4. Walk-Forward: Slide window → Repeat
5. Agregación de resultados → Score final
6. Persistencia → Base de datos
7. Monitoreo → Alertas si degradación
```

## Criterios de Aceptación

### Mínimos Requeridos
- **Sharpe Ratio > 1.0**: Retorno ajustado por riesgo aceptable
- **Max Drawdown < 30%**: Riesgo controlado
- **Win Rate > 45%**: Más ganadores que perdedores
- **Profit Factor > 1.2**: Rentabilidad positiva
- **Min Trades > 20**: Suficiente actividad

### Validación Walk-Forward
- **Consistencia**: OOS performance similar a IS (ratio > 0.7)
- **Estabilidad**: Parámetros óptimos no cambian drásticamente entre períodos
- **Robustez**: Performance estable bajo diferentes condiciones

## Implementación

### Estructura de Directorios
```
backtest/
  engine/
    walk_forward.py      # Walk-forward engine
    optimizer.py         # Parameter optimization
    validator.py         # Validation logic
  evaluation/
    synthetic_data.py    # Synthetic dataset generation
    evaluator.py         # Automatic evaluation
    reporter.py          # Report generation
```

### Base de Datos
```sql
-- Resultados de backtests
CREATE TABLE backtest_results (
    id SERIAL PRIMARY KEY,
    strategy_name VARCHAR(100) NOT NULL,
    dataset_name VARCHAR(100),
    period_start TIMESTAMP,
    period_end TIMESTAMP,
    split_type VARCHAR(20),  -- 'is' or 'oos'
    parameters JSONB,
    metrics JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Parámetros óptimos
CREATE TABLE optimal_parameters (
    id SERIAL PRIMARY KEY,
    strategy_name VARCHAR(100) NOT NULL,
    dataset_name VARCHAR(100),
    validation_period_start TIMESTAMP,
    validation_period_end TIMESTAMP,
    parameters JSONB,
    validation_metrics JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
```

## Referencias
- [Walk-Forward Analysis](https://en.wikipedia.org/wiki/Walk_forward_optimization)
- [Backtesting Metrics](https://www.investopedia.com/articles/trading/08/backtesting-trading-strategies.asp)

