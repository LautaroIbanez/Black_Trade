# Backtesting: Comparabilidad y Criterios de Ranking

Este documento describe los nuevos criterios para puntuar y rankear estrategias en el backtesting.

## Objetivos
- Evitar saturación por límites arbitrarios (`min(..., 1.0)`).
- Penalizar estrategias sin operaciones.
- Combinar retorno, drawdown relativo y número de operaciones antes de cualquier escala.

## Fórmula Compuesta (resumen)

Se calcula un puntaje compuesto:
- Retorno ajustado por riesgo: `total_return_pct - max_drawdown_pct` (más alto es mejor, drawdown resta)
- Estabilidad: `(profit_factor - 1.0) + (win_rate - 0.5)`
- Actividad: escala por nº de operaciones con rendimientos decrecientes (≈ completo a 50 trades)
- Expectancy: contribución moderada `expectancy / 100.0`

Puntaje final:
```text
score = [0.6*(ret - dd) + 0.25*stability + 0.15*(expectancy/100)] * (0.5 + 0.5*activity)
```

- `activity = min(total_trades / 50.0, 1.0)`
- Estrategias con `total_trades == 0` reciben `score = -1.0`
- No hay clamp universal a 1.0; el puntaje retiene comparabilidad entre estrategias.

## Ejemplo de Salida

```json
[
  {
    "strategy_name": "Momentum",
    "total_return_pct": 0.45,
    "max_drawdown_pct": 0.12,
    "profit_factor": 1.8,
    "win_rate": 0.62,
    "expectancy": 18.5,
    "total_trades": 34,
    "score": 0.305
  },
  {
    "strategy_name": "OrderFlow",
    "total_return_pct": 0.12,
    "max_drawdown_pct": 0.08,
    "profit_factor": 1.2,
    "win_rate": 0.55,
    "expectancy": 5.0,
    "total_trades": 12,
    "score": 0.068
  },
  {
    "strategy_name": "CryptoRotation",
    "total_return_pct": 0.10,
    "max_drawdown_pct": 0.05,
    "profit_factor": 1.1,
    "win_rate": 0.52,
    "expectancy": 3.0,
    "total_trades": 0,
    "score": -1.0
  }
]
```

## Implementación
- Lógica en `backtest/engine/analysis.py` (`compute_composite_score`).
- Integración de ranking en `backtest/engine.py` (`rank_strategies`).
- Pruebas en `backtest/tests/test_analysis.py`.
