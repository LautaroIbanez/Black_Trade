# Investor Summary

Este documento resume el estado actual del sistema, sus limitaciones y el plan de trabajo para los próximos hitos, con el objetivo de mantener una comunicación clara y verificable con stakeholders.

## Estado Actual y Limitaciones

- Confianza y Consenso:
  - No se aplican floors/boosts artificiales: la confianza proviene de señales reales (0–1) y el consenso está acotado a [0,1].
  - Posible baja confianza en escenarios de señales débiles o conflictivas.
- Estrategias en ajuste:
  - MACD: se corrigió el filtro de línea cero; genera trades en datasets con cruces. Aún requiere calibración fina por timeframe.
  - CryptoRotation y OrderFlow: habilitadas con parámetros conservadores; requieren universo multi-símbolo actualizado y más calibración de triggers para mayor diversificación.
- Gestión de riesgo:
  - SL/TP validado con buffer dinámico (ATR × perfil). Fallback porcentual solo si no hay ATR.
- QA y transparencia:
  - Advertencia: La suite de QA está en expansión; algunas pruebas integrales y de regresión están en progreso. Consulte `docs/qa/status.md` para el estado más reciente.
  - Advertencia: Varias estrategias se encuentran en calibración activa (umbrales y parámetros pueden cambiar entre versiones menores).
  - Pesos por timeframe documentados y verificados; nuevas temporalidades integradas.

### Limitaciones actuales

- La confianza agregada puede superar la señal más débil en escenarios desbalanceados; la normalización está en curso para capear por media y mínimo activo.
- MACD, CryptoRotation y OrderFlow en calibración fina; parámetros sujetos a ajuste hasta cerrar la epic.
- QA end-to-end en progreso; ver ejecución real en `docs/qa/status.md`.

## Roadmap (próximos 4–6 semanas)

- Multi-símbolo y datos:
  - Consolidar universo (`ROTATION_UNIVERSE`) y refresco automático por símbolo/timeframe en `/refresh`.
  - Validaciones de continuidad y frescura por símbolo con alertas.
- Calibraciones y backtesting:
  - MACD: barrido de parámetros por timeframe (8/17/6, 12/26/9) con evaluación OOS.
  - OrderFlow: sensibilidad de `vol_mult` por régimen de volatilidad.
  - CryptoRotation: ranking multi-factor (EMA/RSI/volatilidad) y rotación multi-activo.
- Monitorización y reporting:
  - Reporte quincenal en `docs/reports/strategy_performance.md` (trades, win-rate, DD, retorno) + alertas automáticas (actividad nula, win-rate anómalo).
  - Panel de calibración con top estrategias/temporalidades y gaps de datos.
- Frontend/UX:
  - Placeholders consistentes para campos opcionales y mensajes de estado.
  - Indicadores visuales de contribución por timeframe y por estrategia.

## Dependencias y Riesgos

- Datos externos:
  - Calidad y disponibilidad de OHLCV por símbolo/timeframe (Binance). Mitigación: paginación + detección y relleno de huecos.
- Cobertura QA:
  - Aumentar pruebas de integración y escenarios sintéticos. Mitigación: ampliar suites y publicar estado tras cada release.
- Sobreajuste:
  - Evitar calibración exclusiva in-sample. Mitigación: walk-forward y OOS por defecto en evaluaciones clave.

## Próxima Auditoría

- Fecha objetivo: dentro de 14 días hábiles a partir de la publicación de este documento.
- Hitos:
  - QA status actualizado (`docs/qa/status.md`) con suite completa verde.
  - Reporte de desempeño (`docs/reports/strategy_performance.md`) con snapshot comparativo (últimas 2 semanas).
  - Resultados de calibración MACD y OrderFlow por timeframe con notas de decisión.
- Responsables:
  - Datos/Sync: Responsable de datos
  - Estrategias/Calibración: Responsable de I+D
  - QA/Reporting: Responsable de QA

## Cómo verificar

- Ejecutar QA y publicar estado:
```
python -m pytest -q && python qa/generate_status.py
```
- Revisar timeframes y pesos: `docs/recommendation/timeframes.md`
- Revisar riesgo y buffers: `docs/recommendation/risk.md`
