"""Mean Reversion with Multi-Indicator Confirmation Strategy."""
import pandas as pd
import numpy as np
from typing import List, Dict
from strategies.strategy_base import StrategyBase


class MeanReversionStrategy(StrategyBase):
    """Mean reversion with multi-indicator confirmation."""
    
    def __init__(self, period: int = 20, bb_std: float = 2.0, rsi_period: int = 14, commission: float = 0.001, slippage: float = 0.0005):
        super().__init__("Mean_Reversion", {"period": period, "bb_std": bb_std, "rsi": rsi_period}, commission, slippage)
        self.period = period
        self.bb_std = bb_std
        self.rsi_period = rsi_period
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate mean reversion signals."""
        df = df.copy()
        df['sma'] = df['close'].rolling(window=self.period).mean()
        df['std'] = df['close'].rolling(window=self.period).std()
        df['upper_band'] = df['sma'] + (self.bb_std * df['std'])
        df['lower_band'] = df['sma'] - (self.bb_std * df['std'])
        df['rsi'] = self._calculate_rsi(df['close'], self.rsi_period)
        df['signal'] = 0
        df.loc[(df['close'] <= df['lower_band']) & (df['rsi'] < 30), 'signal'] = 1
        df.loc[(df['close'] >= df['upper_band']) & (df['rsi'] > 70), 'signal'] = -1
        return df
    
    def generate_trades(self, df: pd.DataFrame) -> List[Dict]:
        """Generate trades from mean reversion signals."""
        trades = []
        position = None
        entry_price = 0
        entry_idx = 0
        for idx, row in df.iterrows():
            if position is None and row['signal'] != 0:
                position = {'side': 'long' if row['signal'] == 1 else 'short', 'entry_price': row['close'], 'entry_idx': idx, 'entry_time': row['timestamp']}
                entry_price = row['close']
                entry_idx = idx
            elif position:
                target = df.loc[idx, 'sma']
                if (position['side'] == 'long' and row['close'] >= target) or (position['side'] == 'short' and row['close'] <= target):
                    pnl = (row['close'] - entry_price) if position['side'] == 'long' else (entry_price - row['close'])
                    trades.append({"entry_price": entry_price, "exit_price": row['close'], "side": position['side'], "pnl": pnl, "entry_time": position['entry_time'], "exit_time": row['timestamp']})
                    position = None
        
        # Close any remaining position at end of backtest
        if position:
            final_trade = self.close_all_positions(df, position, df.iloc[-1]['close'], len(df) - 1)
            if final_trade:
                trades.append(final_trade)
        
        return trades
    
    def _generate_signal_reason(self, df: pd.DataFrame, latest_row: pd.Series) -> str:
        """Generate specific reason for Mean Reversion signal."""
        signal = self._convert_numpy_type(latest_row.get('signal', 0), int)
        close = self._convert_numpy_type(latest_row.get('close', 0), float)
        upper_band = self._convert_numpy_type(latest_row.get('upper_band', 0), float)
        lower_band = self._convert_numpy_type(latest_row.get('lower_band', 0), float)
        sma = self._convert_numpy_type(latest_row.get('sma', 0), float)
        rsi = self._convert_numpy_type(latest_row.get('rsi', 50), float)
        
        if signal == 1:
            return f"Mean Reversion BUY: Price ({close:.2f}) <= Lower Band ({lower_band:.2f}), RSI ({rsi:.1f}) < 30"
        elif signal == -1:
            return f"Mean Reversion SELL: Price ({close:.2f}) >= Upper Band ({upper_band:.2f}), RSI ({rsi:.1f}) > 70"
        else:
            return f"Waiting: Price ({close:.2f}) near SMA ({sma:.2f}), RSI ({rsi:.1f})"
    
    def entry_range(self, df: pd.DataFrame, signal: int) -> Dict[str, float]:
        """
        Calculate entry range for Mean Reversion strategy based on Bollinger Bands and RSI.
        Uses band position and RSI extremes to determine optimal entry range for reversions.
        """
        if df.empty or signal == 0:
            current_price = float(df['close'].iloc[-1]) if not df.empty else 0.0
            return {"min": current_price, "max": current_price}
        
        current_price = float(df['close'].iloc[-1])
        
        # Calculate Bollinger Bands for range calculation
        df_temp = df.copy()
        df_temp['sma'] = df_temp['close'].rolling(window=self.period).mean()
        df_temp['std'] = df_temp['close'].rolling(window=self.period).std()
        df_temp['upper_band'] = df_temp['sma'] + (df_temp['std'] * self.bb_std)
        df_temp['lower_band'] = df_temp['sma'] - (df_temp['std'] * self.bb_std)
        
        upper_band = float(df_temp['upper_band'].iloc[-1])
        lower_band = float(df_temp['lower_band'].iloc[-1])
        sma = float(df_temp['sma'].iloc[-1])
        
        # Calculate RSI for momentum adjustment
        rsi = self._calculate_rsi(df_temp['close'], self.rsi_period)
        current_rsi = float(rsi.iloc[-1]) if not rsi.empty else 50.0
        
        # Calculate ATR for volatility measurement
        atr = self._calculate_atr(df_temp, 14)
        atr_value = float(atr.iloc[-1]) if not atr.empty else current_price * 0.01
        
        # Calculate band width
        band_width = upper_band - lower_band
        
        # Adjust range based on RSI extremes
        if current_rsi > 80:  # Very overbought - expect reversion down
            rsi_multiplier = 0.8
        elif current_rsi < 20:  # Very oversold - expect reversion up
            rsi_multiplier = 0.8
        elif current_rsi > 70:  # Overbought - expect reversion down
            rsi_multiplier = 1.0
        elif current_rsi < 30:  # Oversold - expect reversion up
            rsi_multiplier = 1.0
        else:  # Normal range - wider entry range
            rsi_multiplier = 1.2
        
        # Base range from band width and RSI
        range_buffer = (band_width * 0.2) * rsi_multiplier  # 20% of band width
        
        # Ensure minimum range based on ATR
        min_range = atr_value * 0.25  # Minimum 25% of ATR
        range_buffer = max(range_buffer, min_range)
        
        if signal == 1:  # Buy signal - reversion from oversold
            # For buy signals, prefer higher prices
            min_price = current_price - range_buffer * 0.5
            max_price = current_price + range_buffer * 1.5
        else:  # Sell signal - reversion from overbought
            # For sell signals, prefer lower prices
            min_price = current_price - range_buffer * 1.5
            max_price = current_price + range_buffer * 0.5
        
        return {
            "min": min_price,
            "max": max_price
        }
    
    def calculate_exit_levels(self, df: pd.DataFrame, signal: int, entry_price: float) -> Dict[str, float]:
        """
        Calculate explicit take profit and stop loss levels for Mean Reversion strategy.
        Uses Bollinger Bands and RSI to determine optimal exit points.
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
        sma = float(df_temp['sma'].iloc[-1])
        
        # Calculate RSI for momentum adjustment
        rsi = self._calculate_rsi(df_temp['close'], self.rsi_period)
        current_rsi = float(rsi.iloc[-1]) if not rsi.empty else 50.0
        
        # Calculate ATR for volatility
        atr = self._calculate_atr(df_temp, 14)
        atr_value = float(atr.iloc[-1]) if not atr.empty else entry_price * 0.02
        
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
        
        # Calculate levels
        if signal == 1:  # Buy signal (oversold bounce)
            # Stop loss below lower band or ATR-based
            band_stop = lower_band * 0.98  # 2% below lower band
            atr_stop = entry_price - (atr_value * 2)  # 2 ATR below
            stop_loss = max(band_stop, atr_stop)
            
            # Take profit at SMA or upper band
            sma_target = sma  # Target the mean
            band_target = upper_band * 0.98  # 2% below upper band
            take_profit = min(sma_target, band_target)
            
        else:  # Sell signal (overbought drop)
            # Stop loss above upper band or ATR-based
            band_stop = upper_band * 1.02  # 2% above upper band
            atr_stop = entry_price + (atr_value * 2)  # 2 ATR above
            stop_loss = min(band_stop, atr_stop)
            
            # Take profit at SMA or lower band
            sma_target = sma  # Target the mean
            band_target = lower_band * 1.02  # 2% above lower band
            take_profit = max(sma_target, band_target)
        
        # Apply RSI multiplier
        if signal == 1:
            stop_loss = entry_price - ((entry_price - stop_loss) * rsi_multiplier)
            take_profit = entry_price + ((take_profit - entry_price) * rsi_multiplier)
        else:
            stop_loss = entry_price + ((stop_loss - entry_price) * rsi_multiplier)
            take_profit = entry_price - ((entry_price - take_profit) * rsi_multiplier)
        
        return {
            "stop_loss": stop_loss,
            "take_profit": take_profit
        }
    
    def risk_targets(self, df: pd.DataFrame, signal: int, current_price: float) -> Dict[str, float]:
        """
        Calculate adaptive risk targets for Mean Reversion strategy.
        Uses Bollinger Bands and RSI extremes to determine optimal stop loss and take profit.
        """
        if df.empty or signal == 0:
            return {"stop_loss": current_price, "take_profit": current_price}
        
        # Calculate Bollinger Bands for mean reversion analysis
        df_temp = df.copy()
        df_temp['sma'] = df_temp['close'].rolling(window=self.period).mean()
        df_temp['std'] = df_temp['close'].rolling(window=self.period).std()
        df_temp['upper_band'] = df_temp['sma'] + (df_temp['std'] * self.bb_std)
        df_temp['lower_band'] = df_temp['sma'] - (df_temp['std'] * self.bb_std)
        
        upper_band = float(df_temp['upper_band'].iloc[-1])
        lower_band = float(df_temp['lower_band'].iloc[-1])
        sma = float(df_temp['sma'].iloc[-1])
        
        # Calculate RSI for momentum adjustment
        rsi = self._calculate_rsi(df_temp['close'], self.rsi_period)
        current_rsi = float(rsi.iloc[-1]) if not rsi.empty else 50.0
        
        # Calculate ATR for volatility
        atr = self._calculate_atr(df_temp, 14)
        atr_value = float(atr.iloc[-1]) if not atr.empty else current_price * 0.02
        
        # Base risk levels
        base_stop_loss_pct = 0.025  # 2.5%
        base_take_profit_pct = 0.03  # 3% (smaller for mean reversion)
        
        # Adjust based on RSI extremes
        if current_rsi > 85:  # Extreme overbought - tight stops
            rsi_multiplier = 0.6
        elif current_rsi < 15:  # Extreme oversold - tight stops
            rsi_multiplier = 0.6
        elif current_rsi > 75:  # Overbought
            rsi_multiplier = 0.8
        elif current_rsi < 25:  # Oversold
            rsi_multiplier = 0.8
        else:  # Normal range - wider stops
            rsi_multiplier = 1.2
        
        # Adjust based on distance from mean (SMA)
        distance_from_mean = abs(current_price - sma) / sma if sma > 0 else 0
        if distance_from_mean > 0.05:  # Far from mean - tighter stops
            mean_multiplier = 0.7
        elif distance_from_mean < 0.01:  # Close to mean - wider stops
            mean_multiplier = 1.3
        else:  # Normal distance
            mean_multiplier = 1.0
        
        # Calculate levels
        if signal == 1:  # Buy signal - reversion from oversold
            # Stop loss below lower band or ATR-based
            band_stop = lower_band * 0.95  # 5% below lower band
            atr_stop = current_price - (atr_value * 1.5)  # 1.5 ATR below
            stop_loss = max(band_stop, atr_stop)
            
            # Take profit at SMA or ATR-based
            sma_target = sma * 1.02  # 2% above SMA
            atr_target = current_price + (atr_value * 2)  # 2 ATR above
            take_profit = min(sma_target, atr_target)
            
        else:  # Sell signal - reversion from overbought
            # Stop loss above upper band or ATR-based
            band_stop = upper_band * 1.05  # 5% above upper band
            atr_stop = current_price + (atr_value * 1.5)  # 1.5 ATR above
            stop_loss = min(band_stop, atr_stop)
            
            # Take profit at SMA or ATR-based
            sma_target = sma * 0.98  # 2% below SMA
            atr_target = current_price - (atr_value * 2)  # 2 ATR below
            take_profit = max(sma_target, atr_target)
        
        # Apply multipliers
        combined_multiplier = (rsi_multiplier + mean_multiplier) / 2
        
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
    
    def _calculate_rsi(self, prices: pd.Series, period: int) -> pd.Series:
        """Calculate RSI indicator."""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

