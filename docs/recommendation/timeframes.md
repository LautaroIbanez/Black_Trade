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

- **Consenso < 0.55 con señales mixtas**: Interpretar como señal débil o neutral; considerar esperar confirmación antes de tomar posición.
- **Muchos neutrals (>50%)**: Incluso con una mayoría activa, el consenso será conservador, reflejando incertidumbre del mercado.
- **Consenso > 0.70**: Señal más clara; múltiples estrategias alineadas con pocos neutrals.

## Verificación y Estado de Tests

> ⚠️ **Nota sobre QA**: El pipeline de QA está siendo reactivado. Ver `docs/qa/status.md` para el estado actual de los tests y la epic de reactivación de QA en progreso.

### Tests Planeados

Los siguientes tests están definidos pero requieren que el pipeline de QA esté completamente operativo:

- **`tests/recommendation/test_endpoints.py::test_recommendation_includes_new_timeframes`**: Verifica que los timeframes `15m`, `2h` y `12h` aparecen en `strategy_details` cuando hay datos disponibles
- **`tests/recommendation/test_aggregator.py`**: Tests unitarios del agregador que validan:
  - Que los pesos normalizados suman ≈ 1.0
  - Que el cálculo de consenso respeta los límites [0, 1]
  - Que la ponderación dinámica de neutrals funciona correctamente

### Limitaciones Conocidas

Hasta que la suite de QA esté completamente reactivada y todos los tests pasen:

1. **Inclusión de timeframes**: El endpoint de recomendaciones puede no incluir todos los timeframes disponibles en `strategy_details` cuando hay datos disponibles para múltiples timeframes.
2. **Validación de pesos**: La validación automática de que los pesos normalizados suman ~1.0 requiere ejecución de tests para confirmarse.
3. **Consenso**: El cálculo de consenso con ponderación dinámica está implementado, pero requiere validación end-to-end mediante tests.

### Verificación Manual

Mientras tanto, se puede verificar manualmente:

1. **Ejecutar recomendación**: `GET /recommendation`
2. **Verificar `strategy_details`**: Comprobar que contiene señales de todos los timeframes con datos disponibles
3. **Validar suma de pesos**: Sumar todos los `weight` en `strategy_details` (debe ser ≈ 1.0)
4. **Verificar consenso**: `signal_consensus` debe estar en [0, 1] y reflejar correctamente la dispersión de señales

Para más detalles sobre el estado de QA y cómo ejecutar los tests, ver `docs/qa/status.md` y `qa/README.md`.
