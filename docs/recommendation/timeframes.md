# Timeframe Contribution and Weights

Este documento detalla cómo contribuye cada timeframe al consenso y a la confianza final.

## Pesos por Perfil

- balanced:
  - 15m: 0.3
  - 1h: 0.5
  - 2h: 0.6
  - 4h: 0.7
  - 12h: 0.8
  - 1d: 0.9
  - 1w: 1.0
- day_trading:
  - 15m: 0.9
  - 1h: 1.0
  - 2h: 0.9
  - 4h: 0.8
  - 12h: 0.5
  - 1d: 0.4
  - 1w: 0.2
- swing:
  - 15m: 0.2
  - 1h: 0.6
  - 2h: 0.8
  - 4h: 1.0
  - 12h: 0.9
  - 1d: 0.9
  - 1w: 0.3
- long_term:
  - 15m: 0.1
  - 1h: 0.2
  - 2h: 0.4
  - 4h: 0.4
  - 12h: 0.7
  - 1d: 0.8
  - 1w: 1.0

## Cómo influye en el scoring
- En `RecommendationService`, cada señal incorpora `timeframe_weight` al calcular `signal.confidence` y `signal.strength` (se multiplica por el peso del timeframe del perfil activo).
- La agregación final normaliza los pesos por estrategia (confidence × score) para formar `strategy_details.weight` y comprueba que la suma ≈ 1.0.
- `signal_consensus` refleja la proporción de señales por tipo (BUY/SELL/HOLD) sin pre-boosts y se acota a [0,1].

## Verificación
- Pruebas de integración validan que las temporalidades `15m`, `2h` y `12h` aparecen en `strategy_details` y que los pesos normalizados suman ~1.0 (`tests/recommendation/test_endpoints.py`).
