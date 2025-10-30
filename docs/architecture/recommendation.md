# Arquitectura de Recomendación

## Agregador Soportado
- El agregador oficial y soportado se implementa en `backend/services/recommendation_service.py`.
- Este componente realiza: agregación multi-timeframe, normalización (0-1), gestión de riesgo y cálculo de consenso.

## Agregador Legacy (Opcional, Controlado)
- Existe un agregador simple legacy en `recommendation/aggregator.py` únicamente con fines de depuración.
- Está deshabilitado por defecto y no se importa en producción.
- Para habilitarlo temporalmente de forma controlada:

```bash
export USE_SIMPLE_AGGREGATOR=true
```

- El backend lo condiciona mediante `USE_SIMPLE_AGGREGATOR` y no afecta al flujo normal si no se activa.

## Recomendación
- Use siempre `backend/services/recommendation_service.py` para cualquier integración, pruebas y documentación.
- Cualquier referencia a agregadores alternativos debe declararse detrás de flags y no formar parte del camino crítico.
