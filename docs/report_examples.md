# Ejemplos de Reportes y Flujos de Decisión

## Reporte Post-Backtest (Resumen)
```markdown
# BTCUSDT 4H – Enero–Marzo
- Total Return %: +18.4%
- Max Drawdown %: -6.9%
- Win Rate: 54.2%
- Profit Factor: 1.63
- Avg Trade RR: 1.85
- Regimen predominante: Trending (64%) / Ranging (36%)

Top Estrategias:
1) IchimokuTrend (score 0.78)
2) Momentum (score 0.74)
3) MeanReversion (score 0.62) – activo en ranging
```

## Recomendación Operativa (Ejemplo)
```markdown
Acción: BUY
Confianza: 72%
Rango de entrada: 49,500 – 50,500
SL: 48,050 (≈ 1.1% riesgo)
TP: 52,020 (RR ≈ 1.95)
Regimen: Trending
Justificación: Momentum + Ichimoku, consenso 0.84, precio cercano a parte baja del rango de entrada
Ejecución: Tamaño ≈ 52.4 unidades (1% riesgo capital)
```

## Flujo “Esperar” vs “Entrar”
```
¿Precio dentro del rango de entrada?
  No → Esperar pullback/corrección (según entry_label)
  Sí → RR ≥ mínimo de perfil y riesgo% ≤ umbral de perfil?
       No → Ajustar o esperar
       Sí → ¿Régimen compatible con estrategias activas?
             No → Esperar confirmación de régimen
             Sí → Entrar
```

## Reporte de Recalibración Diario (Extracto)
```json
{
  "timestamp": "2025-10-29T12:00:00Z",
  "profile": "balanced",
  "recommendation": {"action": "HOLD", "confidence": 0.31},
  "timeframes_involved": ["1h","4h","1d"],
  "metrics": {"avg_score": 0.66, "consensus": 0.58}
}
```

## Anexos
- Tablas de señales por timeframe (últimas 24–72h)
- Gráficos: Curva de capital, distribución de retornos, drawdown
- Lista de cambios (versionado de estrategias y perfiles)

