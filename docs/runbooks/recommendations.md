# Runbook: Recommendation Tracking and Metrics

## Summary

This document describes the recommendation tracking workflow, how outcomes are recorded, and how hit ratio metrics are calculated and displayed in dashboards.

## Workflow Overview

### 1. Accept/Reject Recommendation

When a trader receives a recommendation:

```bash
POST /api/recommendation-tracking/accept
```

Payload:
```json
{
  "recommendation_id": 123,
  "checklist": {
    "pre_trade": [
      {"key": "liquidity_check", "label": "Liquidity OK", "checked": true, "required": true},
      {"key": "risk_limits", "label": "Within risk limits", "checked": true, "required": true}
    ]
  },
  "notes": "Good entry opportunity"
}
```

**Database Action**: Creates or updates a record in `recommendations_log` with `status='accepted'`.

**Metrics**: Increments `system_recommendation_accepted` counter.

---

### 2. Record Outcome Post-Trade

After closing a position from an accepted recommendation:

```bash
POST /api/recommendation-tracking/outcome
```

Payload:
```json
{
  "recommendation_id": 123,
  "outcome": "win",
  "realized_pnl": 250.50,
  "notes": "TP hit at 48000"
}
```

Valid `outcome` values:
- `win`: Position closed profitably
- `loss`: Position closed at a loss
- `breakeven`: Position closed at breakeven or minimal P/L

**Database Action**: Updates the record with `outcome`, `realized_pnl`, and `decided_at=now()`.

**Metrics**: Increments `system_recommendation_win` or `system_recommendation_loss` based on outcome.

---

### 3. Query Metrics

Retrieve aggregated statistics:

```bash
GET /api/recommendation-tracking/metrics?days=30
```

Response:
```json
{
  "total_decisions": 150,
  "accepted": 100,
  "rejected": 50,
  "accepted_rate": 0.666,
  "tracked_outcomes": 85,
  "wins": 55,
  "losses": 28,
  "hit_ratio": 0.647,
  "total_realized_pnl": 1250.75
}
```

---

## Database Schema

### recommendations_log Table

| Column | Type | Description |
|--------|------|-------------|
| `id` | SERIAL | Primary key |
| `status` | VARCHAR(20) | `suggested`, `accepted`, `rejected` |
| `user_id` | VARCHAR(100) | Trader identifier (nullable) |
| `symbol` | VARCHAR(50) | Trading pair (indexed) |
| `timeframe` | VARCHAR(20) | Chart timeframe (indexed) |
| `confidence` | VARCHAR(20) | Confidence level |
| `risk_level` | VARCHAR(20) | Risk categorization |
| `payload` | JSONB | Full recommendation snapshot |
| `checklist` | JSONB | Pre/post-trade checklist |
| `notes` | VARCHAR(1000) | Trader notes |
| `outcome` | VARCHAR(20) | `win`, `loss`, `breakeven` (nullable) |
| `realized_pnl` | NUMERIC(20,8) | Actual profit/loss (nullable) |
| `decided_at` | TIMESTAMPTZ | Outcome timestamp (nullable) |
| `created_at` | TIMESTAMPTZ | Record creation (indexed) |
| `updated_at` | TIMESTAMPTZ | Last update (indexed) |

---

## Metrics Calculation

### Hit Ratio

```
hit_ratio = wins / tracked_outcomes
```

Where:
- `wins`: Count of `outcome='win'`
- `tracked_outcomes`: Count of accepted recommendations with non-null `outcome`

**Interpretation**: Higher hit ratio (closer to 1.0) indicates better recommendation quality.

### Accepted Rate

```
accepted_rate = accepted / total_decisions
```

Where:
- `accepted`: Count of `status='accepted'`
- `total_decisions`: Count of `status IN ('accepted', 'rejected')`

**Interpretation**: Measure of trader trust in recommendations.

---

## Observability Integration

### Metrics Collector

The `MetricsCollector` records:
- `system_recommendation_accepted`: Counter of acceptances
- `system_recommendation_rejected`: Counter of rejections
- `system_recommendation_win`: Counter of wins
- `system_recommendation_loss`: Counter of losses

Retrieve via:
```python
from backend.observability.metrics import get_metrics_collector

collector = get_metrics_collector()
recommendation_metrics = collector.get_recommendation_metrics()
# Returns: {'system_recommendation_accepted': 100, ...}
```

### Dashboard Panels

**Grafana Dashboard: Recommendation Performance**

Panels:
1. Hit Ratio (Gauge) - Target > 0.55
2. Accepted Rate (Time series)
3. Total Realized P&L (Single stat)
4. Wins vs Losses (Bar chart)
5. Average Realized P&L (Time series)
6. Outcomes by Symbol (Pie chart)

**PromQL Example**:
```promql
# Hit ratio calculation from counters
rate(system_recommendation_win_total[5m]) / 
  (rate(system_recommendation_win_total[5m]) + rate(system_recommendation_loss_total[5m]))
```

---

## Alerts

### Low Hit Ratio Alert

**Trigger**: Hit ratio < 0.4 over last 100 tracked outcomes

**Action**: 
1. Notify risk team via Slack/PagerDuty
2. Review recent recommendations and market conditions
3. Consider pausing auto-orders (if enabled)
4. Investigate strategy calibration issues

**Resolution**: 
- Check for data quality issues
- Review recent regime changes
- Validate stop loss/take profit levels
- Consider recalibration

---

### High Rejection Rate Alert

**Trigger**: Accepted rate < 0.3 over last 50 decisions

**Action**:
1. Review recent recommendations with traders
2. Check if recommendations align with current risk appetite
3. Validate risk limits and sizing calculations
4. Consider strategy parameter adjustment

---

## Troubleshooting

### Missing Outcomes

**Symptom**: `tracked_outcomes < accepted`

**Cause**: Traders forgetting to record outcomes post-trade

**Resolution**: 
- Implement reminder notifications
- Create periodic reconciliation jobs
- Add UI prompts for outstanding outcomes

### Inconsistent Metrics

**Symptom**: Database metrics ≠ MetricsCollector counters

**Cause**: Metrics collector is in-memory; metrics lost on restart

**Resolution**:
- Database is source of truth for historical metrics
- MetricsCollector only tracks real-time counters
- Sync on application start if needed

### Performance Issues

**Symptom**: Slow queries on `recommendations_log` table

**Cause**: Missing indexes or large table size

**Resolution**:
- Ensure indexes on `status`, `user_id`, `symbol`, `timeframe`, `created_at`
- Implement table partitioning by date if data > 1M rows
- Add archived table for old records (> 1 year)

---

## API Integration Examples

### Python Client

```python
import requests

# Accept recommendation
response = requests.post(
    'http://api.black-trade.com/api/recommendation-tracking/accept',
    headers={'Authorization': f'Bearer {token}'},
    json={
        'recommendation_id': 123,
        'checklist': {'pre_trade': [...]},
        'notes': 'Good opportunity'
    }
)

# Record outcome
response = requests.post(
    'http://api.black-trade.com/api/recommendation-tracking/outcome',
    headers={'Authorization': f'Bearer {token}'},
    json={
        'recommendation_id': 123,
        'outcome': 'win',
        'realized_pnl': 250.50,
        'notes': 'TP hit'
    }
)

# Query metrics
metrics = requests.get(
    'http://api.black-trade.com/api/recommendation-tracking/metrics?days=30',
    headers={'Authorization': f'Bearer {token}'}
).json()
print(f"Hit ratio: {metrics['hit_ratio']:.2%}")
```

### Frontend Integration

```javascript
// Accept recommendation
await fetch('/api/recommendation-tracking/accept', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    recommendation_id: recommendationId,
    checklist: checklistData,
    notes: notesText
  })
});

// Record outcome
await fetch('/api/recommendation-tracking/outcome', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    recommendation_id: recommendationId,
    outcome: 'win',
    realized_pnl: realizedPnL,
    notes: outcomeNotes
  })
});

// Display metrics
const metrics = await fetch('/api/recommendation-tracking/metrics?days=30', {
  headers: { 'Authorization': `Bearer ${token}` }
}).then(r => r.json());
```

---

## References

- [API Documentation](../api/normalization.md)
- [Observability Setup](../OBSERVABILITY_SETUP.md)
- [Dashboard Configuration](./dashboards.md)
- [Incident Response](./incident_response.md)

