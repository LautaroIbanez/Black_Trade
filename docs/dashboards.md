# Dashboards: Señales, Resultados y Riesgo

## Objetivos
- Visualizar históricos de señales y consensos por timeframe
- Reportar resultados (backtests y live) con métricas clave
- Exponer riesgo: SL/TP, RR, tamaño de posición, drawdown

## Vistas Propuestas
1) Señales y Consenso (por timeframe)
   - Timeline de señales por estrategia
   - Consensus y confianza
   - Régimen (trending/ranging)
2) Gestión de Operación
   - Rango de entrada, SL/TP agregados
   - RR, tamaño de posición sugerido, riesgo%
   - Desglose de contribuciones
3) Rendimiento
   - Curva de capital (backtest/live)
   - Total return %, max drawdown %, profit factor
   - Tabla de trades (top/bottom)
4) Monitoreo y Alertas
   - Recalibration logs
   - Alertas por desviación de confianza vs score histórico

## Fuentes de Datos
- Backtests: `backend/scripts/backtest_all.py` resultados JSON + docs
- Live: Endpoints `GET /recommendation`, `GET /api/monitoring/recalibration_logs`
- Estrategias: `GET /strategies` y `GET /strategies/info`

## Integración Técnica
- Frontend: ampliar `MonitoringDashboard` o crear `PerformanceDashboard`
- Polling interval recomendado: 30–60s para live; cargar bajo demanda backtests
- Caching básico en frontend para métricas agregadas

## KPIs Clave
- Señales: consenso, confianza, participación de estrategias
- Risk: RR, riesgo %, sum(weights) = 1.0
- Rendimiento: total_return_pct, max_drawdown_pct, win_rate, profit_factor

## Roadmap
- v1: Lectura de logs + recomendaciones actuales
- v2: Tabla de señales históricas y filtros por timeframe
- v3: Gráficos de equity (backtest vs live) y comparativa por perfil





