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

El consenso (`signal_consensus`) refleja el grado de acuerdo entre estrategias, con ponderación dinámica para señales neutrales:
- Señales neutrales (HOLD) reciben un peso proporcional a su número pero reducido cuando hay señales activas
- Fórmula: `neutral_weight_factor = max(neutral_base_ratio * 0.3, min(neutral_base_ratio, 0.15))`
- Esto previene sobreconfianza cuando pocas señales activas enfrentan muchas neutrales
- Consenso se calcula como: `max(buy_ratio, sell_ratio)` donde los ratios usan el `effective_total = active_count + weighted_hold_count`

Ver `docs/recommendation/timeframes.md` para ejemplos numéricos y advertencias de interpretación.