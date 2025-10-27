"""EMA Crossover + RSI Filter Strategy."""
import pandas as pd
import numpy as np
from typing import List, Dict
from strategies.strategy_base import StrategyBase


class EMARSIStrategy(StrategyBase):
    """EMA Crossover with RSI filter strategy."""
    
    def __init__(self, fast_period: int = 12, slow_period: int = 26, rsi_period: int = 14, rsi_oversold: int = 30, rsi_overbought: int = 70, commission: float = 0.001, slippage: float = 0.0005):
        super().__init__("EMA_RSI", {"fast": fast_period, "slow": slow_period, "rsi": rsi_period}, commission, slippage)
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.rsi_period = rsi_period
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate signals based on EMA crossover and RSI."""
        df = df.copy()
        df['ema_fast'] = df['close'].ewm(span=self.fast_period, adjust=False).mean()
        df['ema_slow'] = df['close'].ewm(span=self.slow_period, adjust=False).mean()
        df['rsi'] = self._calculate_rsi(df['close'], self.rsi_period)
        df['signal'] = 0
        df.loc[(df['ema_fast'] > df['ema_slow']) & (df['ema_fast'].shift(1) <= df['ema_slow'].shift(1)) & (df['rsi'] > self.rsi_oversold), 'signal'] = 1
        df.loc[(df['ema_fast'] < df['ema_slow']) & (df['ema_fast'].shift(1) >= df['ema_slow'].shift(1)) & (df['rsi'] < self.rsi_overbought), 'signal'] = -1
        return df
    
    def generate_trades(self, df: pd.DataFrame) -> List[Dict]:
        """Generate trades from signals with stop loss and take profit."""
        trades = []
        position = None
        entry_price = 0
        entry_idx = 0
        stop_loss_pct = 0.02
        take_profit_pct = 0.04
        
        for idx, row in df.iterrows():
            if position is None and row['signal'] != 0:
                position = {'side': 'long' if row['signal'] == 1 else 'short', 'entry_price': row['close'], 'entry_idx': idx, 'entry_time': row['timestamp']}
                entry_price = row['close']
                entry_idx = idx
                sl = entry_price * (1 - stop_loss_pct) if position['side'] == 'long' else entry_price * (1 + stop_loss_pct)
                tp = entry_price * (1 + take_profit_pct) if position['side'] == 'long' else entry_price * (1 - take_profit_pct)
            elif position:
                exit_price = row['close']
                sl_hit = (position['side'] == 'long' and row['low'] <= sl) or (position['side'] == 'short' and row['high'] >= sl)
                tp_hit = (position['side'] == 'long' and row['high'] >= tp) or (position['side'] == 'short' and row['low'] <= tp)
                
                if sl_hit or tp_hit or row['signal'] != 0:
                    if sl_hit:
                        exit_price = sl
                    elif tp_hit:
                        exit_price = tp
                    pnl = (exit_price - entry_price) if position['side'] == 'long' else (entry_price - exit_price)
                    trades.append({"entry_price": entry_price, "exit_price": exit_price, "side": position['side'], "pnl": pnl, "entry_time": position['entry_time'], "exit_time": row['timestamp']})
                    position = None
                    if row['signal'] != 0:
                        position = {'side': 'long' if row['signal'] == 1 else 'short', 'entry_price': row['close'], 'entry_idx': idx, 'entry_time': row['timestamp']}
                        entry_price = row['close']
                        entry_idx = idx
                        sl = entry_price * (1 - stop_loss_pct) if position['side'] == 'long' else entry_price * (1 + stop_loss_pct)
                        tp = entry_price * (1 + take_profit_pct) if position['side'] == 'long' else entry_price * (1 - take_profit_pct)
        
        # Close any remaining position at end of backtest
        if position:
            final_trade = self.close_all_positions(df, position, df.iloc[-1]['close'], len(df) - 1)
            if final_trade:
                trades.append(final_trade)
        
        return trades
    
    def _generate_signal_reason(self, df: pd.DataFrame, latest_row: pd.Series) -> str:
        """Generate specific reason for EMA RSI signal."""
        signal = self._convert_numpy_type(latest_row.get('signal', 0), int)
        rsi = self._convert_numpy_type(latest_row.get('rsi', 50), float)
        ema_fast = self._convert_numpy_type(latest_row.get('ema_fast', 0), float)
        ema_slow = self._convert_numpy_type(latest_row.get('ema_slow', 0), float)
        
        if signal == 1:
            return f"EMA Crossover BUY: Fast EMA ({ema_fast:.2f}) > Slow EMA ({ema_slow:.2f}), RSI ({rsi:.1f}) > {self.rsi_oversold}"
        elif signal == -1:
            return f"EMA Crossover SELL: Fast EMA ({ema_fast:.2f}) < Slow EMA ({ema_slow:.2f}), RSI ({rsi:.1f}) < {self.rsi_overbought}"
        else:
            return f"Waiting: Fast EMA ({ema_fast:.2f}) vs Slow EMA ({ema_slow:.2f}), RSI ({rsi:.1f})"
    
    def entry_range(self, df: pd.DataFrame, signal: int) -> Dict[str, float]:
        """
        Calculate entry range for EMA RSI strategy based on EMA levels and RSI momentum.
        Uses the distance between fast and slow EMA as the primary range indicator.
        """
        if df.empty or signal == 0:
            current_price = float(df['close'].iloc[-1]) if not df.empty else 0.0
            return {"min": current_price, "max": current_price}
        
        current_price = float(df['close'].iloc[-1])
        
        # Calculate EMAs for range calculation
        df_temp = df.copy()
        df_temp['ema_fast'] = df_temp['close'].ewm(span=self.fast_period, adjust=False).mean()
        df_temp['ema_slow'] = df_temp['close'].ewm(span=self.slow_period, adjust=False).mean()
        
        ema_fast = float(df_temp['ema_fast'].iloc[-1])
        ema_slow = float(df_temp['ema_slow'].iloc[-1])
        
        # Calculate RSI for momentum adjustment
        rsi = self._calculate_rsi(df_temp['close'], self.rsi_period)
        current_rsi = float(rsi.iloc[-1]) if not rsi.empty else 50.0
        
        # Base range from EMA distance
        ema_distance = abs(ema_fast - ema_slow)
        
        # Adjust range based on RSI momentum
        if current_rsi > 70:  # Overbought - tighter range
            rsi_multiplier = 0.5
        elif current_rsi < 30:  # Oversold - wider range
            rsi_multiplier = 1.5
        else:  # Normal range
            rsi_multiplier = 1.0
        
        # Calculate range buffer
        range_buffer = ema_distance * rsi_multiplier * 0.3  # 30% of EMA distance
        
        # Ensure minimum range based on ATR
        atr = self._calculate_atr(df, 14)
        if not atr.empty:
            atr_value = float(atr.iloc[-1])
            min_range = atr_value * 0.2  # Minimum 20% of ATR
            range_buffer = max(range_buffer, min_range)
        
        if signal == 1:  # Buy signal - range around current price to EMA levels
            # For buy signals, prefer higher prices (above current)
            min_price = current_price - range_buffer * 0.5
            max_price = current_price + range_buffer * 1.5
        else:  # Sell signal
            # For sell signals, prefer lower prices (below current)
            min_price = current_price - range_buffer * 1.5
            max_price = current_price + range_buffer * 0.5
        
        # Ensure min < max
        if min_price >= max_price:
            mid_price = (min_price + max_price) / 2
            min_price = mid_price - range_buffer
            max_price = mid_price + range_buffer
        
        return {
            "min": min_price,
            "max": max_price
        }
    
    def risk_targets(self, df: pd.DataFrame, signal: int, current_price: float) -> Dict[str, float]:
        """
        Calculate adaptive risk targets for EMA RSI strategy.
        Uses EMA levels and RSI momentum to determine optimal stop loss and take profit.
        """
        if df.empty or signal == 0:
            return {"stop_loss": current_price, "take_profit": current_price}
        
        # Calculate EMAs for risk level determination
        df_temp = df.copy()
        df_temp['ema_fast'] = df_temp['close'].ewm(span=self.fast_period, adjust=False).mean()
        df_temp['ema_slow'] = df_temp['close'].ewm(span=self.slow_period, adjust=False).mean()
        
        ema_fast = float(df_temp['ema_fast'].iloc[-1])
        ema_slow = float(df_temp['ema_slow'].iloc[-1])
        
        # Calculate RSI for momentum adjustment
        rsi = self._calculate_rsi(df_temp['close'], self.rsi_period)
        current_rsi = float(rsi.iloc[-1]) if not rsi.empty else 50.0
        
        # Calculate ATR for volatility
        atr = self._calculate_atr(df_temp, 14)
        atr_value = float(atr.iloc[-1]) if not atr.empty else current_price * 0.02
        
        # Base risk levels
        base_stop_loss_pct = 0.02  # 2%
        base_take_profit_pct = 0.04  # 4%
        
        # Adjust based on RSI momentum
        if current_rsi > 80:  # Very overbought - tighter stops
            rsi_multiplier = 0.7
        elif current_rsi < 20:  # Very oversold - wider stops
            rsi_multiplier = 1.3
        elif current_rsi > 70:  # Overbought
            rsi_multiplier = 0.8
        elif current_rsi < 30:  # Oversold
            rsi_multiplier = 1.2
        else:  # Normal range
            rsi_multiplier = 1.0
        
        # Adjust based on EMA distance (trend strength)
        ema_distance = abs(ema_fast - ema_slow)
        ema_multiplier = min(ema_distance / current_price, 0.05) / 0.02  # Cap at 5%
        ema_multiplier = max(ema_multiplier, 0.5)  # Minimum 0.5x
        
        # Combine adjustments
        volatility_multiplier = (rsi_multiplier + ema_multiplier) / 2
        
        # Calculate levels
        if signal == 1:  # Buy signal
            # Stop loss below slow EMA or ATR-based
            ema_stop = ema_slow * 0.98  # 2% below slow EMA
            atr_stop = current_price - (atr_value * 2)  # 2 ATR below current price
            stop_loss = max(ema_stop, atr_stop)
            
            # Take profit above fast EMA or ATR-based
            ema_target = ema_fast * 1.04  # 4% above fast EMA
            atr_target = current_price + (atr_value * 3)  # 3 ATR above current price
            take_profit = min(ema_target, atr_target)
            
        else:  # Sell signal
            # Stop loss above slow EMA or ATR-based
            ema_stop = ema_slow * 1.02  # 2% above slow EMA
            atr_stop = current_price + (atr_value * 2)  # 2 ATR above current price
            stop_loss = min(ema_stop, atr_stop)
            
            # Take profit below fast EMA or ATR-based
            ema_target = ema_fast * 0.96  # 4% below fast EMA
            atr_target = current_price - (atr_value * 3)  # 3 ATR below current price
            take_profit = max(ema_target, atr_target)
        
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

