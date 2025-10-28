# Black Trade - Quick Start Guide

## System Overview

Black Trade is a complete crypto trading recommendation system with:
- 5 trading strategies running on 4 timeframes
- Real-time data from Binance
- Backtesting and ranking system
- Web interface for recommendations and metrics

## Prerequisites

- Python 3.10+
- Node.js 18+
- Binance API credentials (optional for testing)

## Quick Start

### 1. Clone and Setup

```bash
cd Black_Trade
```

### 2. Backend Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your Binance credentials (optional for initial testing)
```

### 3. Frontend Setup

```bash
cd frontend
npm install
cd ..
```

### 4. Run the System

**Terminal 1 - Backend:**
```bash
uvicorn backend.app:app --reload --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

### 5. Access the Application

Open your browser to: **http://localhost:5173**

## First Steps

1. **Initial Data Download**: Click "Refresh" button on Dashboard
   - This downloads historical data from Binance (or uses mock data if no API credentials)
   - Runs backtests on all strategies
   - Generates trading recommendation

2. **View Recommendation**: 
   - See current BTC/USDT price
   - View recommended action (LONG/SHORT/FLAT)
   - Check entry range, stop loss, and take profit levels
   - Review confidence level

3. **Analyze Strategies**:
   - Switch to "Strategies" tab
   - Select timeframe (1h, 4h, 1d, 1w)
   - Review performance metrics for each strategy
   - See top-ranked strategy highlighted in green

## API Endpoints

- `GET /` - API status
- `POST /refresh` - Refresh data and run backtests
- `GET /recommendation` - Get current trading recommendation
- `GET /strategies` - Get all strategy metrics

## Features

### 5 Trading Strategies

1. **EMA_RSI** - EMA crossover with RSI filter (2% SL, 4% TP)
2. **Ichimoku_ADX** - Ichimoku cloud with ADX confirmation
3. **Breakout** - Volatility breakout with trailing stop
4. **Mean_Reversion** - Bollinger Bands + RSI
5. **Momentum** - MACD + RSI confirmation

### Metrics Calculated

- Win Rate
- Net PnL
- Max Drawdown
- Profit Factor
- Expectancy
- Composite Score (for ranking)

## Architecture

```
┌─────────────────┐
│   Frontend      │  React + Vite
│   (Port 5173)   │
└────────┬────────┘
         │ HTTP API
┌────────▼────────┐
│   Backend       │  FastAPI
│   (Port 8000)   │
└────────┬────────┘
         │
    ┌────┴────┬──────────┬────────────┐
    │         │          │            │
┌───▼───┐ ┌──▼──┐  ┌────▼────┐  ┌────▼─────┐
│ Binance│ │Data │  │Strategies│  │Backtest │
│ API   │ │Sync │  │(5 types)│  │ Engine  │
└───────┘ └─────┘  └─────────┘  └──────────┘
```

## Troubleshooting

### Backend won't start
- Check if port 8000 is available
- Ensure Python dependencies are installed: `pip install -r requirements.txt`
- Verify Binance credentials in `.env` (or leave default for testing)

### Frontend won't start
- Check if port 5173 is available
- Run `npm install` in the frontend directory
- Check Node.js version: `node --version` (should be 18+)

### No data showing
- Make sure backend is running first
- Click "Refresh" button to fetch data
- Check browser console for errors
- Verify backend is accessible at http://localhost:8000

## Next Steps

- Add more trading strategies
- Customize strategy parameters
- Add chart visualization
- Implement paper trading
- Add email/alerts for signals



