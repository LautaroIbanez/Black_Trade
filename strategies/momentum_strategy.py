"""Momentum Strategy with Multi-Timeframe Confirmation."""
import pandas as pd
import numpy as np
from typing import List, Dict
from strategies.strategy_base import StrategyBase


class MomentumStrategy(StrategyBase):
    """Momentum strategy with multi-timeframe confirmation."""
    
    def __init__(self, rsi_period: int = 14, macd_fast: int = 12, macd_slow: int = 26, macd_signal: int = 9, commission: float = 0.001, slippage: float = 0.0005):
        super().__init__("Momentum", {"rsi": rsi_period, "macd_fast": macd_fast, "macd_slow": macd_slow, "macd_signal": macd_signal}, commission, slippage)
        self.rsi_period = rsi_period
        self.macd_fast = macd_fast
        self.macd_slow = macd_slow
        self.macd_signal = macd_signal
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate momentum signals."""
        df = df.copy()
        df['rsi'] = self._calculate_rsi(df['close'], self.rsi_period)
        ema_fast = df['close'].ewm(span=self.macd_fast, adjust=False).mean()
        ema_slow = df['close'].ewm(span=self.macd_slow, adjust=False).mean()
        df['macd'] = ema_fast - ema_slow
        df['macd_signal'] = df['macd'].ewm(span=self.macd_signal, adjust=False).mean()
        df['signal'] = 0
        df.loc[(df['macd'] > df['macd_signal']) & (df['macd'].shift(1) <= df['macd_signal'].shift(1)) & (df['rsi'] > 50), 'signal'] = 1
        df.loc[(df['macd'] < df['macd_signal']) & (df['macd'].shift(1) >= df['macd_signal'].shift(1)) & (df['rsi'] < 50), 'signal'] = -1
        return df
    
    def generate_trades(self, df: pd.DataFrame) -> List[Dict]:
        """Generate trades from momentum signals."""
        trades = []
        position = None
        entry_price = 0
        entry_idx = 0
        for idx, row in df.iterrows():
            if position is None and row['signal'] != 0:
                position = {'side': 'long' if row['signal'] == 1 else 'short', 'entry_price': row['close'], 'entry_idx': idx, 'entry_time': row['timestamp']}
                entry_price = row['close']
                entry_idx = idx
            elif position and row['signal'] != 0:
                pnl = (row['close'] - entry_price) if position['side'] == 'long' else (entry_price - row['close'])
                trades.append({"entry_price": entry_price, "exit_price": row['close'], "side": position['side'], "pnl": pnl, "entry_time": position['entry_time'], "exit_time": row['timestamp']})
                position = {'side': 'long' if row['signal'] == 1 else 'short', 'entry_price': row['close'], 'entry_idx': idx, 'entry_time': row['timestamp']} if row['signal'] != 0 else None
                entry_price = row['close']
                entry_idx = idx
        
        # Close any remaining position at end of backtest
        if position:
            final_trade = self.close_all_positions(df, position, df.iloc[-1]['close'], len(df) - 1)
            if final_trade:
                trades.append(final_trade)
        
        return trades
    
    def _generate_signal_reason(self, df: pd.DataFrame, latest_row: pd.Series) -> str:
        """Generate specific reason for Momentum signal."""
        signal = self._convert_numpy_type(latest_row.get('signal', 0), int)
        rsi = self._convert_numpy_type(latest_row.get('rsi', 50), float)
        macd = self._convert_numpy_type(latest_row.get('macd', 0), float)
        macd_signal = self._convert_numpy_type(latest_row.get('macd_signal', 0), float)
        
        if signal == 1:
            return f"Momentum BUY: MACD ({macd:.4f}) > Signal ({macd_signal:.4f}), RSI ({rsi:.1f}) > 50"
        elif signal == -1:
            return f"Momentum SELL: MACD ({macd:.4f}) < Signal ({macd_signal:.4f}), RSI ({rsi:.1f}) < 50"
        else:
            return f"Waiting: MACD ({macd:.4f}) vs Signal ({macd_signal:.4f}), RSI ({rsi:.1f})"
    
    def entry_range(self, df: pd.DataFrame, signal: int) -> Dict[str, float]:
        """
        Calculate entry range for Momentum strategy based on MACD histogram and RSI momentum.
        Uses MACD histogram strength and RSI levels to determine optimal entry range.
        """
        if df.empty or signal == 0:
            current_price = float(df['close'].iloc[-1]) if not df.empty else 0.0
            return {"min": current_price, "max": current_price}
        
        current_price = float(df['close'].iloc[-1])
        
        # Calculate MACD for range calculation
        df_temp = df.copy()
        macd_line, signal_line, histogram = self._calculate_macd(df_temp['close'])
        df_temp['macd'] = macd_line
        df_temp['macd_signal'] = signal_line
        df_temp['macd_histogram'] = histogram
        
        current_macd = float(df_temp['macd'].iloc[-1])
        current_signal = float(df_temp['macd_signal'].iloc[-1])
        current_histogram = float(df_temp['macd_histogram'].iloc[-1])
        
        # Calculate RSI for momentum adjustment
        rsi = self._calculate_rsi(df_temp['close'], self.rsi_period)
        current_rsi = float(rsi.iloc[-1]) if not rsi.empty else 50.0
        
        # Base range from MACD histogram strength
        macd_strength = abs(current_histogram)
        
        # Adjust range based on RSI momentum
        if current_rsi > 80:  # Very overbought - tighter range
            rsi_multiplier = 0.3
        elif current_rsi < 20:  # Very oversold - wider range
            rsi_multiplier = 2.0
        elif current_rsi > 70:  # Overbought - tighter range
            rsi_multiplier = 0.6
        elif current_rsi < 30:  # Oversold - wider range
            rsi_multiplier = 1.4
        else:  # Normal range
            rsi_multiplier = 1.0
        
        # Calculate range buffer based on MACD strength and RSI
        range_buffer = macd_strength * rsi_multiplier * 0.1  # 10% of MACD strength
        
        # Ensure minimum range based on ATR
        atr = self._calculate_atr(df, 14)
        if not atr.empty:
            atr_value = float(atr.iloc[-1])
            min_range = atr_value * 0.15  # Minimum 15% of ATR
            range_buffer = max(range_buffer, min_range)
        
        # Additional adjustment based on MACD signal line distance
        macd_distance = abs(current_macd - current_signal)
        if macd_distance > 0:
            range_buffer = max(range_buffer, macd_distance * 0.2)
        
        if signal == 1:  # Buy signal - range around current price
            # For buy signals, prefer higher prices
            min_price = current_price - range_buffer * 0.5
            max_price = current_price + range_buffer * 1.5
        else:  # Sell signal
            # For sell signals, prefer lower prices
            min_price = current_price - range_buffer * 1.5
            max_price = current_price + range_buffer * 0.5
        
        return {
            "min": min_price,
            "max": max_price
        }
    
    def calculate_exit_levels(self, df: pd.DataFrame, signal: int, entry_price: float) -> Dict[str, float]:
        """
        Calculate explicit take profit and stop loss levels for Momentum strategy.
        Uses MACD histogram strength and RSI momentum to determine optimal exit points.
        """
        if df.empty or signal == 0:
            return {"stop_loss": entry_price, "take_profit": entry_price}
        
        # Calculate MACD for range calculation
        df_temp = df.copy()
        macd_line, signal_line, histogram = self._calculate_macd(df_temp['close'])
        df_temp['macd'] = macd_line
        df_temp['macd_signal'] = signal_line
        df_temp['macd_histogram'] = histogram
        
        current_macd = float(df_temp['macd'].iloc[-1])
        current_signal = float(df_temp['macd_signal'].iloc[-1])
        current_histogram = float(df_temp['macd_histogram'].iloc[-1])
        
        # Calculate RSI for momentum adjustment
        rsi = self._calculate_rsi(df_temp['close'], self.rsi_period)
        current_rsi = float(rsi.iloc[-1]) if not rsi.empty else 50.0
        
        # Calculate ATR for volatility
        atr = self._calculate_atr(df_temp, 14)
        atr_value = float(atr.iloc[-1]) if not atr.empty else entry_price * 0.02
        
        # Base range from MACD histogram strength
        macd_strength = abs(current_histogram)
        macd_distance = abs(current_macd - current_signal)
        
        # Adjust range based on RSI momentum
        if current_rsi > 80:  # Very overbought - tighter range
            rsi_multiplier = 0.3
        elif current_rsi < 20:  # Very oversold - wider range
            rsi_multiplier = 2.0
        elif current_rsi > 70:  # Overbought - tighter range
            rsi_multiplier = 0.6
        elif current_rsi < 30:  # Oversold - wider range
            rsi_multiplier = 1.4
        else:  # Normal range
            rsi_multiplier = 1.0
        
        # Adjust based on MACD distance
        distance_multiplier = min(macd_distance / entry_price, 0.05) / 0.02  # Cap at 5%
        distance_multiplier = max(distance_multiplier, 0.5)  # Minimum 0.5x
        
        # Combine adjustments
        volatility_multiplier = (rsi_multiplier + distance_multiplier) / 2
        
        # Calculate levels
        if signal == 1:  # Buy signal
            # Stop loss based on MACD signal line or ATR
            macd_stop = entry_price - (macd_distance * 0.5)  # Half MACD distance
            atr_stop = entry_price - (atr_value * 2.5)  # 2.5 ATR below
            stop_loss = max(macd_stop, atr_stop)
            
            # Take profit based on MACD strength or ATR
            macd_target = entry_price + (macd_strength * 2)  # 2x MACD strength
            atr_target = entry_price + (atr_value * 4)  # 4 ATR above
            take_profit = min(macd_target, atr_target)
            
        else:  # Sell signal
            # Stop loss based on MACD signal line or ATR
            macd_stop = entry_price + (macd_distance * 0.5)  # Half MACD distance
            atr_stop = entry_price + (atr_value * 2.5)  # 2.5 ATR above
            stop_loss = min(macd_stop, atr_stop)
            
            # Take profit based on MACD strength or ATR
            macd_target = entry_price - (macd_strength * 2)  # 2x MACD strength
            atr_target = entry_price - (atr_value * 4)  # 4 ATR below
            take_profit = max(macd_target, atr_target)
        
        # Apply volatility multiplier
        if signal == 1:
            stop_loss = entry_price - ((entry_price - stop_loss) * volatility_multiplier)
            take_profit = entry_price + ((take_profit - entry_price) * volatility_multiplier)
        else:
            stop_loss = entry_price + ((stop_loss - entry_price) * volatility_multiplier)
            take_profit = entry_price - ((entry_price - take_profit) * volatility_multiplier)
        
        return {
            "stop_loss": stop_loss,
            "take_profit": take_profit
        }
    
    def risk_targets(self, df: pd.DataFrame, signal: int, current_price: float) -> Dict[str, float]:
        """
        Calculate adaptive risk targets for Momentum strategy.
        Uses MACD histogram strength and RSI momentum to determine optimal stop loss and take profit.
        """
        if df.empty or signal == 0:
            return {"stop_loss": current_price, "take_profit": current_price}
        
        # Calculate MACD for momentum analysis
        df_temp = df.copy()
        macd_line, signal_line, histogram = self._calculate_macd(df_temp['close'])
        df_temp['macd'] = macd_line
        df_temp['macd_signal'] = signal_line
        df_temp['macd_histogram'] = histogram
        
        current_macd = float(df_temp['macd'].iloc[-1])
        current_signal = float(df_temp['macd_signal'].iloc[-1])
        current_histogram = float(df_temp['macd_histogram'].iloc[-1])
        
        # Calculate RSI for momentum adjustment
        rsi = self._calculate_rsi(df_temp['close'], self.rsi_period)
        current_rsi = float(rsi.iloc[-1]) if not rsi.empty else 50.0
        
        # Calculate ATR for volatility
        atr = self._calculate_atr(df_temp, 14)
        atr_value = float(atr.iloc[-1]) if not atr.empty else current_price * 0.02
        
        # Base risk levels
        base_stop_loss_pct = 0.025  # 2.5%
        base_take_profit_pct = 0.05  # 5%
        
        # Adjust based on MACD histogram strength
        macd_strength = abs(current_histogram)
        macd_multiplier = min(macd_strength / (current_price * 0.01), 2.0)  # Cap at 2x
        macd_multiplier = max(macd_multiplier, 0.5)  # Minimum 0.5x
        
        # Adjust based on RSI momentum
        if current_rsi > 85:  # Extreme overbought - very tight stops
            rsi_multiplier = 0.5
        elif current_rsi < 15:  # Extreme oversold - wider stops
            rsi_multiplier = 1.5
        elif current_rsi > 75:  # Overbought - tighter stops
            rsi_multiplier = 0.7
        elif current_rsi < 25:  # Oversold - wider stops
            rsi_multiplier = 1.3
        else:  # Normal range
            rsi_multiplier = 1.0
        
        # Adjust based on MACD signal line distance
        macd_distance = abs(current_macd - current_signal)
        distance_multiplier = min(macd_distance / (current_price * 0.01), 1.5)  # Cap at 1.5x
        distance_multiplier = max(distance_multiplier, 0.5)  # Minimum 0.5x
        
        # Combine adjustments
        volatility_multiplier = (macd_multiplier + rsi_multiplier + distance_multiplier) / 3
        
        # Calculate levels
        if signal == 1:  # Buy signal
            # Stop loss based on MACD signal line or ATR
            macd_stop = current_price - (macd_distance * 0.5)  # Half MACD distance
            atr_stop = current_price - (atr_value * 2.5)  # 2.5 ATR below
            stop_loss = max(macd_stop, atr_stop)
            
            # Take profit based on MACD strength or ATR
            macd_target = current_price + (macd_strength * 2)  # 2x MACD strength
            atr_target = current_price + (atr_value * 4)  # 4 ATR above
            take_profit = min(macd_target, atr_target)
            
        else:  # Sell signal
            # Stop loss based on MACD signal line or ATR
            macd_stop = current_price + (macd_distance * 0.5)  # Half MACD distance
            atr_stop = current_price + (atr_value * 2.5)  # 2.5 ATR above
            stop_loss = min(macd_stop, atr_stop)
            
            # Take profit based on MACD strength or ATR
            macd_target = current_price - (macd_strength * 2)  # 2x MACD strength
            atr_target = current_price - (atr_value * 4)  # 4 ATR below
            take_profit = max(macd_target, atr_target)
        
        # Apply volatility multiplier
        if signal == 1:
            stop_loss = current_price - ((current_price - stop_loss) * volatility_multiplier)
            take_profit = current_price + ((take_profit - current_price) * volatility_multiplier)
        else:
            stop_loss = current_price + ((stop_loss - current_price) * volatility_multiplier)
            take_profit = current_price - ((current_price - take_profit) * volatility_multiplier)
        
        return {
            "stop_loss": stop_loss,
            "take_profit": take_profit
        }
    
    def _calculate_rsi(self, prices: pd.Series, period: int) -> pd.Series:
        """Calculate RSI indicator."""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _calculate_macd(self, prices: pd.Series) -> tuple:
        """Calculate MACD indicator."""
        ema_12 = prices.ewm(span=12).mean()
        ema_26 = prices.ewm(span=26).mean()
        macd_line = ema_12 - ema_26
        signal_line = macd_line.ewm(span=9).mean()
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram


