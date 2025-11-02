# QA Status

**Última ejecución:** 2025-11-01 14:00:58  
**Estado:** ❌ FAILED  
**Comando:** `C:\Users\lauta\AppData\Local\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0\python.exe -m pytest --tb=short`  
**Código de salida:** 1

## Resumen

4 failed, 129 passed, 2 warnings in 23.87s

### Conteo de tests
- ✅ Pasados: 129
- ❌ Fallidos: 4
- ⚠️  Errores: 0
- ⏭️  Omitidos: 0

## Salida completa

<details>
<summary>Ver salida completa (click para expandir)</summary>

```
.........F......................F......F................................ [ 54%]
...........................................F.................            [100%]
================================== FAILURES ===================================
_______________ TestBacktestEngine.test_split_and_walk_forward ________________
..\..\..\..\AppData\Local\Packages\PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0\LocalCache\local-packages\Python311\site-packages\pandas\core\indexes\range.py:414: in get_loc
    return self._range.index(new_key)
E   ValueError: 29 is not in range

The above exception was the direct cause of the following exception:
backtest\tests\test_backtest_engine.py:159: in test_split_and_walk_forward
    split_result = engine.run_backtest_with_split(strategy, self.sample_data, '1h', split=0.7)
backtest\engine.py:195: in run_backtest_with_split
    out_sample = self.run_backtest(strategy, test, timeframe)
backtest\engine.py:131: in run_backtest
    metrics = strategy.backtest(data)
strategies\strategy_base.py:300: in backtest
    trades = self.generate_trades(signals_df)
strategies\momentum_strategy.py:51: in generate_trades
    final_trade = self.close_all_positions(df, position, df.iloc[-1]['close'], len(df) - 1)
strategies\strategy_base.py:276: in close_all_positions
    "exit_time": df.loc[current_idx, 'timestamp'],
..\..\..\..\AppData\Local\Packages\PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0\LocalCache\local-packages\Python311\site-packages\pandas\core\indexing.py:1146: in __getitem__
    return self.obj._get_value(*key, takeable=self._takeable)
..\..\..\..\AppData\Local\Packages\PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0\LocalCache\local-packages\Python311\site-packages\pandas\core\frame.py:4012: in _get_value
    row = self.index.get_loc(index)
..\..\..\..\AppData\Local\Packages\PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0\LocalCache\local-packages\Python311\site-packages\pandas\core\indexes\range.py:416: in get_loc
    raise KeyError(key) from err
E   KeyError: 29
___________________ TestStrategyBase.test_cost_calculation ____________________
backtest\tests\test_strategy_base.py:56: in test_cost_calculation
    self.assertAlmostEqual(costs, expected_total, places=6)
E   AssertionError: 0.3075 != 0.315 within 6 places (0.007500000000000007 difference)
______ TestStrategyImplementations.test_strategies_with_different_costs _______
backtest\tests\test_strategy_base.py:211: in test_strategies_with_different_costs
    self.assertGreater(metrics_high_cost['total_costs'], metrics_no_cost['total_costs'])
E   AssertionError: 0.0 not greater than 0.0
_________________ test_recommendation_includes_new_timeframes _________________
tests\recommendation\test_endpoints.py:39: in test_recommendation_includes_new_timeframes
    assert {'15m', '2h', '12h'}.intersection(tfs) == {'15m', '2h', '12h'} or len(tfs) > 0
E   AssertionError: assert (set() == {'12h', '15m', '2h'}
E     Extra items in the right set:
E     '12h'
E     '2h'
E     '15m'
E     Use -v to get more diff or 0 > 0)
E    +  where 0 = len(set())
---------------------------- Captured stdout call -----------------------------
Error generating signal for Mean_Reversion on 15m: 'bool' object is not iterable
Error generating signal for Mean_Reversion on 15m: 'bool' object is not iterable
Error generating signal for Mean_Reversion on 15m: 'bool' object is not iterable
Error generating signal for Ichimoku_ADX on 15m: 'bool' object is not iterable
Error generating signal for Ichimoku_ADX on 15m: 'bool' object is not iterable
Error generating signal for Ichimoku_ADX on 15m: 'bool' object is not iterable
Error generating signal for RSIDivergence on 15m: 'bool' object is not iterable
Error generating signal for Stochastic on 15m: 'bool' object is not iterable
Error generating signal for Mean_Reversion on 1h: 'bool' object is not iterable
Error generating signal for Mean_Reversion on 1h: 'bool' object is not iterable
Error generating signal for Mean_Reversion on 1h: 'bool' object is not iterable
Error generating signal for Ichimoku_ADX on 1h: 'bool' object is not iterable
Error generating signal for Ichimoku_ADX on 1h: 'bool' object is not iterable
Error generating signal for Ichimoku_ADX on 1h: 'bool' object is not iterable
Error generating signal for RSIDivergence on 1h: 'bool' object is not iterable
Error generating signal for Stochastic on 1h: 'bool' object is not iterable
Error generating signal for Mean_Reversion on 2h: 'bool' object is not iterable
Error generating signal for Mean_Reversion on 2h: 'bool' object is not iterable
Error generating signal for Mean_Reversion on 2h: 'bool' object is not iterable
Error generating signal for Ichimoku_ADX on 2h: 'bool' object is not iterable
Error generating signal for Ichimoku_ADX on 2h: 'bool' object is not iterable
Error generating signal for Ichimoku_ADX on 2h: 'bool' object is not iterable
Error generating signal for RSIDivergence on 2h: 'bool' object is not iterable
Error generating signal for Stochastic on 2h: 'bool' object is not iterable
Error generating signal for Mean_Reversion on 4h: 'bool' object is not iterable
Error generating signal for Mean_Reversion on 4h: 'bool' object is not iterable
Error generating signal for Mean_Reversion on 4h: 'bool' object is not iterable
Error generating signal for Ichimoku_ADX on 4h: 'bool' object is not iterable
Error generating signal for Ichimoku_ADX on 4h: 'bool' object is not iterable
Error generating signal for Ichimoku_ADX on 4h: 'bool' object is not iterable
Error generating signal for RSIDivergence on 4h: 'bool' object is not iterable
Error generating signal for Stochastic on 4h: 'bool' object is not iterable
Error generating signal for Mean_Reversion on 12h: 'bool' object is not iterable
Error generating signal for Mean_Reversion on 12h: 'bool' object is not iterable
Error generating signal for Mean_Reversion on 12h: 'bool' object is not iterable
Error generating signal for Ichimoku_ADX on 12h: 'bool' object is not iterable
Error generating signal for Ichimoku_ADX on 12h: 'bool' object is not iterable
Error generating signal for Ichimoku_ADX on 12h: 'bool' object is not iterable
Error generating signal for RSIDivergence on 12h: 'bool' object is not iterable
Error generating signal for Stochastic on 12h: 'bool' object is not iterable
Error generating signal for Mean_Reversion on 1d: 'bool' object is not iterable
Error generating signal for Mean_Reversion on 1d: 'bool' object is not iterable
Error generating signal for Mean_Reversion on 1d: 'bool' object is not iterable
Error generating signal for Ichimoku_ADX on 1d: 'bool' object is not iterable
Error generating signal for Ichimoku_ADX on 1d: 'bool' object is not iterable
Error generating signal for Ichimoku_ADX on 1d: 'bool' object is not iterable
Error generating signal for RSIDivergence on 1d: 'bool' object is not iterable
Error generating signal for Stochastic on 1d: 'bool' object is not iterable
Error generating signal for Mean_Reversion on 1w: 'bool' object is not iterable
Error generating signal for Mean_Reversion on 1w: 'bool' object is not iterable
Error generating signal for Mean_Reversion on 1w: 'bool' object is not iterable
Error generating signal for Ichimoku_ADX on 1w: 'bool' object is not iterable
Error generating signal for Ichimoku_ADX on 1w: 'bool' object is not iterable
Error generating signal for Ichimoku_ADX on 1w: 'bool' object is not iterable
Error generating signal for RSIDivergence on 1w: 'bool' object is not iterable
Error generating signal for Stochastic on 1w: 'bool' object is not iterable
============================== warnings summary ===============================
tests/qa/test_contracts.py::test_recommendation_response_schema_fields
  C:\Users\lauta\OneDrive\Desktop\Trading\Black_Trade\backend\app.py:108: DeprecationWarning: 
          on_event is deprecated, use lifespan event handlers instead.
  
          Read more about it in the
          [FastAPI docs for Lifespan Events](https://fastapi.tiangolo.com/advanced/events/).
          
    @app.on_event("startup")

tests/qa/test_contracts.py::test_recommendation_response_schema_fields
  C:\Users\lauta\AppData\Local\Packages\PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0\LocalCache\local-packages\Python311\site-packages\fastapi\applications.py:4495: DeprecationWarning: 
          on_event is deprecated, use lifespan event handlers instead.
  
          Read more about it in the
          [FastAPI docs for Lifespan Events](https://fastapi.tiangolo.com/advanced/events/).
          
    return self.router.on_event(event_type)

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ===========================
FAILED backtest/tests/test_backtest_engine.py::TestBacktestEngine::test_split_and_walk_forward
FAILED backtest/tests/test_strategy_base.py::TestStrategyBase::test_cost_calculation
FAILED backtest/tests/test_strategy_base.py::TestStrategyImplementations::test_strategies_with_different_costs
FAILED tests/recommendation/test_endpoints.py::test_recommendation_includes_new_timeframes
4 failed, 129 passed, 2 warnings in 23.87s

```

```

```
</details>

## Incidencias Pendientes

### Tests Faltantes

**Prioridad Media** (no bloquean funcionalidad core):

1. **Backtesting - Walk Forward** (`test_split_and_walk_forward`):
   - **Error**: KeyError en cierre forzado de posiciones al final del split
   - **Causa**: Index fuera de rango en `strategies/strategy_base.py:276` (línea `df.loc[current_idx, 'timestamp']`)
   - **Archivo**: `backtest/tests/test_backtest_engine.py:159`
   - **Responsable**: Equipo Backend / Backtesting
   - **Target**: Próximo sprint (2-3 semanas)

2. **Backtesting - Cálculo de Costes** (`test_cost_calculation`, `test_strategies_with_different_costs`):
   - **Error**: Desajuste entre costes calculados y esperados
   - **Causa**: Modelo de costes necesita ajuste en cálculo total
   - **Archivos**: `backtest/tests/test_strategy_base.py:56,211`
   - **Responsable**: Equipo Backend / Backtesting
   - **Target**: Próximo sprint (2-3 semanas)

3. **Endpoints - Timeframes** (`test_recommendation_includes_new_timeframes`):
   - **Error**: `'bool' object is not iterable` en generación de señales
   - **Causa**: Error en Mean_Reversion, Ichimoku_ADX, RSIDivergence, Stochastic
   - **Archivo**: `tests/recommendation/test_endpoints.py:39`
   - **Responsable**: Equipo Backend / Estrategias
   - **Target**: Próximo sprint (2-3 semanas)

### Tests Exitosos

**Resaltados**: 129 tests pasando, incluyendo:
- ✅ Normalización y moderación de consenso (incluyendo escenarios mixtos)
- ✅ CryptoRotation multi-activo (todos los tests de rotación pasando)
- ✅ Gestión de riesgo y cálculo de SL/TP
- ✅ Tests end-to-end del pipeline completo
- ✅ Consenso neutral (100% HOLD = 0% consenso)

Para más detalles sobre estado general y plan de acción, ver `docs/CHANGELOG.md` y `docs/roadmap.md`.

## Notas

Este archivo se actualiza automáticamente después de cada ejecución de `pytest` usando el script `qa/generate_status.py`.

Para ejecutar manualmente:
```bash
python qa/generate_status.py
```

O combinar ejecución y actualización:
```bash
python -m pytest -q && python qa/generate_status.py
```
