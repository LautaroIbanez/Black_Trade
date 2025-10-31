### CryptoRotation y OrderFlow - Propuesta de valor activada

**Objetivo**: Transformar prototipos en estrategias multi-activo con métricas de backtest consistentes.

### Ingesta de datos multi-activo
- `data/feeds/rotation_loader.py` soporta múltiples símbolos vía `load_rotation_universe(symbols, timeframe)` y ranking por fuerza relativa con `rank_universe_by_strength`.
- Se puede configurar el universo con `ROTATION_UNIVERSE="BTCUSDT,ETHUSDT,..."`.

### Estrategia CryptoRotation
- Señales basadas en `rel = close/EMA(lookback)-1`.
- Entradas cuando `rel > +0.5%` (largo) o `rel < -0.5%` (corto).
- Cierres con señal opuesta o al finalizar el backtest.
- Escenario de backtest: seleccionar el símbolo con mayor fuerza relativa en cada corrida (`backtest/scenarios/rotation_orderflow.py::run_rotation_scenario`).

### Estrategia OrderFlow
- Señales cuando hay volumen anómalo (`volume > vol_mult * MA_volume(lookback)`) alineado con el retorno de la vela.
- Entradas en la dirección del movimiento; salidas con señal opuesta o normalización (signal=0) y cierre forzado al final.

### Fixtures/escenarios
- `backtest/scenarios/rotation.yaml`: símbolos y parámetros por defecto para ambas estrategias.
- `backtest/scenarios/orderflow.yaml`: símbolos y parámetros de OrderFlow.

### Resultados de backtests (ejemplo orientativo)
- En datasets con `1h` y universo `{BTC,ETH,BNB}`, ambas estrategias generan operaciones con `win_rate > 0` en periodos con tendencias o eventos de volumen; en rangos estrechos, OrderFlow tiende a operar menos y CryptoRotation depende del umbral de `rel`.

### Requisitos de datos
- OHLCV por símbolo en `data/ohlcv/{SYMBOL}_{TF}.csv` con columnas `timestamp,open,high,low,close,volume`.
- Cobertura suficiente para calcular EMA(lookback) y medias de volumen.

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
