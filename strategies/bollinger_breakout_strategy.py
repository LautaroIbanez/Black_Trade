"""Bollinger Bands breakout strategy with volume confirmation."""
import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple, List, Optional
from .strategy_base import StrategyBase


class BollingerBreakoutStrategy(StrategyBase):
    """Bollinger Bands breakout strategy with volume confirmation."""
    
    def __init__(self, period: int = 20, bb_std: float = 2.0, volume_threshold: float = 1.5, 
                 rsi_period: int = 14, commission: float = 0.001, slippage: float = 0.0005):
        """
        Initialize Bollinger Breakout strategy.
        
        Args:
            period: Period for Bollinger Bands calculation
            bb_std: Standard deviation multiplier for Bollinger Bands
            volume_threshold: Volume multiplier threshold for confirmation
            rsi_period: RSI period for momentum confirmation
            commission: Trading commission rate
            slippage: Trading slippage rate
        """
        super().__init__("BollingerBreakout", {
            "period": period,
            "bb_std": bb_std,
            "volume_threshold": volume_threshold,
            "rsi_period": rsi_period
        }, commission, slippage)
        self.period = period
        self.bb_std = bb_std
        self.volume_threshold = volume_threshold
        self.rsi_period = rsi_period
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate Bollinger Bands and RSI indicators."""
        df = df.copy()
        
        # Calculate Bollinger Bands
        df['bb_middle'] = df['close'].rolling(window=self.period).mean()
        bb_std = df['close'].rolling(window=self.period).std()
        df['bb_upper'] = df['bb_middle'] + (bb_std * self.bb_std)
        df['bb_lower'] = df['bb_middle'] - (bb_std * self.bb_std)
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
        
        # Calculate RSI
        df['rsi'] = self._calculate_rsi(df['close'], self.rsi_period)
        
        # Calculate volume moving average
        df['volume_ma'] = df['volume'].rolling(window=self.period).mean()
        df['volume_ratio'] = df['volume'] / df['volume_ma']
        
        # Calculate price position within bands
        df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
        
        return df
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate trading signals from price data."""
        df = self.calculate_indicators(df)
        df['signal'] = 0
        df['strength'] = 0.0
        df['reason'] = "No signal"
        
        for i in range(len(df)):
            if i < self.period:
                continue
            current_df = df.iloc[:i+1]
            signal, strength, reason = self._generate_signal(current_df)
            df.iloc[i, df.columns.get_loc('signal')] = signal
            df.iloc[i, df.columns.get_loc('strength')] = strength
            df.iloc[i, df.columns.get_loc('reason')] = reason
        
        return df
    
    def generate_trades(self, df: pd.DataFrame) -> List[Dict]:
        """Generate trade list from signals."""
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
                    'entry_time': row.get('timestamp', idx)
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
                    "exit_time": row.get('timestamp', idx)
                })
                position = {
                    'side': 'long' if row['signal'] == 1 else 'short',
                    'entry_price': row['close'],
                    'entry_idx': idx,
                    'entry_time': row.get('timestamp', idx)
                }
                entry_price = row['close']
                entry_idx = idx
        
        # Close any remaining position
        if position:
            final_trade = self.close_all_positions(df, position, df.iloc[-1]['close'], len(df) - 1)
            if final_trade:
                trades.append(final_trade)
        
        return trades
    
    def _calculate_rsi(self, prices: pd.Series, period: int) -> pd.Series:
        """Calculate RSI indicator."""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _generate_signal(self, df: pd.DataFrame) -> Tuple[int, float, str]:
        """
        Generate trading signal based on Bollinger Bands breakout.
        
        Returns:
            Tuple of (signal, strength, reason)
            signal: -1 (sell), 0 (hold), 1 (buy)
            strength: Signal strength (0.0 to 1.0)
            reason: Signal reason
        """
        if len(df) < self.period + 1:
            return 0, 0.0, "Insufficient data"
        
        current = df.iloc[-1]
        prev = df.iloc[-2]
        
        # Check for valid indicators
        if pd.isna(current['bb_upper']) or pd.isna(current['bb_lower']) or pd.isna(current['rsi']):
            return 0, 0.0, "Invalid indicators"
        
        signal = 0
        strength = 0.0
        reason = "No signal"
        
        # Volume confirmation
        volume_confirmed = current['volume_ratio'] >= self.volume_threshold
        
        # Bollinger Bands breakout conditions
        upper_breakout = (current['close'] > current['bb_upper'] and 
                         prev['close'] <= prev['bb_upper'])
        lower_breakout = (current['close'] < current['bb_lower'] and 
                         prev['close'] >= prev['bb_lower'])
        
        # RSI momentum confirmation
        rsi_oversold = current['rsi'] < 30
        rsi_overbought = current['rsi'] > 70
        rsi_neutral = 30 <= current['rsi'] <= 70
        
        # Band width for volatility check
        bb_width_ok = current['bb_width'] > 0.02  # Minimum 2% band width
        
        if upper_breakout and volume_confirmed and bb_width_ok:
            # Bullish breakout
            if rsi_neutral or rsi_oversold:
                signal = 1
                strength = min(0.8 + (current['volume_ratio'] - 1.0) * 0.2, 1.0)
                reason = f"Bullish breakout: Close above upper BB, Volume {current['volume_ratio']:.1f}x"
            elif rsi_overbought:
                signal = 1
                strength = 0.6
                reason = f"Bullish breakout with RSI overbought: Close above upper BB"
        
        elif lower_breakout and volume_confirmed and bb_width_ok:
            # Bearish breakout
            if rsi_neutral or rsi_overbought:
                signal = -1
                strength = min(0.8 + (current['volume_ratio'] - 1.0) * 0.2, 1.0)
                reason = f"Bearish breakout: Close below lower BB, Volume {current['volume_ratio']:.1f}x"
            elif rsi_oversold:
                signal = -1
                strength = 0.6
                reason = f"Bearish breakout with RSI oversold: Close below lower BB"
        
        # Mean reversion signals (weaker)
        elif current['bb_position'] > 0.95 and rsi_overbought and volume_confirmed:
            signal = -1
            strength = 0.4
            reason = "Mean reversion: Near upper BB with RSI overbought"
        
        elif current['bb_position'] < 0.05 and rsi_oversold and volume_confirmed:
            signal = 1
            strength = 0.4
            reason = "Mean reversion: Near lower BB with RSI oversold"
        
        return signal, strength, reason
    
    def calculate_exit_levels(self, df: pd.DataFrame, signal: int, entry_price: float) -> Dict[str, float]:
        """
        Calculate explicit take profit and stop loss levels for Bollinger Breakout strategy.
        Uses Bollinger Bands levels and ATR for dynamic exit levels.
        """
        if df.empty or signal == 0:
            return {"stop_loss": entry_price, "take_profit": entry_price}
        
        # Get current Bollinger Bands
        current = df.iloc[-1]
        bb_upper = current['bb_upper']
        bb_lower = current['bb_lower']
        bb_middle = current['bb_middle']
        
        # Calculate ATR for volatility
        atr = self._calculate_atr(df, 14)
        atr_value = float(atr.iloc[-1]) if not atr.empty else entry_price * 0.02
        
        # Calculate band width for volatility adjustment
        bb_width = current['bb_width'] if not pd.isna(current['bb_width']) else 0.02
        volatility_multiplier = min(bb_width / 0.02, 2.0)  # Cap at 2x
        volatility_multiplier = max(volatility_multiplier, 0.5)  # Minimum 0.5x
        
        if signal == 1:  # Buy signal
            # Stop loss: Below lower BB or ATR-based
            bb_stop = bb_lower * 0.98  # 2% below lower BB
            atr_stop = entry_price - (atr_value * 2)  # 2 ATR below entry
            stop_loss = max(bb_stop, atr_stop)
            
            # Take profit: Above upper BB or ATR-based
            bb_target = bb_upper * 1.02  # 2% above upper BB
            atr_target = entry_price + (atr_value * 3)  # 3 ATR above entry
            take_profit = min(bb_target, atr_target)
            
        else:  # Sell signal
            # Stop loss: Above upper BB or ATR-based
            bb_stop = bb_upper * 1.02  # 2% above upper BB
            atr_stop = entry_price + (atr_value * 2)  # 2 ATR above entry
            stop_loss = min(bb_stop, atr_stop)
            
            # Take profit: Below lower BB or ATR-based
            bb_target = bb_lower * 0.98  # 2% below lower BB
            atr_target = entry_price - (atr_value * 3)  # 3 ATR below entry
            take_profit = max(bb_target, atr_target)
        
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
    
    def close_all_positions(self, df: pd.DataFrame, current_position: Optional[Dict], current_price: float, current_idx: int) -> Optional[Dict]:
        """Close any remaining positions at the end of backtest."""
        if current_position:
            pnl = (current_price - current_position['entry_price']) if current_position['side'] == 'long' else (current_position['entry_price'] - current_price)
            return {
                "entry_price": current_position['entry_price'],
                "exit_price": current_price,
                "side": current_position['side'],
                "pnl": pnl,
                "entry_time": current_position['entry_time'],
                "exit_time": df.iloc[current_idx].get('timestamp', current_idx),
                "forced_close": True
            }
        return None
    
    def get_parameters(self) -> Dict[str, Any]:
        """Get strategy parameters."""
        return {
            "period": self.period,
            "bb_std": self.bb_std,
            "volume_threshold": self.volume_threshold,
            "rsi_period": self.rsi_period
        }
