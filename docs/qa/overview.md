# QA Overview

Este documento resume el alcance de QA automatizado y verificable:

## Cobertura mínima garantizada
- Normalización: `signal_consensus` ∈ [0,1], pesos normalizados suman 1.0
- Confianza: pisos no superan la confianza del soporte más débil
- Sizing: `position_size_usd` y `position_size_pct` presentes y consistentes
- Timeframes: `15m`, `2h`, `12h` integrados en agregación cuando hay datos
- Contratos: Esquema de respuesta sincronizado con modelos Pydantic

## Cómo ejecutar
```bash
python -m pytest -q
python qa/generate_status.py
```

## Resultado
- `docs/qa/status.md` publica un resumen legible de últimas ejecuciones
