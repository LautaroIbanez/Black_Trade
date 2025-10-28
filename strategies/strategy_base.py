"""Base strategy class for all trading strategies."""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import pandas as pd


class StrategyBase(ABC):
    """Abstract base class for trading strategies."""
    
    def __init__(self, name: str, params: Dict[str, Any] = None, commission: float = 0.0002, slippage: float = 0.0001):
        """Initialize strategy with name, parameters, and trading costs."""
        self.name = name
        self.params = params or {}
        self.commission = commission  # Commission as percentage (0.0002 = 0.02%)
        self.slippage = slippage  # Slippage as percentage (0.0001 = 0.01%)
    
    @abstractmethod
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate trading signals from price data."""
        pass
    
    @abstractmethod
    def generate_trades(self, df: pd.DataFrame) -> List[Dict]:
        """Generate trade list from signals."""
        pass
    
    @abstractmethod
    def calculate_exit_levels(self, df: pd.DataFrame, signal: int, entry_price: float) -> Dict[str, float]:
        """
        Calculate explicit take profit and stop loss levels for a trade.
        This method must be implemented by each strategy to define clear exit rules.
        
        Args:
            df: DataFrame with OHLCV data and indicators
            signal: Signal value (-1, 0, 1)
            entry_price: Price at which the trade was entered
            
        Returns:
            Dict with 'take_profit' and 'stop_loss' levels
        """
        pass
    
    def generate_signal(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Generate current signal from the latest candle data."""
        if df.empty:
            return {
                "signal": 0,
                "strength": 0.0,
                "confidence": 0.0,
                "reason": "No data available",
                "timestamp": None
            }
        
        # Get signals for the entire dataframe
        signals_df = self.generate_signals(df)
        
        # Get the latest signal
        latest_row = signals_df.iloc[-1]
        signal_value = latest_row.get('signal', 0)
        
        # Get signal strength from the strategy (if available)
        strength = latest_row.get('strength', 0.0)
        if strength == 0.0 and signal_value != 0:
            # Fallback: use absolute signal value as strength
            strength = abs(signal_value)
        
        # Calculate confidence based on signal consistency and strength
        recent_signals = signals_df['signal'].tail(5)  # Last 5 periods
        if len(recent_signals) > 1:
            # Base confidence from signal strength
            base_confidence = strength
            
            # Boost confidence for signal consistency
            signal_consistency = (recent_signals == signal_value).sum() / len(recent_signals)
            consistency_boost = 1.0 + (signal_consistency * 0.5)  # Up to 50% boost
            
            # Boost confidence for active signals vs neutrals
            active_boost = 1.5 if signal_value != 0 else 0.8
            
            confidence = min(base_confidence * consistency_boost * active_boost, 1.0)
        else:
            # For single signals, use strength with active signal boost
            active_boost = 1.5 if signal_value != 0 else 0.8
            confidence = min(strength * active_boost, 1.0)
        
        # Ensure minimum confidence for active signals
        if signal_value != 0 and confidence < 0.1:
            confidence = 0.1
        
        # Generate reason for the signal
        reason = self._generate_signal_reason(signals_df, latest_row)
        
        # Convert timestamp and price to Python types
        timestamp = latest_row.get('timestamp')
        if hasattr(timestamp, 'item'):  # numpy scalar
            timestamp = timestamp.item()
        
        price = latest_row.get('close', 0)
        if hasattr(price, 'item'):  # numpy scalar
            price = float(price.item())
        else:
            price = float(price)
        
        return {
            "signal": int(signal_value),  # Convert to Python int
            "strength": float(strength),  # Convert to Python float
            "confidence": float(confidence),  # Convert to Python float
            "reason": reason,
            "timestamp": timestamp,
            "price": price
        }
    
    def _convert_numpy_type(self, value, target_type):
        """Convert numpy types to Python types."""
        if hasattr(value, 'item'):  # numpy scalar
            return target_type(value.item())
        else:
            return target_type(value)
    
    def entry_range(self, df: pd.DataFrame, signal: int) -> Dict[str, float]:
        """
        Calculate dynamic entry range based on strategy-specific indicators and volatility.
        Override in subclasses for strategy-specific logic.
        
        Args:
            df: DataFrame with OHLCV data and indicators
            signal: Signal value (-1, 0, 1)
            
        Returns:
            Dict with 'min' and 'max' entry prices
        """
        if df.empty:
            return {"min": 0.0, "max": 0.0}
        if signal == 0:
            # Neutral signal: derive a non-degenerate range from recent volatility
            current_price = float(df['close'].iloc[-1])
            atr = self._calculate_atr(df, 14)
            atr_value = float(atr.iloc[-1]) if not atr.empty else 0.0
            # Use close-to-close standard deviation as secondary measure
            close_returns = df['close'].pct_change().rolling(window=20).std()
            std_value = float(close_returns.iloc[-1]) if not close_returns.empty and pd.notna(close_returns.iloc[-1]) else 0.0
            # Convert std of returns to price volatility estimate
            std_price = current_price * std_value
            # Combine signals: take a blended buffer ensuring a reasonable floor
            base_buffer = 0.0
            if atr_value > 0 and std_price > 0:
                base_buffer = 0.25 * atr_value + 0.75 * std_price
            elif atr_value > 0:
                base_buffer = 0.5 * atr_value
            elif std_price > 0:
                base_buffer = std_price
            else:
                base_buffer = max(current_price * 0.002, 1e-6)  # 0.2% fallback
            # Produce asymmetric but bounded range around price
            lower = max(0.0, current_price - base_buffer * 0.9)
            upper = current_price + base_buffer * 1.1
            # Ensure non-degenerate ordering
            if upper <= lower:
                upper = lower + max(current_price * 0.001, 1e-6)
            return {"min": lower, "max": upper}
        
        current_price = float(df['close'].iloc[-1])
        
        # Default implementation using ATR for volatility-based range
        atr = self._calculate_atr(df, 14)
        if not atr.empty:
            atr_value = float(atr.iloc[-1])
            # Use 0.5 * ATR as range buffer
            range_buffer = atr_value * 0.5
        else:
            # Fallback to 0.5% of current price
            range_buffer = current_price * 0.005
        
        if signal == 1:  # Buy signal
            return {
                "min": current_price - range_buffer,
                "max": current_price + range_buffer
            }
        else:  # Sell signal
            return {
                "min": current_price - range_buffer,
                "max": current_price + range_buffer
            }
    
    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Average True Range for volatility measurement."""
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift())
        low_close = abs(df['low'] - df['close'].shift())
        
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = true_range.rolling(window=period).mean()
        return atr
    
    def risk_targets(self, df: pd.DataFrame, signal: int, current_price: float) -> Dict[str, float]:
        """
        Calculate adaptive stop loss and take profit levels based on volatility and market conditions.
        This method delegates to calculate_exit_levels for strategy-specific implementation.
        
        Args:
            df: DataFrame with OHLCV data and indicators
            signal: Signal value (-1, 0, 1)
            current_price: Current market price
            
        Returns:
            Dict with 'stop_loss' and 'take_profit' levels
        """
        if df.empty or signal == 0:
            return {"stop_loss": current_price, "take_profit": current_price}
        
        # Use strategy-specific exit level calculation
        return self.calculate_exit_levels(df, signal, current_price)
    
    def _default_exit_levels(self, df: pd.DataFrame, signal: int, current_price: float) -> Dict[str, float]:
        """
        Default implementation for exit levels using ATR-based volatility.
        Used as fallback when strategies don't override calculate_exit_levels.
        Ensures SL/TP are always outside entry range for neutral signals.
        """
        # Calculate ATR for volatility-based levels
        atr = self._calculate_atr(df, 14)
        atr_value = float(atr.iloc[-1]) if not atr.empty else current_price * 0.02
        
        # Base risk levels - ensure minimum distance from entry range
        base_stop_loss_pct = 0.02  # 2%
        base_take_profit_pct = 0.04  # 4%
        
        # Adjust based on ATR volatility
        volatility_multiplier = min(atr_value / current_price, 0.05) / 0.02  # Cap at 5%
        volatility_multiplier = max(volatility_multiplier, 0.5)  # Minimum 0.5x
        
        # For neutral signals, use wider ranges to ensure clear separation
        if signal == 0:
            # Neutral signals get wider, symmetric ranges
            base_stop_loss_pct = 0.03  # 3% for neutral
            base_take_profit_pct = 0.06  # 6% for neutral
            volatility_multiplier = max(volatility_multiplier, 1.0)  # At least 1x for neutral
        
        # Calculate levels
        if signal == 1:  # Buy signal
            stop_loss = current_price * (1 - base_stop_loss_pct * volatility_multiplier)
            take_profit = current_price * (1 + base_take_profit_pct * volatility_multiplier)
        elif signal == -1:  # Sell signal
            stop_loss = current_price * (1 + base_stop_loss_pct * volatility_multiplier)
            take_profit = current_price * (1 - base_take_profit_pct * volatility_multiplier)
        else:  # Neutral signal - create symmetric levels
            stop_loss = current_price * (1 - base_stop_loss_pct * volatility_multiplier)
            take_profit = current_price * (1 + base_take_profit_pct * volatility_multiplier)
        
        return {
            "stop_loss": stop_loss,
            "take_profit": take_profit
        }
    
    def _generate_signal_reason(self, df: pd.DataFrame, latest_row: pd.Series) -> str:
        """Generate human-readable reason for the signal. Override in subclasses for custom reasons."""
        signal = self._convert_numpy_type(latest_row.get('signal', 0), int)
        
        if signal == 1:
            return "Buy signal generated"
        elif signal == -1:
            return "Sell signal generated"
        else:
            return "No signal - waiting for conditions"
    
    def close_all_positions(self, df: pd.DataFrame, current_position: Optional[Dict], current_price: float, current_idx: int) -> Optional[Dict]:
        """Hook to close all positions at end of backtest. Override if needed."""
        if current_position:
            pnl = (current_price - current_position['entry_price']) if current_position['side'] == 'long' else (current_position['entry_price'] - current_price)
            trade = {
                "entry_price": current_position['entry_price'],
                "exit_price": current_price,
                "side": current_position['side'],
                "pnl": pnl,
                "entry_time": current_position['entry_time'],
                "exit_time": df.loc[current_idx, 'timestamp'],
                "forced_close": True
            }
            return trade
        return None
    
    def calculate_trade_costs(self, entry_price: float, exit_price: float, side: str) -> float:
        """Calculate total trading costs (commission + slippage) for a trade."""
        # Calculate costs based on actual trade value
        entry_cost = entry_price * (self.commission + self.slippage)
        exit_cost = exit_price * (self.commission + self.slippage)
        return entry_cost + exit_cost
    
    def apply_costs_to_pnl(self, trade: Dict) -> Dict:
        """Apply trading costs to trade PnL."""
        if 'entry_price' in trade and 'exit_price' in trade:
            costs = self.calculate_trade_costs(trade['entry_price'], trade['exit_price'], trade.get('side', 'long'))
            trade['costs'] = costs
            trade['net_pnl'] = trade.get('pnl', 0) - costs
        return trade
    
    def backtest(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Run backtest and return metrics."""
        signals_df = self.generate_signals(df)
        trades = self.generate_trades(signals_df)
        
        # Apply costs to all trades
        trades = [self.apply_costs_to_pnl(trade) for trade in trades]
        
        return self._calculate_metrics(trades, df)
    
    def _calculate_metrics(self, trades: List[Dict], df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate backtest metrics from trades."""
        if not trades:
            return {
                "total_trades": 0,
                "win_rate": 0.0,
                "net_pnl": 0.0,
                "max_drawdown": 0.0,
                "profit_factor": 0.0,
                "expectancy": 0.0,
                "total_costs": 0.0
            }
        
        # Use net_pnl if available, otherwise fall back to pnl
        winning_trades = [t for t in trades if t.get('net_pnl', t.get('pnl', 0)) > 0]
        losing_trades = [t for t in trades if t.get('net_pnl', t.get('pnl', 0)) < 0]
        
        total_trades = len(trades)
        win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0
        net_pnl = sum(t.get('net_pnl', t.get('pnl', 0)) for t in trades)
        total_costs = sum(t.get('costs', 0) for t in trades)
        
        gross_profit = sum(t.get('net_pnl', t.get('pnl', 0)) for t in winning_trades)
        gross_loss = abs(sum(t.get('net_pnl', t.get('pnl', 0)) for t in losing_trades))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        
        avg_win = gross_profit / len(winning_trades) if winning_trades else 0
        avg_loss = gross_loss / len(losing_trades) if losing_trades else 0
        expectancy = (win_rate * avg_win) - ((1 - win_rate) * avg_loss)
        
        # Calculate max drawdown
        cumulative_pnl = 0
        peak = 0
        max_drawdown = 0
        
        for trade in trades:
            trade_pnl = trade.get('net_pnl', trade.get('pnl', 0))
            cumulative_pnl += trade_pnl
            if cumulative_pnl > peak:
                peak = cumulative_pnl
            drawdown = peak - cumulative_pnl
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        return {
            "total_trades": total_trades,
            "winning_trades": len(winning_trades),
            "losing_trades": len(losing_trades),
            "win_rate": win_rate,
            "net_pnl": net_pnl,
            "gross_profit": gross_profit,
            "gross_loss": gross_loss,
            "max_drawdown": max_drawdown,
            "profit_factor": profit_factor,
            "expectancy": expectancy,
            "total_costs": total_costs
        }

