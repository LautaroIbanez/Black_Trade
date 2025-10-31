"""MACD crossover strategy with histogram confirmation."""
import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple, List, Optional
from .strategy_base import StrategyBase


class MACDCrossoverStrategy(StrategyBase):
    """MACD crossover strategy with histogram confirmation."""
    
    def __init__(self, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9,
                 histogram_threshold: float = 0.001, zero_line_cross: bool = True,
                 commission: float = 0.001, slippage: float = 0.0005):
        super().__init__("MACDCrossover", {
            "fast_period": fast_period,
            "slow_period": slow_period,
            "signal_period": signal_period,
            "histogram_threshold": histogram_threshold,
            "zero_line_cross": zero_line_cross
        }, commission, slippage)
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period
        self.histogram_threshold = histogram_threshold
        self.zero_line_cross = zero_line_cross
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate MACD indicators."""
        df = df.copy()
        ema_fast = df['close'].ewm(span=self.fast_period, adjust=False).mean()
        ema_slow = df['close'].ewm(span=self.slow_period, adjust=False).mean()
        df['macd'] = ema_fast - ema_slow
        df['macd_signal'] = df['macd'].ewm(span=self.signal_period, adjust=False).mean()
        df['macd_histogram'] = df['macd'] - df['macd_signal']
        return df
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate trading signals from price data."""
        df = self.calculate_indicators(df)
        df['signal'] = 0
        df['strength'] = 0.0
        df['reason'] = "No signal"
        
        # MACD crossover signals
        df.loc[df['macd'] > df['macd_signal'], 'signal'] = 1
        df.loc[df['macd'] < df['macd_signal'], 'signal'] = -1
        
        # Zero line cross confirmation
        if self.zero_line_cross:
            # Require MACD above zero for longs and below zero for shorts
            df.loc[(df['signal'] == 1) & (df['macd'] <= 0), 'signal'] = 0
            df.loc[(df['signal'] == -1) & (df['macd'] >= 0), 'signal'] = 0
        
        # Histogram confirmation
        df.loc[abs(df['macd_histogram']) < self.histogram_threshold, 'signal'] = 0
        
        # Calculate signal strength based on histogram magnitude
        df['strength'] = abs(df['macd_histogram']) / df['macd_histogram'].rolling(20).std()
        df['strength'] = df['strength'].fillna(0)
        df['strength'] = np.clip(df['strength'], 0, 1)
        
        # Generate reasons
        df.loc[df['signal'] == 1, 'reason'] = "MACD bullish crossover"
        df.loc[df['signal'] == -1, 'reason'] = "MACD bearish crossover"
        
        return df
    
    def generate_trades(self, df: pd.DataFrame) -> List[Dict]:
        """Generate trade list from signals. Allows exits when MACD histogram crosses back to zero."""
        trades: List[Dict] = []
        position: Optional[Dict] = None
        entry_price: float = 0.0
        prev_hist: Optional[float] = None

        for idx, row in df.iterrows():
            current_signal = int(row.get('signal', 0))
            current_price = float(row['close'])
            current_time = row.get('timestamp', idx)
            hist_value = float(row.get('macd_histogram', 0.0))

            # Track histogram for zero-cross detection
            if prev_hist is None:
                prev_hist = hist_value

            # Entry logic: only enter on active signals (1 or -1)
            if position is None and current_signal != 0:
                position = {
                    'side': 'long' if current_signal == 1 else 'short',
                    'entry_price': current_price,
                    'entry_idx': idx,
                    'entry_time': current_time
                }
                entry_price = current_price

            # Exit logic: if in a position, exit on opposite signal OR histogram zero-cross against position
            elif position is not None:
                side_multiplier = 1 if position['side'] == 'long' else -1

                # Opposite signal triggers exit and optional flip
                opposite_signal = (current_signal == -side_multiplier and current_signal != 0)

                # Histogram zero-cross against the position triggers exit
                hist_cross_against = (prev_hist is not None) and (prev_hist * side_multiplier > 0) and (hist_value * side_multiplier <= 0)

                if opposite_signal or hist_cross_against:
                    exit_price = current_price
                    pnl = (exit_price - entry_price) if position['side'] == 'long' else (entry_price - exit_price)
                    trades.append({
                        "entry_price": entry_price,
                        "exit_price": exit_price,
                        "side": position['side'],
                        "pnl": pnl,
                        "entry_time": position['entry_time'],
                        "exit_time": current_time,
                        "exit_reason": "opposite_signal" if opposite_signal else "hist_zero_cross"
                    })

                    # Flip if opposite signal is present; otherwise flat
                    if opposite_signal:
                        position = {
                            'side': 'long' if current_signal == 1 else 'short',
                            'entry_price': current_price,
                            'entry_idx': idx,
                            'entry_time': current_time
                        }
                        entry_price = current_price
                    else:
                        position = None

            prev_hist = hist_value

        # Close any open position at the last candle
        if position is not None:
            final_trade = self.close_all_positions(df, position, float(df.iloc[-1]['close']), len(df) - 1)
            if final_trade:
                trades.append(final_trade)

        return trades
    
    # Use base class close_all_positions to ensure final position is closed
    
    def _generate_signal(self, df: pd.DataFrame) -> Tuple[int, float, str]:
        """Generate trading signal based on MACD crossovers."""
        return 0, 0.0, "No signal"
    
    def calculate_exit_levels(self, df: pd.DataFrame, signal: int, entry_price: float) -> Dict[str, float]:
        """Calculate explicit take profit and stop loss levels."""
        return self._default_exit_levels(df, signal, entry_price)
    
    def get_parameters(self) -> Dict[str, Any]:
        """Get strategy parameters."""
        return {
            "fast_period": self.fast_period,
            "slow_period": self.slow_period,
            "signal_period": self.signal_period,
            "histogram_threshold": self.histogram_threshold,
            "zero_line_cross": self.zero_line_cross
        }
