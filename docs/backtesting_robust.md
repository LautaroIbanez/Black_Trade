# Backtesting Robusto: Métricas %, Curva de Capital y Validación Fuera de Muestra

## Qué incluye
- Capital inicial y tamaño de posición configurable por backtest
- Métricas porcentuales: `total_return_pct`, `max_drawdown_pct`
- Curva de capital (`equity_curve`) y retornos por trade (`returns_pct`)
- Split train/test y análisis walk-forward
- Modelo de costes parametrizable (comisiones, slippage, spread fijo/ATR)

## Cómo usar

### Motor de backtesting
```python
from backtest.engine import BacktestEngine, CostModel
from strategies.ema_rsi_strategy import EMARSIStrategy
import pandas as pd

df = pd.read_csv('data/ohlcv/BTCUSDT_1h.csv')
engine = BacktestEngine(
    initial_capital=10000.0,
    position_size_pct=0.2,
    cost_model=CostModel(
        commission_pct=0.0002,
        slippage_pct=0.0001,
        spread_mode='atr',              # 'fixed' o 'atr'
        spread_atr_multiplier=0.25,     # multiplica ATR/price
    ),
)

strategy = EMARSIStrategy()
result = engine.run_backtest(strategy, df, '1h')
print(result['total_return_pct'], result['max_drawdown_pct'])
```

### Train/Test split
```python
split_result = engine.run_backtest_with_split(strategy, df, '1h', split=0.7)
print(split_result['in_sample']['total_return_pct'])
print(split_result['out_of_sample']['total_return_pct'])
```

### Walk-forward analysis
```python
wf = engine.run_walk_forward(strategy, df, '1h', train_window=500, test_window=100, step=100)
print(wf['summary'])
```

## Métricas añadidas en resultados
- `equity_curve`: lista de equity simulada por trade
- `returns_pct`: retorno porcentual por paso de equity
- `total_return_pct`: retorno total relativo a `initial_capital`
- `max_drawdown_pct`: drawdown máximo relativo de la curva de equity
- `initial_capital`, `position_size_pct`: parámetros usados

## Modelo de costes
- `commission_pct`: comisión por lado
- `slippage_pct`: deslizamiento fijo base
- `spread_mode`: `fixed` o `atr`
- `spread_atr_multiplier`: si `atr`, aplica coste extra proporcional a ATR/price en la fecha de entrada

Nota: si la estrategia ya incluye `net_pnl`, el motor lo toma como base y aplica costes extra de spread ATR durante la simulación de equity.

## CLI actualizada
```bash
python backend/scripts/backtest_all.py \
  --initial-capital 20000 \
  --position-size-pct 0.15 \
  --commission-pct 0.0004 \
  --slippage-pct 0.0002 \
  --spread-mode atr \
  --spread-atr-multiplier 0.2 \
  --split 0.7

# Walk-forward
python backend/scripts/backtest_all.py \
  --walk-forward --train-window 1000 --test-window 200
```

## Buenas prácticas de validación
- Usar datos representativos (tendencias y rangos)
- Validar OOS con split o walk-forward
- Incluir costes realistas (comisión, slippage, spread)
- Evitar sobreajuste; revisar estabilidad por ventanas






