# Guía: Cómo Ejecutar Backtests

Esta guía te llevará paso a paso para ejecutar backtests en el sistema Black Trade, desde la configuración básica hasta el análisis avanzado de resultados.

## 📋 Prerrequisitos

- Sistema Black Trade instalado y configurado
- Datos históricos sincronizados
- Estrategias habilitadas en el registro
- Conocimiento básico de métricas de trading

## 🚀 Inicio Rápido

### Método 1: A través del Frontend

1. **Abrir la aplicación**:
   ```
   http://localhost:5173
   ```

2. **Hacer clic en "Refresh"**:
   - Esto ejecutará backtests para todas las estrategias habilitadas
   - Los resultados aparecerán automáticamente en el dashboard

3. **Ver resultados**:
   - Gráfico interactivo con señales
   - Recomendación actual
   - Métricas de rendimiento

### Método 2: A través de la API

```bash
# Ejecutar backtest completo
curl -X POST http://localhost:8000/refresh

# Obtener recomendación actual
curl http://localhost:8000/recommendation
```

### Método 3: Programáticamente

```python
from backtest.engine import BacktestEngine
from strategies.ema_rsi_strategy import EMARSIStrategy
import pandas as pd

# Cargar datos
df = pd.read_csv('data/ohlcv/BTCUSDT_1h.csv')

# Crear estrategia
strategy = EMARSIStrategy()

# Ejecutar backtest
engine = BacktestEngine()
results = engine.run_single_backtest(strategy, df, '1h')

print(f"Win Rate: {results['win_rate']:.2%}")
print(f"Profit Factor: {results['profit_factor']:.2f}")
print(f"Max Drawdown: {results['max_drawdown']:.2%}")
```

## 🔧 Configuración Avanzada

### Configurar Parámetros de Estrategia

1. **Editar configuración**:
   ```json
   // backend/config/strategies.json
   {
     "EMA_RSI": {
       "enabled": true,
       "parameters": {
         "fast_period": 12,
         "slow_period": 26,
         "rsi_period": 14,
         "rsi_oversold": 30,
         "rsi_overbought": 70
       },
       "commission": 0.001,
       "slippage": 0.0005
     }
   }
   ```

2. **Recargar configuración**:
   ```bash
   curl -X POST http://localhost:8000/strategies/reload
   ```

### Configurar Período de Backtest

```python
# En backend/app.py, modificar el período
def refresh_data():
    # Cambiar days_back según necesidades
    download_results = sync_service.download_historical_data(
        symbol, timeframes, days_back=365  # 1 año de datos
    )
```

### Configurar Timeframes

```bash
# Variables de entorno
export TIMEFRAMES="1h,4h,1d,1w"
export TRADING_PAIRS="BTCUSDT"
```

## 📊 Análisis de Resultados

### Métricas Principales

#### 1. **Rendimiento**
- **Total PnL**: Ganancia/pérdida total
- **Net PnL**: PnL después de costos
- **Win Rate**: Porcentaje de trades ganadores
- **Profit Factor**: Ratio de ganancias/pérdidas

#### 2. **Riesgo**
- **Max Drawdown**: Máxima pérdida consecutiva
- **Sharpe Ratio**: Rendimiento ajustado por riesgo
- **Volatility**: Volatilidad de los retornos
- **VaR**: Value at Risk

#### 3. **Eficiencia**
- **Total Trades**: Número total de trades
- **Avg Trade Duration**: Duración promedio de trades
- **Trade Frequency**: Frecuencia de trading
- **Hit Rate**: Tasa de aciertos

### Interpretación de Resultados

#### ✅ **Buenos Resultados**
```
Win Rate: > 55%
Profit Factor: > 1.5
Max Drawdown: < 15%
Sharpe Ratio: > 1.0
```

#### ⚠️ **Resultados Aceptables**
```
Win Rate: 45-55%
Profit Factor: 1.2-1.5
Max Drawdown: 15-25%
Sharpe Ratio: 0.5-1.0
```

#### ❌ **Resultados Problemáticos**
```
Win Rate: < 45%
Profit Factor: < 1.2
Max Drawdown: > 25%
Sharpe Ratio: < 0.5
```

## 🔍 Análisis Detallado

### 1. **Análisis por Timeframe**

```python
# Comparar rendimiento por timeframe
timeframes = ['1h', '4h', '1d', '1w']
results_by_timeframe = {}

for tf in timeframes:
    df = pd.read_csv(f'data/ohlcv/BTCUSDT_{tf}.csv')
    results = engine.run_single_backtest(strategy, df, tf)
    results_by_timeframe[tf] = results

# Analizar diferencias
for tf, results in results_by_timeframe.items():
    print(f"{tf}: Win Rate {results['win_rate']:.2%}, "
          f"Profit Factor {results['profit_factor']:.2f}")
```

### 2. **Análisis de Sensibilidad**

```python
# Probar diferentes parámetros
fast_periods = [8, 12, 16, 20]
slow_periods = [20, 26, 32, 40]

best_performance = 0
best_params = None

for fast in fast_periods:
    for slow in slow_periods:
        if fast >= slow:
            continue
            
        strategy = EMARSIStrategy(fast_period=fast, slow_period=slow)
        results = engine.run_single_backtest(strategy, df, '1h')
        
        # Usar Sharpe Ratio como métrica de optimización
        if results['sharpe_ratio'] > best_performance:
            best_performance = results['sharpe_ratio']
            best_params = (fast, slow)

print(f"Mejores parámetros: Fast={best_params[0]}, Slow={best_params[1]}")
print(f"Mejor Sharpe Ratio: {best_performance:.2f}")
```

### 3. **Análisis de Drawdown**

```python
# Analizar períodos de drawdown
def analyze_drawdowns(trades):
    """Analizar períodos de drawdown en detalle."""
    cumulative_pnl = 0
    peak = 0
    drawdowns = []
    
    for trade in trades:
        cumulative_pnl += trade['pnl']
        
        if cumulative_pnl > peak:
            peak = cumulative_pnl
        
        current_drawdown = peak - cumulative_pnl
        drawdowns.append(current_drawdown)
    
    return {
        'max_drawdown': max(drawdowns),
        'avg_drawdown': sum(drawdowns) / len(drawdowns),
        'drawdown_periods': len([d for d in drawdowns if d > 0])
    }
```

## 🛠️ Herramientas de Análisis

### 1. **Script de Análisis Personalizado**

```python
# analysis_script.py
import pandas as pd
import matplotlib.pyplot as plt
from backtest.engine import BacktestEngine
from strategies.ema_rsi_strategy import EMARSIStrategy

def analyze_strategy_performance():
    """Análisis completo de rendimiento de estrategia."""
    
    # Cargar datos
    df = pd.read_csv('data/ohlcv/BTCUSDT_1h.csv')
    
    # Crear estrategia
    strategy = EMARSIStrategy()
    
    # Ejecutar backtest
    engine = BacktestEngine()
    results = engine.run_single_backtest(strategy, df, '1h')
    
    # Análisis detallado
    print("=== ANÁLISIS DE RENDIMIENTO ===")
    print(f"Período: {len(df)} velas")
    print(f"Total Trades: {results['total_trades']}")
    print(f"Win Rate: {results['win_rate']:.2%}")
    print(f"Profit Factor: {results['profit_factor']:.2f}")
    print(f"Max Drawdown: {results['max_drawdown']:.2%}")
    print(f"Sharpe Ratio: {results['sharpe_ratio']:.2f}")
    
    # Análisis de trades
    trades = strategy.generate_trades(df)
    if trades:
        winning_trades = [t for t in trades if t['pnl'] > 0]
        losing_trades = [t for t in trades if t['pnl'] < 0]
        
        print(f"\n=== ANÁLISIS DE TRADES ===")
        print(f"Trades Ganadores: {len(winning_trades)}")
        print(f"Trades Perdedores: {len(losing_trades)}")
        
        if winning_trades:
            avg_win = sum(t['pnl'] for t in winning_trades) / len(winning_trades)
            print(f"Ganancia Promedio: {avg_win:.2f}")
        
        if losing_trades:
            avg_loss = sum(t['pnl'] for t in losing_trades) / len(losing_trades)
            print(f"Pérdida Promedio: {avg_loss:.2f}")

if __name__ == "__main__":
    analyze_strategy_performance()
```

### 2. **Comparación de Estrategias**

```python
# compare_strategies.py
from strategies.ema_rsi_strategy import EMARSIStrategy
from strategies.momentum_strategy import MomentumStrategy
from strategies.breakout_strategy import BreakoutStrategy
from backtest.engine import BacktestEngine

def compare_strategies():
    """Comparar rendimiento de múltiples estrategias."""
    
    strategies = [
        EMARSIStrategy(),
        MomentumStrategy(),
        BreakoutStrategy()
    ]
    
    df = pd.read_csv('data/ohlcv/BTCUSDT_1h.csv')
    engine = BacktestEngine()
    
    results = {}
    
    for strategy in strategies:
        result = engine.run_single_backtest(strategy, df, '1h')
        results[strategy.name] = result
    
    # Crear tabla comparativa
    comparison_df = pd.DataFrame(results).T
    comparison_df = comparison_df[['win_rate', 'profit_factor', 'max_drawdown', 'sharpe_ratio']]
    
    print("=== COMPARACIÓN DE ESTRATEGIAS ===")
    print(comparison_df.round(3))
    
    # Encontrar mejor estrategia
    best_strategy = comparison_df['sharpe_ratio'].idxmax()
    print(f"\nMejor estrategia: {best_strategy}")
    print(f"Sharpe Ratio: {comparison_df.loc[best_strategy, 'sharpe_ratio']:.2f}")

if __name__ == "__main__":
    compare_strategies()
```

### 3. **Análisis de Robustez**

```python
# robustness_analysis.py
import numpy as np
from backtest.engine import BacktestEngine
from strategies.ema_rsi_strategy import EMARSIStrategy

def robustness_analysis():
    """Análisis de robustez con diferentes condiciones de mercado."""
    
    # Cargar datos
    df = pd.read_csv('data/ohlcv/BTCUSDT_1h.csv')
    
    # Dividir en períodos
    total_length = len(df)
    period_length = total_length // 4
    
    periods = [
        ('Q1', df.iloc[:period_length]),
        ('Q2', df.iloc[period_length:2*period_length]),
        ('Q3', df.iloc[2*period_length:3*period_length]),
        ('Q4', df.iloc[3*period_length:])
    ]
    
    strategy = EMARSIStrategy()
    engine = BacktestEngine()
    
    print("=== ANÁLISIS DE ROBUSTEZ ===")
    
    for period_name, period_df in periods:
        if len(period_df) < 100:  # Mínimo de datos
            continue
            
        results = engine.run_single_backtest(strategy, period_df, '1h')
        
        print(f"\n{period_name}:")
        print(f"  Win Rate: {results['win_rate']:.2%}")
        print(f"  Profit Factor: {results['profit_factor']:.2f}")
        print(f"  Max Drawdown: {results['max_drawdown']:.2%}")
        print(f"  Total Trades: {results['total_trades']}")

if __name__ == "__main__":
    robustness_analysis()
```

## 📈 Visualización de Resultados

### 1. **Gráfico de Equity Curve**

```python
import matplotlib.pyplot as plt

def plot_equity_curve(trades):
    """Crear gráfico de curva de equity."""
    
    cumulative_pnl = 0
    equity_curve = [0]
    
    for trade in trades:
        cumulative_pnl += trade['pnl']
        equity_curve.append(cumulative_pnl)
    
    plt.figure(figsize=(12, 6))
    plt.plot(equity_curve)
    plt.title('Equity Curve')
    plt.xlabel('Trade Number')
    plt.ylabel('Cumulative PnL')
    plt.grid(True)
    plt.show()
```

### 2. **Distribución de Retornos**

```python
def plot_returns_distribution(trades):
    """Crear histograma de distribución de retornos."""
    
    returns = [trade['pnl'] for trade in trades]
    
    plt.figure(figsize=(10, 6))
    plt.hist(returns, bins=30, alpha=0.7, edgecolor='black')
    plt.title('Distribución de Retornos por Trade')
    plt.xlabel('PnL por Trade')
    plt.ylabel('Frecuencia')
    plt.axvline(0, color='red', linestyle='--', alpha=0.7)
    plt.grid(True)
    plt.show()
```

### 3. **Análisis de Drawdown**

```python
def plot_drawdown_analysis(trades):
    """Crear gráfico de análisis de drawdown."""
    
    cumulative_pnl = 0
    peak = 0
    drawdowns = []
    
    for trade in trades:
        cumulative_pnl += trade['pnl']
        if cumulative_pnl > peak:
            peak = cumulative_pnl
        drawdowns.append(peak - cumulative_pnl)
    
    plt.figure(figsize=(12, 6))
    plt.fill_between(range(len(drawdowns)), drawdowns, alpha=0.3, color='red')
    plt.title('Análisis de Drawdown')
    plt.xlabel('Trade Number')
    plt.ylabel('Drawdown')
    plt.grid(True)
    plt.show()
```

## 🚨 Troubleshooting

### Problemas Comunes

#### 1. **No hay datos disponibles**
```bash
# Verificar sincronización
curl -X POST http://localhost:8000/refresh

# Verificar archivos de datos
ls -la data/ohlcv/
```

#### 2. **Estrategia no genera señales**
```python
# Verificar parámetros
strategy = EMARSIStrategy()
df = pd.read_csv('data/ohlcv/BTCUSDT_1h.csv')
signals_df = strategy.generate_signals(df)
print(f"Señales generadas: {signals_df['signal'].sum()}")
```

#### 3. **Rendimiento muy bajo**
```python
# Verificar costos
strategy = EMARSIStrategy(commission=0.001, slippage=0.0005)
results = engine.run_single_backtest(strategy, df, '1h')
print(f"Total costs: {results['total_costs']}")
print(f"Net PnL: {results['net_pnl']}")
```

#### 4. **Error de memoria**
```python
# Reducir período de datos
df = df.tail(1000)  # Últimas 1000 velas
results = engine.run_single_backtest(strategy, df, '1h')
```

### Debugging Avanzado

```python
# Habilitar logging detallado
import logging
logging.basicConfig(level=logging.DEBUG)

# Verificar cada paso
strategy = EMARSIStrategy()
df = pd.read_csv('data/ohlcv/BTCUSDT_1h.csv')

# 1. Verificar datos
print(f"Datos cargados: {len(df)} velas")
print(f"Rango de fechas: {df['timestamp'].min()} - {df['timestamp'].max()}")

# 2. Verificar señales
signals_df = strategy.generate_signals(df)
print(f"Señales generadas: {signals_df['signal'].sum()}")

# 3. Verificar trades
trades = strategy.generate_trades(signals_df)
print(f"Trades generados: {len(trades)}")

# 4. Verificar métricas
engine = BacktestEngine()
results = engine.run_single_backtest(strategy, df, '1h')
print(f"Resultados: {results}")
```

## 📚 Mejores Prácticas

### 1. **Validación de Datos**
- Verificar calidad y completitud de datos
- Usar datos de múltiples timeframes
- Validar rangos de fechas

### 2. **Configuración de Parámetros**
- Probar múltiples configuraciones
- Usar optimización de parámetros
- Validar robustez en diferentes períodos

### 3. **Análisis de Resultados**
- Usar múltiples métricas
- Comparar con benchmark
- Analizar drawdowns y volatilidad

### 4. **Monitoreo Continuo**
- Ejecutar backtests regularmente
- Monitorear degradación de rendimiento
- Ajustar parámetros según sea necesario

## 🔄 Automatización

### 1. **Script de Backtest Diario**

```bash
#!/bin/bash
# daily_backtest.sh

echo "Ejecutando backtest diario..."
curl -X POST http://localhost:8000/refresh

echo "Generando reporte..."
python generate_daily_report.py

echo "Enviando notificación..."
python send_notification.py
```

### 2. **Cron Job**

```bash
# Agregar a crontab
0 9 * * * /path/to/daily_backtest.sh
```

### 3. **Monitoreo Automático**

```python
# monitor_performance.py
def monitor_strategy_performance():
    """Monitorear rendimiento de estrategias."""
    
    # Ejecutar backtest
    results = run_backtest()
    
    # Verificar métricas críticas
    if results['win_rate'] < 0.45:
        send_alert("Win rate below threshold")
    
    if results['max_drawdown'] > 0.25:
        send_alert("Max drawdown exceeded")
    
    # Guardar resultados
    save_results(results)
```

¡Ahora tienes todas las herramientas necesarias para ejecutar backtests efectivos en Black Trade! 🚀
