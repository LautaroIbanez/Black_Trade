# Strategy Development Guide

This document provides comprehensive guidelines for extending the `StrategyBase` class and implementing new trading strategies in the Black Trade system.

## Available Strategies

The Black Trade system includes a comprehensive catalog of trading strategies optimized for different timeframes and market conditions:

### Core Strategies

1. **EMA RSI Strategy** (`EMARSIStrategy`)
   - **Fast Variant**: 8/21 EMAs, optimized for scalping (1m-5m)
   - **Standard Variant**: 12/26 EMAs, for intraday trading (1h-4h)
   - **Swing Variant**: 21/50 EMAs, for daily timeframes
   - Uses RSI for momentum confirmation and signal persistence

2. **Momentum Strategy** (`MomentumStrategy`)
   - **Fast Variant**: 8/17/6 MACD, 9-period RSI
   - **Standard Variant**: 12/26/9 MACD, 14-period RSI
   - **Swing Variant**: 19/39/15 MACD, 21-period RSI
   - Combines MACD and RSI for momentum detection

3. **Breakout Strategy** (`BreakoutStrategy`)
   - **Short-term**: 10-period lookback, 1.5x BB standard deviation
   - **Standard**: 20-period lookback, 2.0x BB standard deviation
   - **Long-term**: 50-period lookback, 2.5x BB standard deviation
   - Volatility-based breakout detection with trailing stops

4. **Mean Reversion Strategy** (`MeanReversionStrategy`)
   - **Fast Variant**: 10-period BB, 9-period RSI
   - **Standard Variant**: 20-period BB, 14-period RSI
   - **Swing Variant**: 50-period BB, 21-period RSI
   - Bollinger Bands with RSI confirmation

5. **Ichimoku Strategy** (`IchimokuStrategy`)
   - **Fast Variant**: 5/13/26 periods, 9-period ADX
   - **Standard Variant**: 9/26/52 periods, 14-period ADX
   - **Swing Variant**: 18/52/104 periods, 21-period ADX
   - Cloud analysis with ADX trend strength confirmation

### Advanced Strategies

6. **Bollinger Breakout Strategy** (`BollingerBreakoutStrategy`)
   - Volume-confirmed breakouts from Bollinger Bands
   - RSI momentum confirmation
   - Dynamic volatility-based exit levels

7. **Ichimoku Trend Strategy** (`IchimokuTrendStrategy`)
   - Pure trend-following using Ichimoku cloud analysis
   - Trend strength and cloud thickness filters
   - Cloud color and position analysis

8. **RSI Divergence Strategy** (`RSIDivergenceStrategy`)
   - Detects price/RSI divergences for reversal signals
   - Volume confirmation for signal strength
   - Configurable divergence sensitivity

9. **MACD Crossover Strategy** (`MACDCrossoverStrategy`)
   - MACD line and signal line crossovers
   - Histogram momentum confirmation
   - Zero-line cross detection (optional)

10. **Stochastic Oscillator Strategy** (`StochasticStrategy`)
    - %K and %D line crossovers
    - Divergence detection between price and stochastic
    - Overbought/oversold level analysis

### Strategy Configuration

All strategies are configured through `backend/config/strategies.json` with:
- **Parameter variants** for different timeframes
- **Commission and slippage** settings
- **Enable/disable** functionality
- **Strategy descriptions** and use cases

### Timeframe Optimization

Strategies are optimized for specific timeframes:
- **Scalping (1m-5m)**: Fast parameters, tight stops, high frequency
- **Intraday (1h-4h)**: Standard parameters, balanced risk/reward
- **Swing (Daily)**: Longer periods, wider stops, trend-following

## Table of Contents

1. [StrategyBase Overview](#strategybase-overview)
2. [Creating a New Strategy](#creating-a-new-strategy)
3. [Available Hooks and Methods](#available-hooks-and-methods)
4. [Cost Management](#cost-management)
5. [Position Management](#position-management)
6. [Best Practices](#best-practices)
7. [Testing Strategies](#testing-strategies)
8. [Examples](#examples)

## StrategyBase Overview

The `StrategyBase` class is the abstract base class for all trading strategies. It provides:

- **Cost Management**: Built-in commission and slippage calculation
- **Position Closing**: Automatic position closing at end of backtest
- **Metrics Calculation**: Comprehensive performance metrics
- **Hooks**: Extensible methods for custom behavior

### Key Features

- **Parameterized Costs**: Configurable commission and slippage rates
- **Automatic Position Closing**: Ensures no open positions at backtest end
- **Net PnL Calculation**: Accounts for trading costs in performance metrics
- **Extensible Design**: Easy to add new strategies and features

## Creating a New Strategy

### Basic Structure

```python
from strategies.strategy_base import StrategyBase
import pandas as pd
from typing import List, Dict

class MyStrategy(StrategyBase):
    """My custom trading strategy."""
    
    def __init__(self, param1: int = 10, param2: float = 0.5, 
                 commission: float = 0.001, slippage: float = 0.0005):
        super().__init__("MyStrategy", {"param1": param1, "param2": param2}, 
                        commission, slippage)
        self.param1 = param1
        self.param2 = param2
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate trading signals from price data."""
        # Implementation here
        pass
    
    def generate_trades(self, df: pd.DataFrame) -> List[Dict]:
        """Generate trade list from signals."""
        # Implementation here
        pass
```

### Required Methods

#### `generate_signals(self, df: pd.DataFrame) -> pd.DataFrame`

This method should:
- Take OHLCV data as input
- Calculate technical indicators
- Generate buy/sell signals (1 for buy, -1 for sell, 0 for no signal)
- Return the dataframe with signal column added

**Example:**
```python
def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    # Calculate indicators
    df['sma_20'] = df['close'].rolling(window=20).mean()
    df['sma_50'] = df['close'].rolling(window=50).mean()
    
    # Generate signals
    df['signal'] = 0
    df.loc[df['sma_20'] > df['sma_50'], 'signal'] = 1
    df.loc[df['sma_20'] < df['sma_50'], 'signal'] = -1
    
    return df
```

#### `generate_trades(self, df: pd.DataFrame) -> List[Dict]`

This method should:
- Process signals to create actual trades
- Handle position management (entry/exit logic)
- Apply stop losses, take profits, etc.
- Return a list of trade dictionaries
- **IMPORTANT**: Close any remaining positions at the end

**Example:**
```python
def generate_trades(self, df: pd.DataFrame) -> List[Dict]:
    trades = []
    position = None
    entry_price = 0
    entry_idx = 0
    
    for idx, row in df.iterrows():
        if position is None and row['signal'] != 0:
            # Open new position
            position = {
                'side': 'long' if row['signal'] == 1 else 'short',
                'entry_price': row['close'],
                'entry_idx': idx,
                'entry_time': row['timestamp']
            }
            entry_price = row['close']
            entry_idx = idx
        elif position and row['signal'] != 0:
            # Close current position and open new one
            pnl = (row['close'] - entry_price) if position['side'] == 'long' else (entry_price - row['close'])
            trades.append({
                "entry_price": entry_price,
                "exit_price": row['close'],
                "side": position['side'],
                "pnl": pnl,
                "entry_time": position['entry_time'],
                "exit_time": row['timestamp']
            })
            position = {
                'side': 'long' if row['signal'] == 1 else 'short',
                'entry_price': row['close'],
                'entry_idx': idx,
                'entry_time': row['timestamp']
            }
            entry_price = row['close']
            entry_idx = idx
    
    # Close any remaining position at end of backtest
    if position:
        final_trade = self.close_all_positions(df, position, df.iloc[-1]['close'], len(df) - 1)
        if final_trade:
            trades.append(final_trade)
    
    return trades
```

## Available Hooks and Methods

### Position Management Hooks

#### `close_all_positions(self, df: pd.DataFrame, current_position: Optional[Dict], current_price: float, current_idx: int) -> Optional[Dict]`

**Purpose**: Close any remaining positions at the end of backtest.

**Parameters**:
- `df`: The dataframe with price data
- `current_position`: Current open position (None if no position)
- `current_price`: Current market price
- `current_idx`: Current row index

**Returns**: Trade dictionary if position was closed, None otherwise

**Default Behavior**: Closes position at current price with `forced_close: True` flag.

**Override When**: You need custom logic for closing positions (e.g., different exit conditions).

### Cost Management Methods

#### `calculate_trade_costs(self, entry_price: float, exit_price: float, side: str) -> float`

**Purpose**: Calculate total trading costs for a trade.

**Parameters**:
- `entry_price`: Entry price of the trade
- `exit_price`: Exit price of the trade
- `side`: 'long' or 'short'

**Returns**: Total cost amount

**Formula**: `(commission * trade_value * 2) + (slippage * trade_value * 2)`

#### `apply_costs_to_pnl(self, trade: Dict) -> Dict`

**Purpose**: Apply trading costs to a trade dictionary.

**Parameters**:
- `trade`: Trade dictionary with entry_price, exit_price, side, pnl

**Returns**: Updated trade dictionary with costs and net_pnl

**Adds**:
- `costs`: Total cost amount
- `net_pnl`: PnL after costs

### Metrics Methods

#### `_calculate_metrics(self, trades: List[Dict], df: pd.DataFrame) -> Dict[str, Any]`

**Purpose**: Calculate comprehensive performance metrics.

**Returns**:
- `total_trades`: Number of trades
- `winning_trades`: Number of winning trades
- `losing_trades`: Number of losing trades
- `win_rate`: Percentage of winning trades
- `net_pnl`: Net profit/loss after costs
- `gross_profit`: Total profit from winning trades
- `gross_loss`: Total loss from losing trades
- `max_drawdown`: Maximum drawdown
- `profit_factor`: Gross profit / gross loss
- `expectancy`: Expected value per trade
- `total_costs`: Total trading costs

## Cost Management

### Setting Costs

```python
# Default costs (0.1% commission, 0.05% slippage)
strategy = MyStrategy()

# Custom costs
strategy = MyStrategy(commission=0.002, slippage=0.001)

# No costs
strategy = MyStrategy(commission=0.0, slippage=0.0)
```

### Cost Calculation

Costs are automatically applied to all trades during backtesting. The system:

1. Calculates costs for each trade using `calculate_trade_costs()`
2. Applies costs using `apply_costs_to_pnl()`
3. Uses `net_pnl` for all performance calculations
4. Reports `total_costs` in metrics

## Position Management

### Position Structure

When managing positions, use this structure:

```python
position = {
    'side': 'long' or 'short',
    'entry_price': float,
    'entry_idx': int,
    'entry_time': timestamp
}
```

### Critical Requirements

1. **Always close positions**: Use `close_all_positions()` hook at end of backtest
2. **Track position state**: Maintain position dictionary throughout trade loop
3. **Handle signal changes**: Close current position before opening new one
4. **Use proper data types**: Ensure prices and indices are correct types

## Best Practices

### 1. Signal Generation

- **Use vectorized operations**: Leverage pandas for performance
- **Handle NaN values**: Clean data before signal generation
- **Avoid look-ahead bias**: Don't use future data for current signals
- **Validate signals**: Ensure signals are -1, 0, or 1

### 2. Trade Generation

- **Consistent position tracking**: Use the position dictionary structure
- **Proper PnL calculation**: Account for long/short differences
- **Include timestamps**: Add entry_time and exit_time to trades
- **Handle edge cases**: Empty data, no signals, etc.

### 3. Performance

- **Minimize loops**: Use pandas operations when possible
- **Efficient indicators**: Cache calculated indicators
- **Memory management**: Don't store unnecessary data

### 4. Testing

- **Unit tests**: Test individual methods
- **Integration tests**: Test full backtest flow
- **Edge cases**: Test with empty data, extreme values
- **Cost validation**: Verify cost calculations

## Testing Strategies

### Unit Testing

```python
import unittest
from strategies.my_strategy import MyStrategy

class TestMyStrategy(unittest.TestCase):
    def setUp(self):
        self.strategy = MyStrategy()
        self.sample_data = create_sample_data()
    
    def test_signal_generation(self):
        signals = self.strategy.generate_signals(self.sample_data)
        self.assertIn('signal', signals.columns)
        self.assertTrue(signals['signal'].isin([-1, 0, 1]).all())
    
    def test_trade_generation(self):
        signals = self.strategy.generate_signals(self.sample_data)
        trades = self.strategy.generate_trades(signals)
        self.assertIsInstance(trades, list)
        # Verify all positions are closed
        # Check trade structure
```

### Integration Testing

```python
def test_full_backtest(self):
    strategy = MyStrategy(commission=0.001, slippage=0.0005)
    metrics = strategy.backtest(self.sample_data)
    
    self.assertIn('total_trades', metrics)
    self.assertIn('net_pnl', metrics)
    self.assertIn('total_costs', metrics)
    self.assertGreaterEqual(metrics['total_costs'], 0)
```

## Examples

### Simple Moving Average Crossover

```python
class SMACrossoverStrategy(StrategyBase):
    def __init__(self, fast_period=10, slow_period=20, **kwargs):
        super().__init__("SMA_Crossover", 
                        {"fast": fast_period, "slow": slow_period}, **kwargs)
        self.fast_period = fast_period
        self.slow_period = slow_period
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df['sma_fast'] = df['close'].rolling(window=self.fast_period).mean()
        df['sma_slow'] = df['close'].rolling(window=self.slow_period).mean()
        
        df['signal'] = 0
        df.loc[df['sma_fast'] > df['sma_slow'], 'signal'] = 1
        df.loc[df['sma_fast'] < df['sma_slow'], 'signal'] = -1
        
        return df
    
    def generate_trades(self, df: pd.DataFrame) -> List[Dict]:
        trades = []
        position = None
        entry_price = 0
        entry_idx = 0
        
        for idx, row in df.iterrows():
            if position is None and row['signal'] != 0:
                position = {
                    'side': 'long' if row['signal'] == 1 else 'short',
                    'entry_price': row['close'],
                    'entry_idx': idx,
                    'entry_time': row['timestamp']
                }
                entry_price = row['close']
                entry_idx = idx
            elif position and row['signal'] != 0:
                pnl = (row['close'] - entry_price) if position['side'] == 'long' else (entry_price - row['close'])
                trades.append({
                    "entry_price": entry_price,
                    "exit_price": row['close'],
                    "side": position['side'],
                    "pnl": pnl,
                    "entry_time": position['entry_time'],
                    "exit_time": row['timestamp']
                })
                position = {
                    'side': 'long' if row['signal'] == 1 else 'short',
                    'entry_price': row['close'],
                    'entry_idx': idx,
                    'entry_time': row['timestamp']
                }
                entry_price = row['close']
                entry_idx = idx
        
        # Close any remaining position
        if position:
            final_trade = self.close_all_positions(df, position, df.iloc[-1]['close'], len(df) - 1)
            if final_trade:
                trades.append(final_trade)
        
        return trades
```

### RSI Mean Reversion

```python
class RSIMeanReversionStrategy(StrategyBase):
    def __init__(self, rsi_period=14, oversold=30, overbought=70, **kwargs):
        super().__init__("RSI_MeanReversion", 
                        {"rsi_period": rsi_period, "oversold": oversold, "overbought": overbought}, **kwargs)
        self.rsi_period = rsi_period
        self.oversold = oversold
        self.overbought = overbought
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df['rsi'] = self._calculate_rsi(df['close'], self.rsi_period)
        
        df['signal'] = 0
        df.loc[df['rsi'] < self.oversold, 'signal'] = 1
        df.loc[df['rsi'] > self.overbought, 'signal'] = -1
        
        return df
    
    def generate_trades(self, df: pd.DataFrame) -> List[Dict]:
        trades = []
        position = None
        entry_price = 0
        entry_idx = 0
        
        for idx, row in df.iterrows():
            if position is None and row['signal'] != 0:
                position = {
                    'side': 'long' if row['signal'] == 1 else 'short',
                    'entry_price': row['close'],
                    'entry_idx': idx,
                    'entry_time': row['timestamp']
                }
                entry_price = row['close']
                entry_idx = idx
            elif position:
                # Close position when RSI returns to neutral
                if (position['side'] == 'long' and row['rsi'] > 50) or \
                   (position['side'] == 'short' and row['rsi'] < 50):
                    pnl = (row['close'] - entry_price) if position['side'] == 'long' else (entry_price - row['close'])
                    trades.append({
                        "entry_price": entry_price,
                        "exit_price": row['close'],
                        "side": position['side'],
                        "pnl": pnl,
                        "entry_time": position['entry_time'],
                        "exit_time": row['timestamp']
                    })
                    position = None
        
        # Close any remaining position
        if position:
            final_trade = self.close_all_positions(df, position, df.iloc[-1]['close'], len(df) - 1)
            if final_trade:
                trades.append(final_trade)
        
        return trades
    
    def _calculate_rsi(self, prices: pd.Series, period: int) -> pd.Series:
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
```

## Conclusion

This guide provides the foundation for creating robust, well-tested trading strategies. Remember to:

1. Always close positions at the end of backtests
2. Use the provided cost management system
3. Test thoroughly with various market conditions
4. Follow the established patterns for consistency
5. Document your strategy's logic and parameters

For questions or contributions, please refer to the project's main documentation or contact the development team.

## CryptoRotation y OrderFlow (Activadas)

- Habilitadas en el registro con parámetros por defecto conservadores.
- Generan trades reales: entrada en señal activa, salida en señal opuesta (OrderFlow también sale cuando volumen se normaliza), cierre forzado al final.
- Costos aplicados a cada trade (commission + slippage).

### Escenarios de backtest

```python
from backtest.scenarios.rotation_orderflow import run_rotation_scenario, run_orderflow_scenario
print(run_rotation_scenario("BTCUSDT", "1h"))
print(run_orderflow_scenario("BTCUSDT", "1h"))
```

Los escenarios leen `data/ohlcv/{SYMBOL}_{TF}.csv` y reportan `total_trades`, `win_rate`, `net_pnl`, `max_drawdown`, `profit_factor`, `expectancy`.