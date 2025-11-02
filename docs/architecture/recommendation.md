# Arquitectura de Recomendación

## Agregador Soportado
- El agregador oficial y soportado se implementa en `backend/services/recommendation_service.py`.
- Este componente realiza: agregación multi-timeframe, normalización (0-1), gestión de riesgo y cálculo de consenso.

## Agregador Experimental (Opcional, Controlado)
- Existe un agregador simple experimental en `recommendation/experimental/aggregator.py` únicamente con fines de depuración.
- No se incluye en builds productivas ni se importa desde el backend.
- Si desea experimentar localmente, impórtelo explícitamente en un entorno de desarrollo aislado. Bajo su responsabilidad.

## Recomendación
- Use siempre `backend/services/recommendation_service.py` para cualquier integración, pruebas y documentación.
- Agregadores alternativos no forman parte del camino crítico y no se soportan en producción.

## Cálculo de Consenso

El consenso (`signal_consensus`) refleja el grado de acuerdo entre estrategias, con una filosofía clave: **incertidumbre ≠ convicción**.

### Principio Fundamental

**100% HOLD = 0% Consenso (Incertidumbre)**, no 100% consenso. Un escenario donde todas las estrategias están en HOLD refleja incertidumbre del mercado, no convicción total.

### Cálculo con Señales Mixtas

Cuando hay señales activas (BUY/SELL) mezcladas con neutrales (HOLD):

1. **Ponderación de Neutrals**: 
   - Los neutrals mantienen un peso residual proporcional al total de estrategias
   - Fórmula: `neutral_weight_factor = max(neutral_base_ratio * neutral_floor, min(neutral_base_ratio, 0.15))`
   - Parámetro configurable `neutral_floor` (default 0.3) previene sobreconfianza cuando pocas señales activas enfrentan muchas neutrales

2. **Cálculo de Consenso**:
   - Si hay señales activas: `signal_consensus = max(buy_ratio, sell_ratio)`
   - **MODERACIÓN PARA ESCENARIOS MIXTOS BUY/SELL/HOLD**: Si hay señales BUY y SELL coexistiendo con HOLD, el consenso se acota a `simple_majority - max_consensus_delta`
     - `simple_majority = max(buy_count, sell_count) / active_count`
     - Parámetro configurable `max_consensus_delta` (default 0.1) previene consenso inflado cuando señales activas están balanceadas
   - Si los neutrals predominan (>50% del total): el consenso se escala hacia abajo por la proporción de señales activas
   - Fórmula de escala: `signal_consensus = signal_consensus * (active_count / total_signals)`

3. **Límite de Seguridad**:
   - Si los neutrals predominan, el consenso nunca alcanza 1.0
   - Límite máximo: `max_consensus = 0.5 * (active_count / total_signals) + 0.3`
   - Esto previene falsa convicción cuando la mayoría de estrategias están indecisas

### Escenario 100% HOLD

Cuando todas las estrategias están en HOLD:
- `signal_consensus = 0.0` (umbral de incertidumbre configurable)
- `action = "HOLD"`
- `confidence = 0.0`

Esto refleja explícitamente que no hay convicción direccional, solo incertidumbre.

### Ejemplo Numérico 1: 2 BUY / 1 SELL / 4 HOLD

- Total: 7 señales (2 BUY, 1 SELL, 4 HOLD)
- Active: 3, Hold: 4
- Proporción activa: 3/7 ≈ 43%

Cálculo:
1. `neutral_base_ratio = 4/7 ≈ 0.57`
2. `neutral_weight_factor = max(0.57 * 0.3, min(0.57, 0.15)) = 0.15`
3. `weighted_hold_count = 4 * 0.15 = 0.6`
4. `effective_total = 3 + 0.6 = 3.6`
5. `buy_ratio = 2 / 3.6 ≈ 0.56`
6. `signal_consensus = 0.56` (inicial)
7. Como neutrals (4) > active (3), se escala: `signal_consensus = 0.56 * (3/7) ≈ 0.24`

**Resultado**: Consenso refleja incertidumbre, no convicción total, a pesar de que BUY > SELL.

### Ejemplo Numérico 2: 2 BUY / 1 SELL / 1 HOLD (Escenario Mixto)

- Total: 4 señales (2 BUY, 1 SELL, 1 HOLD)
- Active: 3, Hold: 1
- Proporción activa: 3/4 = 75%

Cálculo (con parámetros por defecto: `neutral_floor=0.3`, `max_consensus_delta=0.1`):
1. `neutral_base_ratio = 1/4 = 0.25`
2. `neutral_weight_factor = max(0.25 * 0.3, min(0.25, 0.15)) = 0.15`
3. `weighted_hold_count = 1 * 0.15 = 0.15`
4. `effective_total = 3 + 0.15 = 3.15`
5. `buy_ratio = 2 / 3.15 ≈ 0.635`
6. **MODERACIÓN**: Como hay BUY y SELL mezclados, aplicar limitación:
   - `simple_majority = 2/3 ≈ 0.667`
   - `signal_consensus = min(0.635, 0.667 - 0.1) = min(0.635, 0.567) = 0.567`

**Resultado**: Consenso moderado a 0.567, evitando inflación artificial por señales HOLD residuales. Sin moderación, el consenso sería 0.635, transmitiendo convicción superior a la justificada.

### Configuración de Parámetros

Los parámetros `neutral_floor` y `max_consensus_delta` se configuran al inicializar `RecommendationService`:

```python
# Valores por defecto: neutral_floor=0.3, max_consensus_delta=0.1
svc = RecommendationService()

# Personalización para escenarios más conservadores
svc = RecommendationService(neutral_floor=0.2, max_consensus_delta=0.05)

# Personalización para escenarios más permisivos
svc = RecommendationService(neutral_floor=0.4, max_consensus_delta=0.15)
```

Ver `docs/recommendation/timeframes.md` para más ejemplos numéricos y advertencias de interpretación.