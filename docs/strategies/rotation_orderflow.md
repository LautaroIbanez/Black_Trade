# CryptoRotation y OrderFlow: Datos y Resultados Iniciales

## Requerimientos de Datos
- CSVs OHLCV por símbolo y timeframe en `data/ohlcv/{SYMBOL}_{TF}.csv`.
- Universo por defecto (override con `ROTATION_UNIVERSE`): `BTCUSDT, ETHUSDT, BNBUSDT, SOLUSDT, ADAUSDT`.
- Timeframes soportados: `15m, 1h, 2h, 4h, 12h, 1d, 1w`.

## Feeds Multi-símbolo
- Módulo: `data/feeds/rotation_loader.py`
  - `default_universe()` lee `ROTATION_UNIVERSE` o usa universo por defecto.
  - `load_rotation_universe(symbols, timeframe)` carga dataframes por símbolo.
  - `rank_universe_by_strength(universe, ema_span)` calcula fuerza relativa (close/EMA - 1).

## Parámetros por Defecto (Registro)
- `CryptoRotation`: `lookback=50`, `universe="BTCUSDT,ETHUSDT,BNBUSDT"`.
- `OrderFlow`: `vol_mult=1.5`, `lookback=30`.

## Backtests Rápidos
- Escenario: `backtest/scenarios/rotation_orderflow.py`
  - `run_rotation_scenario(symbols, timeframe)` selecciona el símbolo top por fuerza relativa y ejecuta backtest.
  - `run_orderflow_scenario(symbols, timeframe)` usa el primer símbolo disponible con datos.
- Config YAML: `backtest/scenarios/rotation.yaml`

## Ejemplo de Uso
```python
from backtest.scenarios.rotation_orderflow import run_rotation_scenario, run_orderflow_scenario
print(run_rotation_scenario(["BTCUSDT","ETHUSDT","BNBUSDT"], "1h"))
print(run_orderflow_scenario(["BTCUSDT","ETHUSDT","BNBUSDT"], "1h"))
```

## Notas
- Asegúrate de sincronizar datos con `/refresh` incluyendo los símbolos del universo.
- Para rotación real, extiende la lógica para cambiar entre símbolos según ranking en cada periodo.
