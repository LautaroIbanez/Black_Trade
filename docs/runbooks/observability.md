## Observability Runbook

Purpose: Diagnose and resolve issues with pipeline freshness, latency, hit ratio, and risk alerts.

### Dashboards
- Ingestion Freshness: p95 latency, last candle timestamps per TF.
- Signal Generation: generation time p50/p95/p99, last recommendation timestamp.
- Recommendations: accepted vs. rejected counts, hit ratio (wins / decided), realized PnL.
- Risk: exposure %, drawdowns, VaR.

### Alerts
- Stale recommendations (> 10 min without live snapshot).
- Low hit ratio (last 100 < 0.4).
- High risk breaches (drawdown/VAR).

### Triage Steps
1) Check `/api/health` and logs for ingestion errors.
2) Verify `live_recommendations` has recent rows; if not, inspect `MessageProcessor` and `SignalComputationService`.
3) Review scheduler jobs running in `backend/tasks/scheduler.py`.
4) For low hit ratio, sample recent `recommendations_log` and compare entry/SL/TP against market data.

### Escalation
- If recommendations stale > 30 min, page on-call; attach logs from ingestion and signal services.
- If hit ratio < 0.3 over last 300, freeze auto-orders (if enabled) and notify risk.


