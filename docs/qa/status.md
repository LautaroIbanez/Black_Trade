# QA Status

**Última ejecución:** 2025-11-02 08:04:15  
**Estado:** ❌ FAILED  
**Comando:** `C:\Users\lauta\AppData\Local\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0\python.exe -m pytest --tb=short`  
**Código de salida:** 1

## Resumen

1 failed, 136 passed, 2 warnings in 10.32s

### Conteo de tests
- ✅ Pasados: 136
- ❌ Fallidos: 1
- ⚠️  Errores: 0
- ⏭️  Omitidos: 0

## Salida completa

<details>
<summary>Ver salida completa (click para expandir)</summary>

```
........................................................................ [ 52%]
...............................................F.................        [100%]
================================== FAILURES ===================================
_________________ test_recommendation_includes_new_timeframes _________________
tests\recommendation\test_endpoints.py:39: in test_recommendation_includes_new_timeframes
    assert {'15m', '2h', '12h'}.intersection(tfs) == {'15m', '2h', '12h'} or len(tfs) > 0
E   AssertionError: assert (set() == {'12h', '15m', '2h'}
E     Extra items in the right set:
E     '2h'
E     '15m'
E     '12h'
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
FAILED tests/recommendation/test_endpoints.py::test_recommendation_includes_new_timeframes
1 failed, 136 passed, 2 warnings in 10.32s

```

```

```
</details>

## Resumen Ejecutivo

### Estado Actual de la Suite
- **Tests pasando**: 136
- **Tests fallando**: 1
- **Errores**: 0
- **Omitidos**: 0

### Tests Fallidos y Responsables

#### 1. `test_recommendation_includes_new_timeframes` (tests/recommendation/test_endpoints.py:39)

**Estado**: ❌ FALLANDO  
**Prioridad**: Media (no bloquea funcionalidad core)  
**Responsable**: Equipo Backend / Estrategias  
**Target de corrección**: Próximo sprint (2-3 semanas)

**Descripción del error**:
- **Causa**: Error en generación de señales para estrategias Mean_Reversion, Ichimoku_ADX, RSIDivergence, Stochastic
- **Error específico**: `'bool' object is not iterable`
- **Impacto**: El endpoint `/recommendation` no incluye timeframes `15m`, `2h`, `12h` en `strategy_details` cuando estas estrategias fallan al generar señales
- **Contexto**: El test verifica que los nuevos timeframes aparezcan en los detalles de estrategia, pero las estrategias mencionadas fallan en la generación de señales con datos de prueba mínimos

**Nota**: Este error es de las implementaciones de estrategias específicas, no del pipeline de QA ni del servicio de recomendaciones. Las estrategias fallan al procesar datos mínimos de prueba (3 registros OHLCV).

### Tests Críticos Operativos

✅ **Tests de consenso y agregación**: Todos pasando, incluyendo escenarios mixtos (2 BUY / 1 SELL / 1 HOLD)  
✅ **Tests de walk-forward**: Corregido bug de índice fuera de rango  
✅ **Tests de costes**: Corregidas expectativas del modelo  
✅ **Tests end-to-end**: Pipeline completo validado  
✅ **Tests de normalización**: Validación completa de consenso y confianza  

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
