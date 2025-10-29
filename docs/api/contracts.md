# API Contracts Documentation

## Overview

This document defines the contracts and data structures for the Black Trade API endpoints, ensuring consistency between different services and frontend components.

## Recommendation Data Contract

### Unified Recommendation Structure

Both `/api/chart/{symbol}/{timeframe}` and `/recommendation` endpoints now return identical recommendation data structures to ensure consistency between the chart and card components.

### Core Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `action` | string | Trading action: "BUY", "SELL", "HOLD" | "SELL" |
| `confidence` | float | Confidence level (0.0 to 1.0) | 0.180 |
| `current_price` | float | Current market price | 112609.98 |
| `primary_strategy` | string | Name of the primary strategy | "Stochastic" |
| `risk_level` | string | Risk assessment: "LOW", "MEDIUM", "HIGH" | "LOW" |
| `signal_consensus` | float | Signal consensus strength | 1.068 |

### Entry and Exit Levels

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `entry_range` | object | Price range for entry | `{"min": 112277.02, "max": 114640.31}` |
| `stop_loss` | float | Stop loss price level | 123419.07 |
| `take_profit` | float | Take profit price level | 117975.64 |

### Strategy Information

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `supporting_strategies` | array | List of supporting strategy names | `["EMA_RSI", "MACD"]` |
| `strategy_details` | array | Detailed strategy information | See Strategy Details below |

### Strategy Details Structure

Each item in `strategy_details` contains:

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `strategy_name` | string | Strategy identifier | "EMA_RSI_Strategy" |
| `signal` | integer | Signal value: -1, 0, 1 | 1 |
| `strength` | float | Signal strength (0.0 to 1.0) | 0.75 |
| `confidence` | float | Strategy confidence (0.0 to 1.0) | 0.65 |
| `reason` | string | Signal reasoning | "EMA crossover with RSI confirmation" |
| `price` | float | Price at signal generation | 112609.98 |
| `timestamp` | string | Signal timestamp | "2025-10-28T21:00:00Z" |
| `timeframe` | string | Timeframe of the signal | "1h" |
| `entry_range` | object | Strategy-specific entry range | `{"min": 112000, "max": 113000}` |
| `risk_targets` | object | Strategy-specific risk levels | `{"stop_loss": 110000, "take_profit": 115000}` |

## Endpoint Specifications

### GET /api/chart/{symbol}/{timeframe}

**Purpose**: Retrieve chart data with trading signals and recommendation

**Parameters**:
- `symbol` (path): Trading symbol (e.g., "BTCUSDT")
- `timeframe` (path): Timeframe (e.g., "1h", "4h", "1d", "1w")
- `limit` (query, optional): Number of candles (1-1000, default: 100)
- `include_signals` (query, optional): Include trading signals (default: true)
- `include_recommendation` (query, optional): Include recommendation (default: true)

**Response Structure**:
```json
{
  "symbol": "BTCUSDT",
  "timeframe": "1h",
  "candles": [...],
  "signals": [...],
  "current_price": 112609.98,
  "recommendation": {
    "action": "SELL",
    "confidence": 0.180,
    "entry_range": {"min": 112277.02, "max": 114640.31},
    "stop_loss": 123419.07,
    "take_profit": 117975.64,
    "current_price": 112609.98,
    "primary_strategy": "Stochastic",
    "supporting_strategies": [...],
    "strategy_details": [...],
    "signal_consensus": 1.068,
    "risk_level": "LOW"
  },
  "metadata": {...}
}
```

### GET /recommendation

**Purpose**: Get current trading recommendation

**Parameters**: None

**Response Structure**:
```json
{
  "action": "SELL",
  "confidence": 0.180,
  "entry_range": {"min": 112277.02, "max": 114640.31},
  "stop_loss": 123419.07,
  "take_profit": 117975.64,
  "current_price": 112609.98,
  "primary_strategy": "Stochastic",
  "supporting_strategies": [...],
  "strategy_details": [...],
  "signal_consensus": 1.068,
  "risk_level": "LOW"
}
```

## Data Consistency Guarantees

### Unified Recommendation Generation

Both endpoints use the same recommendation generation logic:

1. **Data Source**: Both endpoints load the same multi-timeframe data
2. **Historical Metrics**: Both use the same `last_results` from backtest data
3. **Strategy Processing**: Both process the same enabled strategies
4. **Risk Management**: Both use the same risk management calculations

### Implementation Details

**Chart Endpoint**:
```python
# Uses unified recommendation generation
from backend.app import last_results
recommendation = recommendation_service.generate_recommendation(current_data, last_results)
```

**Recommendation Endpoint**:
```python
# Uses the same unified recommendation generation
recommendation = recommendation_service.generate_recommendation(current_data, last_results)
```

### Field Consistency

All fields in the recommendation object are guaranteed to be identical between endpoints:

- ✅ `action`: Same trading action
- ✅ `confidence`: Same confidence level
- ✅ `entry_range`: Same entry range boundaries
- ✅ `stop_loss`: Same stop loss level
- ✅ `take_profit`: Same take profit level
- ✅ `current_price`: Same current market price
- ✅ `primary_strategy`: Same primary strategy
- ✅ `supporting_strategies`: Same supporting strategies
- ✅ `strategy_details`: Same strategy details array
- ✅ `signal_consensus`: Same consensus strength
- ✅ `risk_level`: Same risk assessment

## Error Handling

### Common Error Responses

| Status Code | Error | Description |
|-------------|-------|-------------|
| 404 | "No results available. Please call /refresh first." | No backtest data available |
| 404 | "No data available for {symbol} {timeframe}" | No OHLCV data for symbol/timeframe |
| 400 | "Invalid timeframe" | Unsupported timeframe value |
| 500 | "Error generating recommendation" | Internal recommendation generation error |

### Error Response Format

```json
{
  "detail": "Error message description"
}
```

## Testing and Validation

### Integration Test

The `test_recommendation_unification.py` script validates that both endpoints return identical recommendation data:

```python
# Test both endpoints
chart_result = test_chart_recommendation()
rec_result = test_recommendation_endpoint()

# Compare all fields
for field in fields_to_compare:
    assert chart_result[field] == rec_result[field]
```

### Validation Checklist

- [ ] All recommendation fields match between endpoints
- [ ] Entry range boundaries are identical
- [ ] Stop loss and take profit levels match
- [ ] Confidence levels are identical
- [ ] Strategy details arrays have same length and content
- [ ] Current price is the same
- [ ] Signal consensus values match

## Frontend Integration

### Chart Component

The `SignalChart` component receives recommendation data from `/api/chart/{symbol}/{timeframe}` and displays:

- Entry range as a colored band
- Stop loss as a dashed line
- Take profit as a dashed line
- Current price as a highlighted line
- Recommendation details in the info panel

### Card Component

The `Dashboard` component receives recommendation data from `/recommendation` and displays:

- Action badge (BUY/SELL/HOLD)
- Confidence percentage
- Entry range values
- Stop loss and take profit levels
- Strategy information
- Risk level indicator

### Data Synchronization

Both components now receive identical data structures, ensuring:

- Consistent visual representation
- Synchronized level displays
- Unified user experience
- No discrepancies between chart and card

## Future Considerations

### Performance Optimization

- Consider caching recommendation data to avoid recalculation
- Implement incremental updates for real-time data
- Add data versioning for change detection

### Extensibility

- New recommendation fields should be added to both endpoints
- Strategy details structure should remain backward compatible
- Error handling should be consistent across endpoints

### Monitoring

- Track recommendation generation performance
- Monitor data consistency between endpoints
- Alert on field mismatches in production

## Conclusion

The unified recommendation contract ensures that both the chart and card components display identical trading levels and recommendations, providing a consistent and reliable user experience. All fields are guaranteed to match between endpoints, eliminating any potential confusion or discrepancies in the trading interface.

