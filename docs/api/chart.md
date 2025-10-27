# Chart API Documentation

## Overview

The Chart API provides candle data with trading signals and levels for visualization. It integrates with the synchronization service to ensure data freshness and includes real-time trading signals from enabled strategies.

## Base URL

```
http://localhost:8000/api/chart
```

## Endpoints

### 1. Get Chart Data

**Endpoint:** `GET /chart/{symbol}/{timeframe}`

**Description:** Retrieves candle data with trading signals and levels for a specific symbol and timeframe.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `symbol` | string | Yes | Trading symbol (e.g., 'BTCUSDT') |
| `timeframe` | string | Yes | Timeframe (e.g., '1h', '4h', '1d') |
| `limit` | integer | No | Number of candles to return (1-1000, default: 100) |
| `include_signals` | boolean | No | Include trading signals (default: true) |
| `include_recommendation` | boolean | No | Include current recommendation (default: true) |

**Valid Timeframes:**
- `1m`, `3m`, `5m`, `15m`, `30m`
- `1h`, `2h`, `4h`, `6h`, `8h`, `12h`
- `1d`, `3d`, `1w`, `1M`

**Example Request:**
```bash
curl "http://localhost:8000/api/chart/BTCUSDT/1h?limit=200&include_signals=true"
```

**Response Schema:**

```json
{
  "symbol": "BTCUSDT",
  "timeframe": "1h",
  "candles": [
    {
      "timestamp": 1698768000000,
      "open": 50000.0,
      "high": 51000.0,
      "low": 49500.0,
      "close": 50500.0,
      "volume": 1234.56,
      "datetime": "2023-10-31T00:00:00"
    }
  ],
  "signals": [
    {
      "price": 50200.0,
      "level_type": "entry",
      "strategy": "EMA_RSI",
      "confidence": 0.85,
      "reason": "EMA Crossover BUY: Fast EMA (50100.0) > Slow EMA (49900.0), RSI (65.2) > 30"
    },
    {
      "price": 49800.0,
      "level_type": "stop_loss",
      "strategy": "EMA_RSI",
      "confidence": 0.85,
      "reason": "EMA_RSI SL"
    },
    {
      "price": 51200.0,
      "level_type": "take_profit",
      "strategy": "EMA_RSI",
      "confidence": 0.85,
      "reason": "EMA_RSI TP"
    }
  ],
  "current_price": 50500.0,
  "recommendation": {
    "action": "BUY",
    "confidence": 0.75,
    "entry_range": {
      "min": 50200.0,
      "max": 50800.0
    },
    "stop_loss": 49800.0,
    "take_profit": 51200.0,
    "current_price": 50500.0,
    "primary_strategy": "EMA_RSI",
    "risk_level": "MEDIUM"
  },
  "metadata": {
    "total_candles": 200,
    "date_range": {
      "start": "2023-10-31T00:00:00",
      "end": "2023-11-08T08:00:00"
    },
    "timeframe_minutes": 60,
    "data_freshness_hours": 0.5,
    "signals_count": 12
  }
}
```

**Response Fields:**

#### CandleData
| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | integer | Unix timestamp in milliseconds |
| `open` | float | Opening price |
| `high` | float | Highest price |
| `low` | float | Lowest price |
| `close` | float | Closing price |
| `volume` | float | Trading volume |
| `datetime` | string | ISO 8601 formatted datetime |

#### SignalLevel
| Field | Type | Description |
|-------|------|-------------|
| `price` | float | Price level |
| `level_type` | string | Type: 'entry', 'stop_loss', 'take_profit' |
| `strategy` | string | Strategy name that generated the signal |
| `confidence` | float | Signal confidence (0.0-1.0) |
| `reason` | string | Human-readable reason for the signal |

#### Metadata
| Field | Type | Description |
|-------|------|-------------|
| `total_candles` | integer | Number of candles returned |
| `date_range` | object | Start and end datetime of the data |
| `timeframe_minutes` | integer | Timeframe in minutes |
| `data_freshness_hours` | float | Hours since last data update |
| `signals_count` | integer | Number of signals generated |

### 2. Get Available Symbols

**Endpoint:** `GET /chart/symbols`

**Description:** Returns available trading symbols and timeframes.

**Example Request:**
```bash
curl "http://localhost:8000/api/chart/symbols"
```

**Response:**
```json
{
  "symbols": ["BTCUSDT", "ETHUSDT", "ADAUSDT", "DOTUSDT"],
  "timeframes": ["1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "8h", "12h", "1d", "3d", "1w", "1M"]
}
```

### 3. Get Chart Status

**Endpoint:** `GET /chart/status`

**Description:** Returns chart service status and data availability.

**Example Request:**
```bash
curl "http://localhost:8000/api/chart/status"
```

**Response:**
```json
{
  "service_status": "active",
  "available_data": {
    "1h": {
      "candles": 8789,
      "last_update": "2023-11-08T08:00:00",
      "freshness_hours": 0.5
    },
    "4h": {
      "candles": 2197,
      "last_update": "2023-11-08T08:00:00",
      "freshness_hours": 0.5
    },
    "1d": {
      "candles": 366,
      "last_update": "2023-11-07T00:00:00",
      "freshness_hours": 8.0
    },
    "1w": {
      "candles": 53,
      "last_update": "2023-11-05T00:00:00",
      "freshness_hours": 32.0
    }
  },
  "last_updated": "2023-11-08T08:00:00"
}
```

## Error Responses

### 400 Bad Request
```json
{
  "detail": "Invalid timeframe. Must be one of: ['1m', '3m', '5m', ...]"
}
```

### 404 Not Found
```json
{
  "detail": "No data available for BTCUSDT 1h. Please call /refresh first."
}
```

### 500 Internal Server Error
```json
{
  "detail": "Error generating chart data: [error message]"
}
```

## Usage Examples

### 1. Basic Chart Data
```javascript
// Fetch basic chart data
const response = await fetch('http://localhost:8000/api/chart/BTCUSDT/1h?limit=100');
const chartData = await response.json();

console.log(`Loaded ${chartData.candles.length} candles`);
console.log(`Current price: $${chartData.current_price}`);
console.log(`Found ${chartData.signals.length} signals`);
```

### 2. Chart with Signals Only
```javascript
// Fetch chart data with signals but no recommendation
const response = await fetch('http://localhost:8000/api/chart/BTCUSDT/4h?include_recommendation=false');
const chartData = await response.json();

// Process signals by type
const entrySignals = chartData.signals.filter(s => s.level_type === 'entry');
const stopLossSignals = chartData.signals.filter(s => s.level_type === 'stop_loss');
const takeProfitSignals = chartData.signals.filter(s => s.level_type === 'take_profit');
```

### 3. Multiple Timeframes
```javascript
// Fetch data for multiple timeframes
const timeframes = ['1h', '4h', '1d'];
const chartDataPromises = timeframes.map(tf => 
  fetch(`http://localhost:8000/api/chart/BTCUSDT/${tf}?limit=50`)
    .then(res => res.json())
);

const allChartData = await Promise.all(chartDataPromises);
```

### 4. Real-time Updates
```javascript
// Poll for updates every 5 minutes
setInterval(async () => {
  try {
    const response = await fetch('http://localhost:8000/api/chart/BTCUSDT/1h?limit=100');
    const chartData = await response.json();
    
    // Update chart with new data
    updateChart(chartData);
  } catch (error) {
    console.error('Failed to fetch chart data:', error);
  }
}, 5 * 60 * 1000); // 5 minutes
```

## Data Freshness

The API automatically checks data freshness and includes metadata about when the data was last updated. Fresh data is typically less than 2 hours old for most timeframes.

### Freshness Indicators

- **Fresh**: < 2 hours old
- **Stale**: 2-24 hours old  
- **Very Stale**: > 24 hours old

### Ensuring Fresh Data

1. **Call `/refresh` endpoint** before requesting chart data
2. **Check `data_freshness_hours`** in metadata
3. **Use `/chart/status`** to verify data availability

## Performance Considerations

### Caching
- Chart data is cached for 1 minute to improve performance
- Signals are generated on-demand for each request
- Historical data is loaded from CSV files

### Rate Limiting
- No rate limiting on chart endpoints
- Binance API rate limiting applies to data synchronization
- Consider caching for high-frequency requests

### Memory Usage
- Each candle uses ~100 bytes of memory
- 1000 candles ≈ 100KB of data
- Signals add ~50 bytes per signal
- Typical response size: 200-500KB

## Integration with Trading Strategies

The chart API integrates with all enabled trading strategies to provide:

1. **Entry Signals**: Price ranges for optimal entry
2. **Stop Loss Levels**: Risk management levels
3. **Take Profit Targets**: Profit-taking levels
4. **Confidence Scores**: Signal reliability (0.0-1.0)
5. **Strategy Attribution**: Which strategy generated each signal

### Strategy Integration

```python
# In your strategy implementation
def generate_signal(self, df: pd.DataFrame) -> Dict[str, Any]:
    # Your signal logic here
    return {
        "signal": 1,  # 1 for buy, -1 for sell, 0 for hold
        "strength": 0.85,
        "confidence": 0.75,
        "reason": "EMA crossover detected",
        "price": current_price
    }

def entry_range(self, df: pd.DataFrame, signal: int) -> Dict[str, float]:
    # Your entry range logic here
    return {
        "min": entry_min_price,
        "max": entry_max_price
    }

def risk_targets(self, df: pd.DataFrame, signal: int, current_price: float) -> Dict[str, float]:
    # Your risk management logic here
    return {
        "stop_loss": stop_loss_price,
        "take_profit": take_profit_price
    }
```

## Troubleshooting

### Common Issues

1. **No data available**
   - Call `/refresh` endpoint first
   - Check if symbol/timeframe is valid
   - Verify data files exist in `data/ohlcv/`

2. **Empty signals**
   - Ensure strategies are enabled in registry
   - Check strategy configuration
   - Verify data quality

3. **Stale data**
   - Call `/refresh` to update data
   - Check network connectivity to Binance
   - Verify sync service is running

4. **Performance issues**
   - Reduce `limit` parameter
   - Disable `include_signals` if not needed
   - Use appropriate timeframe for your use case

### Debug Mode

Enable debug logging to troubleshoot issues:

```bash
# Set environment variable
export LOG_LEVEL=DEBUG

# Restart the server
python -m uvicorn backend.app:app --reload --port 8000
```

## Security Considerations

- **No authentication required** for chart data (public data)
- **Rate limiting** should be implemented in production
- **Input validation** on all parameters
- **Error handling** to prevent information leakage
- **CORS enabled** for frontend integration

## Future Enhancements

1. **WebSocket support** for real-time updates
2. **Historical signal data** for backtesting
3. **Custom indicator overlays** (moving averages, etc.)
4. **Volume profile** integration
5. **Multi-symbol** chart support
6. **Export functionality** (CSV, JSON)
7. **Chart image generation** for reports
