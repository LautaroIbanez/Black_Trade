# Black Trade - Project Structure

## Directory Layout

```
Black_Trade/
├── backend/                    # FastAPI backend application
│   ├── __init__.py
│   └── app.py                 # Main FastAPI app with endpoints
│
├── data/                       # Data acquisition and management
│   ├── __init__.py
│   ├── binance_client.py      # Binance API client
│   └── sync_service.py        # Data sync and CSV management
│
├── strategies/                 # Trading strategies
│   ├── __init__.py
│   ├── strategy_base.py       # Abstract base strategy class
│   └── ema_rsi_strategy.py    # EMA + RSI strategy (implemented)
│
├── backtest/                   # Backtesting engine
│   ├── __init__.py
│   └── engine.py              # Backtest execution and ranking
│
├── recommendation/             # Legacy simple aggregator (disabled by default)
│   ├── __init__.py
│   └── aggregator.py          # Legacy simple aggregator (guarded by flag)
│
├── qa/                         # Quality assurance scripts
│
├── docs/                       # Documentation
│   ├── IMPLEMENTATION_STATUS.md
│   └── PROJECT_STRUCTURE.md
│
├── data/                       # Data files (created at runtime)
│   └── ohlcv/                 # OHLCV CSV files
│       ├── BTCUSDT_1h.csv
│       ├── BTCUSDT_4h.csv
│       ├── BTCUSDT_1d.csv
│       └── BTCUSDT_1w.csv
│
├── requirements.txt           # Python dependencies
├── .env.example              # Environment variables template
├── .env                       # Actual environment variables (create from .env.example)
└── README.md                  # Project overview
```

## Module Dependencies

```
backend/app.py
    ├── data/binance_client
    ├── data/sync_service
    ├── strategies/ema_rsi_strategy
    ├── backtest/engine
    └── backend/services/recommendation_service

backtest/engine.py
    └── strategies/strategy_base

backend/services/recommendation_service.py
    └── Aggregation, normalization, risk management

data/sync_service.py
    └── data/binance_client
```

## Key Components

### 1. Data Layer
**Purpose**: Fetch and manage OHLCV data from Binance

**Files**:
- `binance_client.py` - Authenticated Binance API wrapper
- `sync_service.py` - CSV persistence and data refresh

**Key Functions**:
- Download historical candles
- Refresh latest candles
- Validate current day data
- Persist to CSV files

### 2. Strategy Layer
**Purpose**: Implement trading strategies

**Files**:
- `strategy_base.py` - Abstract base class
- `ema_rsi_strategy.py` - EMA crossover + RSI filter

**Key Functions**:
- `generate_signals()` - Produce trading signals
- `generate_trades()` - Convert signals to trades
- `backtest()` - Run backtest with metrics

### 3. Backtest Engine
**Purpose**: Execute backtests and rank strategies

**Files**:
- `engine.py` - Backtest runner and ranking

**Key Functions**:
- `run_backtest()` - Execute strategy backtest
- `run_multiple_backtests()` - Test multiple strategies
- `rank_strategies()` - Calculate and rank by score

### 4. Recommendation System
**Purpose**: Aggregate strategies into trading recommendation

**Files**:
- `aggregator.py` - Signal aggregation

**Key Functions**:
- `generate_recommendation()` - Create final recommendation
- Calculate confidence, entry range, SL/TP

### 5. Backend API
**Purpose**: Expose REST API endpoints

**Files**:
- `app.py` - FastAPI application

**Endpoints**:
- `POST /refresh` - Refresh data and run backtests
- `GET /recommendation` - Get current recommendation
- `GET /strategies` - Get all strategy metrics

## Data Flow

```
1. User calls /refresh
   ↓
2. SyncService refreshes Binance data
   ↓
3. BacktestEngine runs strategies on data
   ↓
4. Strategies ranked by metrics
   ↓
5. Results cached in memory
   ↓
6. User calls /recommendation
   ↓
7. RecommendationAggregator combines top strategies
   ↓
8. Return recommendation with confidence and levels
```

## Configuration

All configuration via environment variables (`.env`):

```bash
BINANCE_API_KEY=your_key
BINANCE_API_SECRET=your_secret
TRADING_PAIRS=BTCUSDT
TIMEFRAMES=1h,4h,1d,1w
```

## Extension Points

### Adding a New Strategy

1. Create `strategies/your_strategy.py`
2. Inherit from `StrategyBase`
3. Implement `generate_signals()` and `generate_trades()`
4. Add to strategy list in `backend/app.py`

### Adding New Metrics

1. Modify `strategy_base.py` `_calculate_metrics()`
2. Update ranking logic in `backtest/engine.py`
3. Update API response models

### Adding New Timeframes

1. Update `TIMEFRAMES` in `.env`
2. No code changes needed (handled automatically)

## Testing Strategy

### Unit Tests (Recommended locations)
- `tests/unit/test_strategies.py` - Strategy logic
- `tests/unit/test_backtest_engine.py` - Backtest calculations
- `tests/unit/test_recommendation.py` - Aggregation logic

### Integration Tests
- `tests/integration/test_api.py` - API endpoints
- `tests/integration/test_data_sync.py` - Binance integration

### E2E Tests
- `tests/e2e/test_full_flow.py` - Complete user journey

## Performance Considerations

- CSV files used for data persistence (lightweight)
- In-memory caching of results (fast retrieval)
- Async FastAPI for concurrent requests
- Minimal external dependencies

## Security Notes

- API credentials stored in `.env` (never commit)
- CORS enabled for development
- No sensitive data exposed in logs
- Rate limiting recommended for production

