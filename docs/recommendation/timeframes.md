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
- **PENALIZACIÓN NEUTRAL**: `hold_count=4 > neutral_count_threshold=2`, `excess_neutrals=2`, `penalty = 0.95^2 ≈ 0.90`
- **Consenso**: `0.51 * 0.90 ≈ 0.46` (BUY apenas prevalece, pero escalado por la incertidumbre de múltiples HOLD)

#### Ejemplo 3: 2 BUY / 1 SELL / 1 HOLD (Escenario Mixto con Oposición)
- Total: 4 señales (2 BUY, 1 SELL, 1 HOLD)
- Active: 3, Hold: 1
- Proporción activa: 3/4 = 75%

Cálculo paso a paso:
1. `neutral_base_ratio = 1/4 = 0.25`
2. `neutral_weight_factor = max(0.25 * 0.3, min(0.25, 0.15)) = 0.15`
3. `weighted_hold_count = 1 * 0.15 = 0.15`
4. `effective_total = 3 + 0.15 = 3.15`
5. `buy_ratio = 2 / 3.15 ≈ 0.635`
6. `sell_ratio = 1 / 3.15 ≈ 0.317`
7. **MODERACIÓN MIXTA**: Como hay BUY y SELL coexistiendo, aplicar `mixed_consensus_cap=0.60`:
   - `signal_consensus = min(0.635, 0.60) = 0.60`
8. **PENALIZACIÓN NEUTRAL**: `hold_count=1 <= neutral_count_threshold=2`, no se aplica

**Resultado**: Consenso = 0.60 (moderado por oposición BUY/SELL)

**Interpretación**: Aunque BUY tiene mayoría (2 vs 1), el consenso está limitado a 0.60 debido a la presencia de señales opuestas. Esto indica señal moderada con dirección clara pero incertidumbre subyacente.

#### Ejemplo 4: 1 BUY / 1 SELL / 3 HOLD (Oposición con Múltiples Neutrals)
- Total: 5 señales (1 BUY, 1 SELL, 3 HOLD)
- Active: 2, Hold: 3
- Proporción activa: 2/5 = 40%

Cálculo paso a paso:
1. `neutral_base_ratio = 3/5 = 0.6`
2. `neutral_weight_factor = max(0.6 * 0.3, min(0.6, 0.15)) = 0.15`
3. `weighted_hold_count = 3 * 0.15 = 0.45`
4. `effective_total = 2 + 0.45 = 2.45`
5. `buy_ratio = 1 / 2.45 ≈ 0.408`
6. `sell_ratio = 1 / 2.45 ≈ 0.408`
7. **MODERACIÓN MIXTA**: Como hay BUY y SELL coexistiendo, aplicar `mixed_consensus_cap=0.60`:
   - `signal_consensus = min(0.408, 0.60) = 0.408`
8. **ESCALA POR NEUTRALS DOMINANTES**: Como `hold_count=3 > active_count=2`, escalar por proporción activa:
   - `active_proportion = 2/5 = 0.4`
   - `signal_consensus = 0.408 * 0.4 ≈ 0.163`
9. **PENALIZACIÓN NEUTRAL**: `hold_count=3 > neutral_count_threshold=2`, `excess_neutrals=1`, `penalty = 0.95^1 = 0.95`
   - `signal_consensus = 0.163 * 0.95 ≈ 0.155`

**Resultado**: Consenso = 0.155 (bajo debido a oposición y predominio de neutrals)

**Interpretación**: Bajo consenso refleja incertidumbre significativa: señales opuestas (BUY/SELL) y mayoría de estrategias indecisas (HOLD). Recomendación: esperar señales más claras.

### Tabla de Referencia Rápida: Escenarios Mixtos

| Escenario | BUY | SELL | HOLD | Consenso Esperado | Interpretación |
|-----------|-----|------|------|-------------------|----------------|
| 2 BUY / 1 SELL / 1 HOLD | 2 | 1 | 1 | ~0.60 (cap aplicado) | Señal moderada con oposición |
| 1 BUY / 1 SELL / 2 HOLD | 1 | 1 | 2 | ~0.35-0.50 (cap + escala) | Baja convicción, conflicto |
| 1 BUY / 1 SELL / 3 HOLD | 1 | 1 | 3 | ~0.15-0.25 (cap + escala + penalización) | Alta incertidumbre |
| 3 BUY / 0 SELL / 1 HOLD | 3 | 0 | 1 | ~0.75-0.85 (sin oposición) | Alta convicción BUY |
| 0 BUY / 0 SELL / 4 HOLD | 0 | 0 | 4 | 0.0 (incertidumbre) | Sin dirección clara |

**Nota**: Los valores exactos dependen de los pesos de confidence/score de cada señal. Esta tabla muestra rangos típicos.

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

Cuando hay señales activas y neutrals están presentes pero no predominan, o cuando BUY y SELL coexisten:
- El consenso refleja acuerdo moderado con incertidumbre
- **Con BUY/SELL opuestos**: El consenso está limitado por `mixed_consensus_cap` (default: 0.60) para reflejar la oposición
- **Interpretación**: Señal moderada; algunas estrategias están alineadas pero hay conflicto u oposición
- **Recomendación**: Posición con cautela, considerar gestión de riesgo estricta. No interprete como alta convicción aunque la dirección esté clara.

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
5. **Consenso moderado en escenarios mixtos**: Cuando coexisten BUY y SELL (ej: 2 BUY / 1 SELL / 1 HOLD), el consenso se modera automáticamente mediante `mixed_consensus_cap` (default: 0.60) para evitar sobreconfianza. El consenso refleja incertidumbre cuando hay señales opuestas.

## Verificación y Estado de Tests

> ⚠️ **Nota sobre QA**: El pipeline de QA está reactivado y operativo. Estado actual: **136 passed, 1 failed**. Ver `docs/qa/status.md` para el estado actual de los tests y resultados de ejecuciones reales.

### Limitaciones Actuales

#### Tests y Validación

- **Estado general**: 136 tests pasando, 1 fallando (no crítico)
- **Test fallando**: `test_recommendation_includes_new_timeframes` - Error en generación de señales para Mean_Reversion, Ichimoku_ADX, RSIDivergence, Stochastic (`'bool' object is not iterable`)
  - **Impacto**: El endpoint puede no incluir todos los timeframes en `strategy_details` cuando estas estrategias fallan
  - **Responsable**: Equipo Backend / Estrategias
  - **Prioridad**: Media (no bloquea funcionalidad core)
  - **Target**: Próximo sprint (2-3 semanas)

#### Calibración de Consenso

- **Parámetros configurados**: `mixed_consensus_cap` (default: 0.60), `neutral_count_factor` (default: 0.95), `neutral_count_threshold` (default: 2)
- **Estado**: Funcional y validado con tests, pero puede requerir ajuste fino según feedback de uso en producción
- **Documentación**: Ver `docs/architecture/recommendation.md` para detalles de configuración y ejemplos numéricos

### Tests Disponibles

Los siguientes tests están definidos y pueden ejecutarse con `python -m pytest`:

- ✅ **`tests/recommendation/test_aggregator.py`**: Tests unitarios del agregador (OPERATIVOS) que validan:
  - Que los pesos normalizados suman ≈ 1.0
  - Que el cálculo de consenso respeta los límites [0, 1]
  - Que la ponderación dinámica de neutrals funciona correctamente
  - Que 100% HOLD resulta en consenso = 0.0 (incertidumbre)
  - Que señales mixtas con predominio de neutrals no saturan el consenso
  - Que escenarios mixtos BUY/SELL/HOLD (ej: 2 BUY / 1 SELL / 1 HOLD) moderan el consenso correctamente
- ✅ **`tests/recommendation/test_e2e_minimal.py`**: Tests end-to-end del pipeline completo (OPERATIVOS)
- ⚠️ **`tests/recommendation/test_endpoints.py::test_recommendation_includes_new_timeframes`**: Verifica que los timeframes `15m`, `2h` y `12h` aparecen en `strategy_details` cuando hay datos disponibles (falla - ver limitaciones arriba)

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

**Resumen**: 136 passed, 1 failed (endpoints - error en estrategias específicas, ver limitaciones arriba).

Para ejecutar los tests y obtener resultados actuales:
```bash
python qa/generate_status.py
```

Para más detalles sobre el estado de QA y cómo ejecutar los tests, ver `docs/qa/status.md` y `qa/README.md`.
