# Procedimientos de Reporting para Stakeholders

## Generación de Reportes
1. Ejecutar backtests comparativos:
```bash
python backend/scripts/backtest_all.py --initial-capital 20000 --position-size-pct 0.15 --split 0.7
```
- Salida JSON: `docs/backtest_comparison_YYYYMMDD_HHMMSS.json`
- Resumen Markdown: `docs/strategy_reports.md`

2. Exportar recomendaciones y recalibraciones (live):
- `GET /recommendation?profile=balanced`
- `GET /api/monitoring/recalibration_logs?limit=500`

3. Compilar informe ejecutivo (Plantilla):
- Resumen de rendimiento (últimos N días)
- Cambios en estrategias/perfiles
- Riesgo actual (RR, riesgo %, drawdown reciente)
- Próximos pasos y tareas abiertas

## Distribución
- Carpeta compartida `docs/reports/` con versionado por fecha
- Envío por email/Slack con enlaces a:
  - Reporte Markdown
  - JSON de resultados
  - Capturas del dashboard

## Calendario
- Semanal: Informe de rendimiento y estabilidad
- Diario: Recalibración y estado del sistema (auto-generado)

## Checklists
- Datos actualizados y validados (sin huecos)
- Consistencia de métricas en dashboard y reportes
- Feature flags correctos (producción)
- Cambios documentados con impacto esperado


