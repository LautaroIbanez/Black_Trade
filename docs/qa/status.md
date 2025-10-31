# QA Status

- Timestamp: 2025-10-31T00:00:00Z
- Command: `.venv\\Scripts\\pytest -q`

<details><summary>Summary</summary>

```
Result: 68% executed, multiple failures remain
Failures (excerpt):
- backtest/tests/test_backtest_engine.py::TestBacktestEngine::test_split_and_walk_forward (indexing KeyError on forced close timestamp)
- backtest/tests/test_strategy_base.py::TestStrategyBase::test_cost_calculation (cost model expectation mismatch)
- backend/tests/test_normalization.py::TestNormalization::test_signal_consensus_normalization (consensus > 1.0 from mocked return)
- backend/tests/test_recommendation_service.py::* (StrategySignal signature requires entry_range/risk_targets)
- backend/tests/test_risk_management.py::TestPositionSizing::test_position_size_by_risk (legacy method missing)
- backend/tests/test_sync_continuity.py::TestDataContinuity::test_continuity_across_timeframes (expects records_count)
- tests/recommendation/test_endpoints.py::test_recommendation_includes_new_timeframes (no details for new TFs)
```

</details>

<details><summary>Environment</summary>

- Python: venv `.venv` (Windows)
- Installed via: `pip install -r requirements-dev.txt` (excluye ta-lib)
- PyTest: 7.4.4

</details>

<details><summary>Notes</summary>

- Se añadió `pandas` a `requirements-dev.txt` y `qa/requirements.txt`. Se excluyó `ta-lib` en dev para evitar compilación nativa.
- `pytest.ini` define `pythonpath = .` y `testpaths = backtest/tests backend/tests tests`.
- Próximas correcciones priorizadas: normalización de consenso/ confianza, firma de `StrategySignal` en tests, `records_count` en validación de datos, y ajuste de cierre forzado en split/walk-forward.

</details>
