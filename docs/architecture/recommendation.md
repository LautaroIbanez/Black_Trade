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
