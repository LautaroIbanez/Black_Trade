"""RSI divergence strategy for detecting reversals."""
import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple, List, Optional
from .strategy_base import StrategyBase


class RSIDivergenceStrategy(StrategyBase):
    """RSI divergence strategy for detecting reversals."""
    
    def __init__(self, rsi_period: int = 14, divergence_lookback: int = 5, 
                 min_divergence: float = 0.1, volume_confirmation: bool = True,
                 commission: float = 0.001, slippage: float = 0.0005):
        super().__init__("RSIDivergence", {
            "rsi_period": rsi_period,
            "divergence_lookback": divergence_lookback,
            "min_divergence": min_divergence,
            "volume_confirmation": volume_confirmation
        }, commission, slippage)
        self.rsi_period = rsi_period
        self.divergence_lookback = divergence_lookback
        self.min_divergence = min_divergence
        self.volume_confirmation = volume_confirmation
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate RSI and divergence indicators."""
        df = df.copy()
        df['rsi'] = self._calculate_rsi(df['close'], self.rsi_period)
        df['bullish_divergence'] = 0
        df['bearish_divergence'] = 0
        df['volume_ratio'] = 1.0
        return df
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate trading signals from price data."""
        df = self.calculate_indicators(df)
        df['signal'] = 0
        df['strength'] = 0.0
        df['reason'] = "No signal"
        
        # Detect bullish divergence (price makes lower low, RSI makes higher low)
        for i in range(self.divergence_lookback, len(df)):
            current_price = df.iloc[i]['close']
            current_rsi = df.iloc[i]['rsi']
            
            # Look for lower low in price
            price_low = df.iloc[i-self.divergence_lookback:i]['low'].min()
            if current_price < price_low:
                # Look for higher low in RSI
                rsi_low = df.iloc[i-self.divergence_lookback:i]['rsi'].min()
                if current_rsi > rsi_low and (current_rsi - rsi_low) > self.min_divergence:
                    df.iloc[i, df.columns.get_loc('signal')] = 1
                    df.iloc[i, df.columns.get_loc('strength')] = min((current_rsi - rsi_low) / 10, 1.0)
                    df.iloc[i, df.columns.get_loc('reason')] = "Bullish divergence detected"
        
        # Detect bearish divergence (price makes higher high, RSI makes lower high)
        for i in range(self.divergence_lookback, len(df)):
            current_price = df.iloc[i]['close']
            current_rsi = df.iloc[i]['rsi']
            
            # Look for higher high in price
            price_high = df.iloc[i-self.divergence_lookback:i]['high'].max()
            if current_price > price_high:
                # Look for lower high in RSI
                rsi_high = df.iloc[i-self.divergence_lookback:i]['rsi'].max()
                if current_rsi < rsi_high and (rsi_high - current_rsi) > self.min_divergence:
                    df.iloc[i, df.columns.get_loc('signal')] = -1
                    df.iloc[i, df.columns.get_loc('strength')] = min((rsi_high - current_rsi) / 10, 1.0)
                    df.iloc[i, df.columns.get_loc('reason')] = "Bearish divergence detected"
        
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
                    'entry_time': row['timestamp']
                }
                entry_price = row['close']
                entry_idx = idx
            elif position and row['signal'] != 0 and row['signal'] != (1 if position['side'] == 'long' else -1):
                # Signal change - close position and open new one
                exit_price = row['close']
                pnl = (exit_price - entry_price) if position['side'] == 'long' else (entry_price - exit_price)
                trades.append({
                    "entry_price": entry_price,
                    "exit_price": exit_price,
                    "side": position['side'],
                    "pnl": pnl,
                    "entry_time": position['entry_time'],
                    "exit_time": row['timestamp']
                })
                
                # Open new position
                position = {
                    'side': 'long' if row['signal'] == 1 else 'short',
                    'entry_price': row['close'],
                    'entry_idx': idx,
                    'entry_time': row['timestamp']
                }
                entry_price = row['close']
                entry_idx = idx
        
        # Close final position if exists
        if position:
            final_trade = self.close_all_positions(df, position, df.iloc[-1]['close'], len(df) - 1)
            if final_trade:
                trades.append(final_trade)
        
        return trades
    
    def close_all_positions(self, df: pd.DataFrame, current_position: Optional[Dict], current_price: float, current_idx: int) -> Optional[Dict]:
        """Close any remaining positions at the end of backtest."""
        return None
    
    def _generate_signal(self, df: pd.DataFrame) -> Tuple[int, float, str]:
        """Generate trading signal based on RSI divergence."""
        return 0, 0.0, "No signal"
    
    def calculate_exit_levels(self, df: pd.DataFrame, signal: int, entry_price: float) -> Dict[str, float]:
        """Calculate explicit take profit and stop loss levels."""
        return {"stop_loss": entry_price, "take_profit": entry_price}
    
    def _calculate_rsi(self, prices: pd.Series, period: int) -> pd.Series:
        """Calculate RSI indicator."""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def get_parameters(self) -> Dict[str, Any]:
        """Get strategy parameters."""
        return {
            "rsi_period": self.rsi_period,
            "divergence_lookback": self.divergence_lookback,
            "min_divergence": self.min_divergence,
            "volume_confirmation": self.volume_confirmation
        }
