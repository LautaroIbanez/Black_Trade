## End-to-end data → signals pipeline

This document describes the automated flow that keeps recommendations fresh without manual POST /refresh.

- Ingestion: `IngestionScheduler` starts `DataIngestionTask` (WS or polling). Incoming candles are batched by `backend/ingestion/processor.py` and saved via `OHLCVRepository`.
- Status/metrics: After a batch is saved, the processor updates `IngestionRepository` status and records latency/throughput metrics.
- Signal computation: The processor asynchronously triggers `SignalComputationService.compute_and_store()` with impacted timeframes. The service loads recent OHLCV from `MarketDataService`, runs `RecommendationService.generate_recommendation`, persists a JSON snapshot per timeframe in `live_recommendations` via `LiveResultsRepository`, and publishes the latest to an in-memory cache via `LiveRecommendationsService`.
- Availability: The `/recommendation` endpoint now reads from `LiveRecommendationsService`/DB and no longer requires `/refresh`. Frontend queries live endpoints (`/recommendation`, `/api/metrics`, `/api/risk/status`) and subscribes to WebSocket broadcasts for risk/alerts/orders. Backend has no dependency on CSV.
- Persistence: Live snapshots are stored in SQL (`live_recommendations`). Historical backtest results remain in `strategy_results`.
- Resilience: Signal computation has bounded retries with exponential backoff. Batch flush re-adds on transient failure. Observability alerts are emitted on repeated computation failures.
- Metrics: The system records ingestion latency/throughput and strategy generation times; OpenTelemetry exporters publish to the configured OTLP endpoint for Prometheus/Grafana via the collector. Dashboards should include: ingestion freshness, signal generation latency p50/p95/p99, order rejection rate, and risk breaches over time.

### Timeline (no manual refresh)

1. t0: Candle arrives via WS/polling → buffered
2. t0+≤1s: Batch flush → DB write (OHLCV)
3. t0+≤1.2s: Status/metrics updated (latency/throughput)
4. t0+≤2s: Async signal compute → `RecommendationService` → persist snapshot(s)
5. t0+≤2.5s: `/recommendation` serves the latest published snapshot; frontend sees updates on next poll; risk/events stream over WebSocket immediately

### Alerts

- High ingestion latency (p95 > threshold)
- Signal computation failures (repeated retries)
- Elevated order rejection rate
- Risk limit violations


