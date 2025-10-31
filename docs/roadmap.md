# Roadmap y Calendario de Auditoría

Este documento establece los hitos próximos y un calendario de auditoría dependiente de completar las correcciones y calibraciones vigentes.

## Dependencias Previas

- MACD: calibración por timeframe tras habilitar cierres por histograma en cero
- CryptoRotation: universo multi-activo (`ROTATION_UNIVERSE`) y ranking por fuerza relativa
- OrderFlow: ajuste de `vol_mult` por régimen de volatilidad
- QA: ampliación de pruebas de integración/regresión y publicación en `docs/qa/status.md`

## Hitos Pendientes Clave

- Normalización de confianza y consenso: asegurar que la confianza agregada no supere la media ni la señal más débil
- Rehabilitación de MACD: confirmar actividad con dataset controlado y Win-Rate > 0%
- Activación multi-símbolo: rotación efectiva de capital con métricas por símbolo y universo configurable

## Calendario de Auditoría (Tentativo)

Semana 1–2:
- Finalizar calibración inicial MACD (8/17/6 y 12/26/9) por 1h/4h/1d
- Ajustar `vol_mult` de OrderFlow con validación OOS
- Publicar `docs/reports/strategy_performance.md` con baseline comparativo

Semana 3:
- Auditoría interna QA: suite completa verde, reporte firmado en `docs/qa/status.md`
- Verificación de datos: continuidad/frescura por símbolo/timeframe

Semana 4:
- Auditoría externa (si aplica) con snapshot de backtests y evidencias QA
- Cierre de hallazgos y actualización de `docs/release_notes.md`

## Criterios de Salida por Hito

- Win-rate y profit factor consistentes entre runs (±5%)
- Max drawdown acotado y estable según perfil de riesgo
- Estrategias sin señales espurias en datasets de control
- QA: >90% de escenarios prioritarios cubiertos y verdes

## Publicaciones y Transparencia

- Estado QA actualizado tras cada release menor
- Resultados de backtests con parámetros y seeds fijados para reproducibilidad
- Documentación de supuestos y límites en cada estrategia (`docs/strategies/*.md`)


