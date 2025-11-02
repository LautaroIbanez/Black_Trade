# Metodología: Señales, Métricas y Gestión de Riesgo

## Señales y Consenso
- Generación por estrategia y timeframe con `strategy_details`: `signal` (-1/0/1), `strength`, `confidence`.
- Ponderación por perfil temporal (Day Trading, Swing, Balanced, Long Term).
- Neutral handling: los HOLD pesan menos cuando hay señales activas.
- `signal_consensus` normalizado 0-1 y con sesgo hacia señales activas.

## Métricas Clave
- Confianza final (0-1) con boost acotado por ranking histórico por timeframe.
- Pesos normalizados (suman 1.0) en `strategy_details.weight`.
- `risk_reward_ratio`, `risk_percentage`, `entry_label`.
- Curva de capital y rendimiento % en backtests (`equity_curve`, `total_return_pct`, `max_drawdown_pct`).

## Gestión de Riesgo
- SL/TP agregados vía `RiskManagementService`:
  - Medición de ATR(14) y mínimos por perfil: SL >= k·ATR; TP con RR mínimo por perfil.
  - Ajustes por soporte/resistencia (niveles cercanos y evitación de solapes).
  - Validación final fuera del rango de entrada.
- Perfiles de riesgo (por defecto):
  - Day Trading: SL = 1.0×ATR, RR ≥ 1.5, riesgo 0.5% del capital
  - Balanced: SL = 1.2×ATR, RR ≥ 1.8, riesgo 1.0%
  - Swing: SL = 1.5×ATR, RR ≥ 2.0, riesgo 1.5%
  - Long Term: SL = 2.0×ATR, RR ≥ 2.5, riesgo 2.0%
- Tamaño de posición:
  - Unidades = (capital × %riesgo) / |precio − SL|
  - `position_size_units` y `position_notional` expuestos en respuesta

## Detección de Régimen
- `RegimeDetector` (EMA-Keltner):
  - Trending si el cierre rompe bandas Keltner; si no, ranging.
  - Activación condicional de estrategias (trend vs mean-reversion) por timeframe.

## Flujo de Decisión (“Esperar” vs “Entrar”)
1. Evaluar `action` y `entry_label`.
2. Confirmar RR ≥ mínimo del perfil y `risk_percentage` ≤ umbral.
3. Verificar que el precio esté dentro/near del rango de entrada.
4. Revisar régimen: preferir estrategias activas acorde al régimen.
5. Si no se cumplen (precio desalineado, RR insuficiente, riesgo alto): “Esperar”.

## Ejemplo Resumido de Recomendación
```json
{
  "action": "BUY",
  "confidence": 0.72,
  "entry_range": {"min": 49500.0, "max": 50500.0},
  "stop_loss": 48050.0,
  "take_profit": 52020.0,
  "risk_reward_ratio": 1.95,
  "risk_percentage": 1.1,
  "entry_label": "Entrada favorable - Precio en la parte baja del rango",
  "position_size_units": 52.4,
  "position_notional": 2620000.0,
  "signal_consensus": 0.84
}
```




