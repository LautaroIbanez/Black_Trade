"""Volatility Breakout with Trailing Stop Strategy."""
import pandas as pd
import numpy as np
from typing import List, Dict
from strategies.strategy_base import StrategyBase


class BreakoutStrategy(StrategyBase):
    """Volatility breakout with trailing stop strategy."""
    
    def __init__(self, lookback: int = 20, multiplier: float = 2.0, trailing_percent: float = 0.01, commission: float = 0.001, slippage: float = 0.0005):
        super().__init__("Breakout", {"lookback": lookback, "multiplier": multiplier, "trailing": trailing_percent}, commission, slippage)
        self.lookback = lookback
        self.multiplier = multiplier
        self.trailing_percent = trailing_percent
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate breakout signals."""
        df = df.copy()
        df['high_max'] = df['high'].rolling(window=self.lookback).max()
        df['low_min'] = df['low'].rolling(window=self.lookback).min()
        df['atr'] = self._calculate_atr(df, 14)
        df['upper_band'] = df['close'].rolling(window=self.lookback).mean() + (self.multiplier * df['atr'])
        df['lower_band'] = df['close'].rolling(window=self.lookback).mean() - (self.multiplier * df['atr'])
        df['signal'] = 0
        df.loc[df['close'] > df['upper_band'], 'signal'] = 1
        df.loc[df['close'] < df['lower_band'], 'signal'] = -1
        return df
    
    def generate_trades(self, df: pd.DataFrame) -> List[Dict]:
        """Generate trades with trailing stop."""
        trades = []
        position = None
        entry_price = 0
        entry_idx = 0
        trailing_stop = 0
        for idx, row in df.iterrows():
            if position is None and row['signal'] != 0:
                position = {'side': 'long' if row['signal'] == 1 else 'short', 'entry_price': row['close'], 'entry_idx': idx, 'entry_time': row['timestamp']}
                entry_price = row['close']
                entry_idx = idx
                trailing_stop = entry_price * (1 - self.trailing_percent) if position['side'] == 'long' else entry_price * (1 + self.trailing_percent)
            elif position and position['side'] == 'long':
                if row['low'] <= trailing_stop:
                    pnl = trailing_stop - entry_price
                    trades.append({"entry_price": entry_price, "exit_price": trailing_stop, "side": position['side'], "pnl": pnl, "entry_time": position['entry_time'], "exit_time": row['timestamp']})
                    position = None
                else:
                    new_stop = row['close'] * (1 - self.trailing_percent)
                    trailing_stop = max(trailing_stop, new_stop)
            elif position and position['side'] == 'short':
                if row['high'] >= trailing_stop:
                    pnl = entry_price - trailing_stop
                    trades.append({"entry_price": entry_price, "exit_price": trailing_stop, "side": position['side'], "pnl": pnl, "entry_time": position['entry_time'], "exit_time": row['timestamp']})
                    position = None
                else:
                    new_stop = row['close'] * (1 + self.trailing_percent)
                    trailing_stop = min(trailing_stop, new_stop)
        
        # Close any remaining position at end of backtest
        if position:
            final_trade = self.close_all_positions(df, position, df.iloc[-1]['close'], len(df) - 1)
            if final_trade:
                trades.append(final_trade)
        
        return trades
    
    def _generate_signal_reason(self, df: pd.DataFrame, latest_row: pd.Series) -> str:
        """Generate specific reason for Breakout signal."""
        signal = self._convert_numpy_type(latest_row.get('signal', 0), int)
        close = self._convert_numpy_type(latest_row.get('close', 0), float)
        upper_band = self._convert_numpy_type(latest_row.get('upper_band', 0), float)
        lower_band = self._convert_numpy_type(latest_row.get('lower_band', 0), float)
        atr = self._convert_numpy_type(latest_row.get('atr', 0), float)
        
        if signal == 1:
            return f"Breakout BUY: Price ({close:.2f}) > Upper Band ({upper_band:.2f}), ATR: {atr:.2f}"
        elif signal == -1:
            return f"Breakout SELL: Price ({close:.2f}) < Lower Band ({lower_band:.2f}), ATR: {atr:.2f}"
        else:
            return f"Waiting: Price ({close:.2f}) between bands ({lower_band:.2f} - {upper_band:.2f})"
    
    def entry_range(self, df: pd.DataFrame, signal: int) -> Dict[str, float]:
        """
        Calculate entry range for Breakout strategy based on Bollinger Bands and ATR.
        Uses band width and ATR to determine optimal entry range for breakouts.
        """
        if df.empty or signal == 0:
            current_price = float(df['close'].iloc[-1]) if not df.empty else 0.0
            return {"min": current_price, "max": current_price}
        
        current_price = float(df['close'].iloc[-1])
        
        # Calculate Bollinger Bands for range calculation
        df_temp = df.copy()
        df_temp['sma'] = df_temp['close'].rolling(window=self.lookback).mean()
        df_temp['std'] = df_temp['close'].rolling(window=self.lookback).std()
        df_temp['upper_band'] = df_temp['sma'] + (df_temp['std'] * self.multiplier)
        df_temp['lower_band'] = df_temp['sma'] - (df_temp['std'] * self.multiplier)
        
        upper_band = float(df_temp['upper_band'].iloc[-1])
        lower_band = float(df_temp['lower_band'].iloc[-1])
        sma = float(df_temp['sma'].iloc[-1])
        
        # Calculate ATR for volatility measurement
        atr = self._calculate_atr(df_temp, 14)
        atr_value = float(atr.iloc[-1]) if not atr.empty else current_price * 0.01
        
        # Calculate band width as percentage
        band_width = (upper_band - lower_band) / sma if sma > 0 else 0.02
        
        # Calculate range buffer based on ATR
        range_buffer = atr_value * 0.3  # 30% of ATR for range width
        
        # Base range from band width and ATR
        if signal == 1:  # Buy signal - breakout above upper band
            # For buy signals, prefer higher prices
            min_price = current_price - range_buffer * 0.5
            max_price = current_price + range_buffer * 1.5
        else:  # Sell signal - breakout below lower band
            # For sell signals, prefer lower prices
            min_price = current_price - range_buffer * 1.5
            max_price = current_price + range_buffer * 0.5
        
        return {
            "min": min_price,
            "max": max_price
        }
    
    def calculate_exit_levels(self, df: pd.DataFrame, signal: int, entry_price: float) -> Dict[str, float]:
        """
        Calculate explicit take profit and stop loss levels for Breakout strategy.
        Uses Bollinger Bands and volatility to determine optimal exit points.
        """
        if df.empty or signal == 0:
            return {"stop_loss": entry_price, "take_profit": entry_price}
        
        # Calculate Bollinger Bands
        df_temp = df.copy()
        df_temp['sma'] = df_temp['close'].rolling(window=self.period).mean()
        df_temp['std'] = df_temp['close'].rolling(window=self.period).std()
        df_temp['upper_band'] = df_temp['sma'] + (self.bb_std * df_temp['std'])
        df_temp['lower_band'] = df_temp['sma'] - (self.bb_std * df_temp['std'])
        
        upper_band = float(df_temp['upper_band'].iloc[-1])
        lower_band = float(df_temp['lower_band'].iloc[-1])
        band_width = upper_band - lower_band
        
        # Calculate ATR for volatility
        atr = self._calculate_atr(df_temp, 14)
        atr_value = float(atr.iloc[-1]) if not atr.empty else entry_price * 0.02
        
        # Adjust based on volatility
        volatility_multiplier = min(atr_value / entry_price, 0.05) / 0.02  # Cap at 5%
        volatility_multiplier = max(volatility_multiplier, 0.5)  # Minimum 0.5x
        
        # Adjust based on breakout strength
        if band_width > df_temp['std'].iloc[-1] * 2:  # Strong breakout
            breakout_multiplier = 1.2
        elif band_width < df_temp['std'].iloc[-1] * 1.5:  # Weak breakout
            breakout_multiplier = 0.8
        else:  # Normal breakout
            breakout_multiplier = 1.0
        
        # Calculate levels
        if signal == 1:  # Buy breakout
            # Stop loss below the breakout level (upper band) or ATR-based
            band_stop = upper_band * 0.98  # 2% below upper band
            atr_stop = entry_price - (atr_value * 2)  # 2 ATR below
            stop_loss = max(band_stop, atr_stop)
            
            # Take profit based on band width or ATR
            band_target = upper_band + (band_width * 0.5)  # Half band width above
            atr_target = entry_price + (atr_value * 3)  # 3 ATR above
            take_profit = min(band_target, atr_target)
            
        else:  # Sell breakout
            # Stop loss above the breakout level (lower band) or ATR-based
            band_stop = lower_band * 1.02  # 2% above lower band
            atr_stop = entry_price + (atr_value * 2)  # 2 ATR above
            stop_loss = min(band_stop, atr_stop)
            
            # Take profit based on band width or ATR
            band_target = lower_band - (band_width * 0.5)  # Half band width below
            atr_target = entry_price - (atr_value * 3)  # 3 ATR below
            take_profit = max(band_target, atr_target)
        
        # Apply multipliers
        combined_multiplier = volatility_multiplier * breakout_multiplier
        
        if signal == 1:
            stop_loss = entry_price - ((entry_price - stop_loss) * combined_multiplier)
            take_profit = entry_price + ((take_profit - entry_price) * combined_multiplier)
        else:
            stop_loss = entry_price + ((stop_loss - entry_price) * combined_multiplier)
            take_profit = entry_price - ((entry_price - take_profit) * combined_multiplier)
        
        return {
            "stop_loss": stop_loss,
            "take_profit": take_profit
        }
    
    def risk_targets(self, df: pd.DataFrame, signal: int, current_price: float) -> Dict[str, float]:
        """
        Calculate adaptive risk targets for Breakout strategy.
        Uses Bollinger Bands and ATR to determine optimal stop loss and take profit for breakouts.
        """
        if df.empty or signal == 0:
            return {"stop_loss": current_price, "take_profit": current_price}
        
        # Calculate Bollinger Bands for breakout analysis
        df_temp = df.copy()
        df_temp['sma'] = df_temp['close'].rolling(window=self.lookback).mean()
        df_temp['std'] = df_temp['close'].rolling(window=self.lookback).std()
        df_temp['upper_band'] = df_temp['sma'] + (df_temp['std'] * self.multiplier)
        df_temp['lower_band'] = df_temp['sma'] - (df_temp['std'] * self.multiplier)
        
        upper_band = float(df_temp['upper_band'].iloc[-1])
        lower_band = float(df_temp['lower_band'].iloc[-1])
        sma = float(df_temp['sma'].iloc[-1])
        
        # Calculate ATR for volatility
        atr = self._calculate_atr(df_temp, 14)
        atr_value = float(atr.iloc[-1]) if not atr.empty else current_price * 0.02
        
        # Calculate band width for volatility adjustment
        band_width = upper_band - lower_band
        band_width_pct = band_width / sma if sma > 0 else 0.02
        
        # Base risk levels
        base_stop_loss_pct = 0.03  # 3%
        base_take_profit_pct = 0.06  # 6%
        
        # Adjust based on band width (volatility)
        if band_width_pct > 0.05:  # High volatility - wider stops
            volatility_multiplier = 1.5
        elif band_width_pct < 0.02:  # Low volatility - tighter stops
            volatility_multiplier = 0.7
        else:  # Normal volatility
            volatility_multiplier = 1.0
        
        # Adjust based on breakout strength
        if signal == 1:  # Buy breakout
            breakout_strength = (current_price - upper_band) / upper_band
        else:  # Sell breakout
            breakout_strength = (lower_band - current_price) / lower_band
        
        # Stronger breakouts get better risk/reward
        if breakout_strength > 0.02:  # Strong breakout
            breakout_multiplier = 1.2
        elif breakout_strength < 0.005:  # Weak breakout
            breakout_multiplier = 0.8
        else:  # Normal breakout
            breakout_multiplier = 1.0
        
        # Calculate levels
        if signal == 1:  # Buy breakout
            # Stop loss below the breakout level (upper band) or ATR-based
            band_stop = upper_band * 0.98  # 2% below upper band
            atr_stop = current_price - (atr_value * 2)  # 2 ATR below
            stop_loss = max(band_stop, atr_stop)
            
            # Take profit based on band width or ATR
            band_target = upper_band + (band_width * 0.5)  # Half band width above
            atr_target = current_price + (atr_value * 3)  # 3 ATR above
            take_profit = min(band_target, atr_target)
            
        else:  # Sell breakout
            # Stop loss above the breakout level (lower band) or ATR-based
            band_stop = lower_band * 1.02  # 2% above lower band
            atr_stop = current_price + (atr_value * 2)  # 2 ATR above
            stop_loss = min(band_stop, atr_stop)
            
            # Take profit based on band width or ATR
            band_target = lower_band - (band_width * 0.5)  # Half band width below
            atr_target = current_price - (atr_value * 3)  # 3 ATR below
            take_profit = max(band_target, atr_target)
        
        # Apply multipliers
        combined_multiplier = volatility_multiplier * breakout_multiplier
        
        if signal == 1:
            stop_loss = current_price - ((current_price - stop_loss) * combined_multiplier)
            take_profit = current_price + ((take_profit - current_price) * combined_multiplier)
        else:
            stop_loss = current_price + ((stop_loss - current_price) * combined_multiplier)
            take_profit = current_price - ((current_price - take_profit) * combined_multiplier)
        
        return {
            "stop_loss": stop_loss,
            "take_profit": take_profit
        }
    
    def _calculate_atr(self, df: pd.DataFrame, period: int) -> pd.Series:
        """Calculate ATR indicator."""
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift())
        low_close = abs(df['low'] - df['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        return tr.rolling(window=period).mean()

