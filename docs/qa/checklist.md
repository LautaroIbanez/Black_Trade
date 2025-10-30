# Checklist de Auditoría (Pre-release)

Use esta lista antes de cada release para validar transparencia y consistencia.

## Normalización y Consenso
- [ ] `signal_consensus` ∈ [0, 1] en muestras recientes
- [ ] Suma de `strategy_details.weight` ≈ 1.0
- [ ] Confianza no forzada por encima del soporte más débil

## Sizing y Gestión de Riesgo
- [ ] `position_size_usd` y `position_size_pct` presentes en respuesta
- [ ] `risk_reward_ratio` > 0 en ejemplos BUY/SELL
- [ ] `risk_percentage` dentro de rango razonable (0-100)

## Timeframes y Datos
- [ ] Series 15m/2h/12h presentes en `/refresh` y usadas en `/recommendation`
- [ ] Validación de continuidad sin errores críticos

## Estrategias y Registro
- [ ] CryptoRotation y OrderFlow habilitadas según configuración
- [ ] Generan trades en backtests de muestra

## QA Automatizado
- [ ] `python -m pytest -q` pasa sin fallos
- [ ] `docs/qa/status.md` actualizado con timestamp reciente

## Documentación
- [ ] `docs/api/recommendation.md` sincronizado con esquema actual
- [ ] README actualizado con pasos de QA
- [ ] `docs/qa/overview.md` y este checklist visibles
