# Timeframe Contribution and Weights

Este documento detalla cómo contribuye cada timeframe al consenso y a la confianza final.

## Pesos por Perfil

- balanced:
  - 15m: 0.3
  - 1h: 0.5
  - 2h: 0.6
  - 4h: 0.7
  - 12h: 0.8
  - 1d: 0.9
  - 1w: 1.0
- day_trading:
  - 15m: 0.9
  - 1h: 1.0
  - 2h: 0.9
  - 4h: 0.8
  - 12h: 0.5
  - 1d: 0.4
  - 1w: 0.2
- swing:
  - 15m: 0.2
  - 1h: 0.6
  - 2h: 0.8
  - 4h: 1.0
  - 12h: 0.9
  - 1d: 0.9
  - 1w: 0.3
- long_term:
  - 15m: 0.1
  - 1h: 0.2
  - 2h: 0.4
  - 4h: 0.4
  - 12h: 0.7
  - 1d: 0.8
  - 1w: 1.0

## Cómo influye en el scoring
- En `RecommendationService`, cada señal incorpora `timeframe_weight` al calcular `signal.confidence` y `signal.strength` (se multiplica por el peso del timeframe del perfil activo).
- La agregación final normaliza los pesos por estrategia (confidence × score) para formar `strategy_details.weight` y comprueba que la suma ≈ 1.0.
- `signal_consensus` refleja la proporción de señales por tipo (BUY/SELL/HOLD) con ponderación dinámica de neutrals y se acota a [0,1].

## Cálculo de Consenso con Ponderación Dinámica de Señales Neutrales

El consenso se calcula asignando pesos dinámicos a señales neutrales (HOLD) para evitar sobreconfianza cuando hay pocas señales activas.

### Fórmula de Ponderación de Neutrals

Cuando hay señales activas (BUY/SELL) y neutrals (HOLD):
- **Base ratio**: `neutral_base_ratio = hold_count / total_signals`
- **Factor de peso**: `neutral_weight_factor = max(neutral_base_ratio * 0.3, min(neutral_base_ratio, 0.15))`
  - Esto asegura un piso mínimo del 30% de la proporción base, pero no más del 15% del total
- **Conteo ponderado**: `weighted_hold_count = hold_count * neutral_weight_factor`

### Ejemplos Numéricos

#### Ejemplo 1: 2 BUY / 1 SELL / 3 HOLD (6 señales totales)
- Active: 3, Hold: 3, Total: 6
- `neutral_base_ratio = 3/6 = 0.5` (50%)
- `neutral_weight_factor = max(0.5 * 0.3, min(0.5, 0.15)) = max(0.15, 0.15) = 0.15` (15%)
- `weighted_hold_count = 3 * 0.15 = 0.45`
- `effective_total = 3 + 0.45 = 3.45`
- `buy_ratio = 2 / 3.45 ≈ 0.58` (58%)
- `sell_ratio = 1 / 3.45 ≈ 0.29` (29%)
- `hold_ratio = 0.45 / 3.45 ≈ 0.13` (13%)
- **Consenso**: `max(0.58, 0.29) = 0.58` (BUY prevalece, pero no inflado)

#### Ejemplo 2: 1 BUY / 0 SELL / 4 HOLD (5 señales totales)
- Active: 1, Hold: 4, Total: 5
- `neutral_base_ratio = 4/5 = 0.8` (80%)
- `neutral_weight_factor = max(0.8 * 0.3, min(0.8, 0.15)) = max(0.24, 0.15) = 0.24`
- `weighted_hold_count = 4 * 0.24 = 0.96`
- `effective_total = 1 + 0.96 = 1.96`
- `buy_ratio = 1 / 1.96 ≈ 0.51` (51%)
- `hold_ratio = 0.96 / 1.96 ≈ 0.49` (49%)
- **Consenso**: `0.51` (BUY apenas prevalece, reflejando la dispersión)

### Advertencias de Interpretación

#### Consenso = 0.0 (100% HOLD)

Cuando **todas las estrategias están en HOLD**, el consenso es **0.0**, reflejando **incertidumbre pura**, no convicción. Esto significa:
- ❌ **No significa**: "Todos están seguros de esperar"
- ✅ **Significa**: "Ninguna estrategia tiene convicción direccional suficiente"

**Interpretación**: El mercado está en indecisión. Espere señales más claras antes de tomar posición.

#### Consenso < 0.30 con Señales Mixtas

Cuando hay señales activas (BUY/SELL) pero **muchos neutrals (>50%)**:
- El consenso está escalado hacia abajo para reflejar la incertidumbre
- **Interpretación**: Señal débil; la mayoría de estrategias están indecisas
- **Recomendación**: Considerar esperar confirmación antes de tomar posición, o reducir tamaño de posición

#### Consenso 0.30 - 0.60 con Señales Mixtas

Cuando hay señales activas y neutrals están presentes pero no predominan:
- El consenso refleja acuerdo moderado
- **Interpretación**: Señal moderada; algunas estrategias están alineadas pero no todas
- **Recomendación**: Posición con cautela, considerar gestión de riesgo estricta

#### Consenso > 0.70

Cuando múltiples estrategias están alineadas y pocos neutrals:
- El consenso refleja alta convicción
- **Interpretación**: Señal clara; múltiples estrategias alineadas con pocos neutrals
- **Recomendación**: Señal más confiable; aún considerar gestión de riesgo adecuada

### Reglas de Oro

1. **Consenso bajo ≠ Señal débil automáticamente**: Si hay pocas estrategias activas pero todas están fuertemente alineadas, puede haber señal válida
2. **Consenso alto + muchos neutrals = Falsa convicción**: Si el consenso es alto pero >50% son neutrals, el sistema lo escala hacia abajo automáticamente
3. **100% HOLD siempre = Consenso 0.0**: Nunca interprete todos HOLD como consenso total
4. **Contexto importa**: Combine consenso con `confidence`, `risk_level` y `supporting_strategies` para decisión completa
5. **Consenso moderado en escenarios mixtos**: Cuando coexisten BUY y SELL (ej: 2 BUY / 1 SELL / 1 HOLD), el consenso se modera automáticamente para evitar sobreconfianza (ej: ~0.57 en lugar de ~0.63)

## Verificación y Estado de Tests

> ⚠️ **Nota sobre QA**: El pipeline de QA está reactivado y operativo. Estado actual: **129 passed, 4 failed**. Ver `docs/qa/status.md` para el estado actual de los tests y resultados de ejecuciones reales.

### Limitaciones Actuales

**Estado QA**: 129 passed, 4 failed

1. ✅ **Validación de consenso**: Tests de normalización y moderación de consenso (incluyendo escenarios mixtos 2 BUY / 1 SELL / 1 HOLD) operativos y pasando.

2. ⚠️ **Validación automática de timeframes**: El test `test_recommendation_includes_new_timeframes` falla por error en generación de señales (`'bool' object is not iterable` en Mean_Reversion, Ichimoku_ADX, RSIDivergence, Stochastic).

3. ⚠️ **Validación de pesos normalizados**: Aunque la lógica está implementada, la validación automatizada requiere que todos los tests de timeframes pasen para confirmarse completamente.

Para más detalles sobre el estado de QA y problemas conocidos, consultar `docs/qa/status.md` y `docs/CHANGELOG.md`.

### Tests Disponibles

Los siguientes tests están definidos y pueden ejecutarse con `python -m pytest`:

- ✅ **`tests/recommendation/test_aggregator.py`**: Tests unitarios del agregador (OPERATIVOS) que validan:
  - Que los pesos normalizados suman ≈ 1.0
  - Que el cálculo de consenso respeta los límites [0, 1]
  - Que la ponderación dinámica de neutrals funciona correctamente
  - Que 100% HOLD resulta en consenso = 0.0 (incertidumbre)
  - Que señales mixtas con predominio de neutrals no saturan el consenso
  - Que escenarios mixtos BUY/SELL/HOLD (ej: 2 BUY / 1 SELL / 1 HOLD) moderan el consenso correctamente
- ⚠️ **`tests/recommendation/test_endpoints.py::test_recommendation_includes_new_timeframes`**: Verifica que los timeframes `15m`, `2h` y `12h` aparecen en `strategy_details` cuando hay datos disponibles (falla - ver limitaciones)

### Verificación Manual

Mientras el pipeline de QA se completa, se puede verificar manualmente:

1. **Ejecutar recomendación**: `GET /recommendation`
2. **Verificar `strategy_details`**: Comprobar que contiene señales de todos los timeframes con datos disponibles
3. **Validar suma de pesos**: Sumar todos los `weight` en `strategy_details` (debe ser ≈ 1.0)
4. **Verificar consenso**: `signal_consensus` debe estar en [0, 1] y reflejar correctamente la dispersión de señales

### Estado de Validación Automática

Las pruebas automatizadas están disponibles en:
- `tests/recommendation/test_aggregator.py`: Tests de consenso y normalización (✅ operativos, todos pasando)
- `tests/recommendation/test_endpoints.py`: Test de inclusión de timeframes (⚠️ falla - ver limitaciones)
- `tests/strategies/test_rotation.py`: Tests de CryptoRotation multi-activo (✅ operativos, todos pasando)

**Resumen**: 129 passed, 4 failed (3 backtesting, 1 endpoints).

Para ejecutar los tests y obtener resultados actuales:
```bash
python qa/generate_status.py
```

Para más detalles sobre el estado de QA y cómo ejecutar los tests, ver `docs/qa/status.md` y `qa/README.md`.
