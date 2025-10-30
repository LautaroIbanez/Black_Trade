# Strategy Performance Report

This document describes how to review strategy performance telemetry and generate periodic reports.

## Telemetry Sources
- Backtesting (engine): logs key metrics per strategy/timeframe
  - trades, win_rate, max_drawdown_pct, total_return_pct
  - Alerts on low trades, low/high unusual win-rate (configurable via env)
- Live aggregation: logs action, confidence, consensus, primary strategy, supporting count

## How to Enable and View Logs
- Python logging is configured by the backend app; ensure log level INFO.
- Run backtests or the API and tail logs:
```bash
# Backtests via /refresh
uvicorn backend.app:app --reload --port 8000
# In another terminal, tail logs or view console output
```

## Environment Thresholds
- MIN_TRADES_ALERT (default 1)
- MIN_WINRATE_ALERT (default 0.1)
- MAX_WINRATE_ALERT (default 0.95)

## Periodic Report (Manual)
- Collect last N runs' logs and summarize by strategy/timeframe:
  - Total trades, win rate, max drawdown, total return
  - Alerts raised
- Save snapshot into this document with date/time.

## Example Snapshot
```
Date: 2025-10-30 12:00
- Momentum 1h: trades=28, win_rate=0.57, max_dd=0.12, total_return=0.18
- MACD 4h: trades=12, win_rate=0.51, max_dd=0.09, total_return=0.07
Alerts:
- None
```
