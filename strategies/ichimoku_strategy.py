"""Ichimoku Cloud + ADX Confirmation Strategy."""
import pandas as pd
import numpy as np
from typing import List, Dict
from strategies.strategy_base import StrategyBase


class IchimokuStrategy(StrategyBase):
    """Ichimoku Cloud + ADX confirmation strategy."""
    
    def __init__(self, conversion_period: int = 9, base_period: int = 26, leading_span_b: int = 52, displacement: int = 26, adx_period: int = 14, adx_threshold: int = 25, commission: float = 0.001, slippage: float = 0.0005):
        super().__init__("Ichimoku_ADX", {"conversion": conversion_period, "base": base_period, "leading_b": leading_span_b, "displacement": displacement, "adx": adx_period}, commission, slippage)
        self.conversion_period = conversion_period
        self.base_period = base_period
        self.leading_span_b = leading_span_b
        self.displacement = displacement
        self.adx_period = adx_period
        self.adx_threshold = adx_threshold
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate signals based on Ichimoku cloud and ADX."""
        df = df.copy()
        high_9 = df['high'].rolling(window=self.conversion_period).max()
        low_9 = df['low'].rolling(window=self.conversion_period).min()
        df['tenkan_sen'] = (high_9 + low_9) / 2
        high_26 = df['high'].rolling(window=self.base_period).max()
        low_26 = df['low'].rolling(window=self.base_period).min()
        df['kijun_sen'] = (high_26 + low_26) / 2
        df['senkou_span_a'] = ((df['tenkan_sen'] + df['kijun_sen']) / 2).shift(self.displacement)
        high_52 = df['high'].rolling(window=self.leading_span_b).max()
        low_52 = df['low'].rolling(window=self.leading_span_b).min()
        df['senkou_span_b'] = ((high_52 + low_52) / 2).shift(self.displacement)
        df['adx'] = self._calculate_adx(df, self.adx_period)
        df['signal'] = 0
        df.loc[(df['close'] > df['senkou_span_a']) & (df['close'] > df['senkou_span_b']) & (df['tenkan_sen'] > df['kijun_sen']) & (df['adx'] > self.adx_threshold), 'signal'] = 1
        df.loc[(df['close'] < df['senkou_span_a']) & (df['close'] < df['senkou_span_b']) & (df['tenkan_sen'] < df['kijun_sen']) & (df['adx'] > self.adx_threshold), 'signal'] = -1
        return df
    
    def generate_trades(self, df: pd.DataFrame) -> List[Dict]:
        """Generate trades from signals."""
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
        """Generate specific reason for Ichimoku signal."""
        signal = self._convert_numpy_type(latest_row.get('signal', 0), int)
        close = self._convert_numpy_type(latest_row.get('close', 0), float)
        tenkan_sen = self._convert_numpy_type(latest_row.get('tenkan_sen', 0), float)
        kijun_sen = self._convert_numpy_type(latest_row.get('kijun_sen', 0), float)
        senkou_span_a = self._convert_numpy_type(latest_row.get('senkou_span_a', 0), float)
        senkou_span_b = self._convert_numpy_type(latest_row.get('senkou_span_b', 0), float)
        adx = self._convert_numpy_type(latest_row.get('adx', 0), float)
        
        if signal == 1:
            return f"Ichimoku BUY: Price ({close:.2f}) above cloud, Tenkan ({tenkan_sen:.2f}) > Kijun ({kijun_sen:.2f}), ADX ({adx:.1f}) > {self.adx_threshold}"
        elif signal == -1:
            return f"Ichimoku SELL: Price ({close:.2f}) below cloud, Tenkan ({tenkan_sen:.2f}) < Kijun ({kijun_sen:.2f}), ADX ({adx:.1f}) > {self.adx_threshold}"
        else:
            return f"Waiting: Price ({close:.2f}) in cloud, Tenkan ({tenkan_sen:.2f}) vs Kijun ({kijun_sen:.2f}), ADX ({adx:.1f})"
    
    def entry_range(self, df: pd.DataFrame, signal: int) -> Dict[str, float]:
        """
        Calculate entry range for Ichimoku strategy based on cloud levels and ADX strength.
        Uses cloud thickness and ADX momentum to determine optimal entry range.
        """
        if df.empty or signal == 0:
            current_price = float(df['close'].iloc[-1]) if not df.empty else 0.0
            return {"min": current_price, "max": current_price}
        
        current_price = float(df['close'].iloc[-1])
        
        # Calculate Ichimoku components for range calculation
        df_temp = df.copy()
        df_temp['tenkan_sen'] = (df_temp['high'].rolling(window=self.conversion_period).max() + 
                                df_temp['low'].rolling(window=self.conversion_period).min()) / 2
        df_temp['kijun_sen'] = (df_temp['high'].rolling(window=self.base_period).max() + 
                               df_temp['low'].rolling(window=self.base_period).min()) / 2
        df_temp['senkou_span_a'] = ((df_temp['tenkan_sen'] + df_temp['kijun_sen']) / 2).shift(self.displacement)
        df_temp['senkou_span_b'] = ((df_temp['high'].rolling(window=self.leading_span_b).max() + 
                                    df_temp['low'].rolling(window=self.leading_span_b).min()) / 2).shift(self.displacement)
        
        tenkan_sen = float(df_temp['tenkan_sen'].iloc[-1])
        kijun_sen = float(df_temp['kijun_sen'].iloc[-1])
        senkou_span_a = float(df_temp['senkou_span_a'].iloc[-1])
        senkou_span_b = float(df_temp['senkou_span_b'].iloc[-1])
        
        # Calculate ADX for momentum strength
        adx = self._calculate_adx(df_temp, self.adx_period)
        current_adx = float(adx.iloc[-1]) if not adx.empty else 25.0
        
        # Calculate cloud thickness
        cloud_top = max(senkou_span_a, senkou_span_b)
        cloud_bottom = min(senkou_span_a, senkou_span_b)
        cloud_thickness = cloud_top - cloud_bottom
        
        # Calculate ATR for volatility measurement
        atr = self._calculate_atr(df_temp, 14)
        atr_value = float(atr.iloc[-1]) if not atr.empty else current_price * 0.01
        
        # Adjust range based on ADX strength
        if current_adx > 50:  # Strong trend - tighter range
            adx_multiplier = 0.6
        elif current_adx > 30:  # Moderate trend - normal range
            adx_multiplier = 1.0
        else:  # Weak trend - wider range
            adx_multiplier = 1.4
        
        # Base range from cloud thickness and ADX
        range_buffer = (cloud_thickness * 0.3) * adx_multiplier  # 30% of cloud thickness
        
        # Ensure minimum range based on ATR
        min_range = atr_value * 0.3  # Minimum 30% of ATR
        range_buffer = max(range_buffer, min_range)
        
        # Additional adjustment based on Tenkan-Kijun distance
        tk_distance = abs(tenkan_sen - kijun_sen)
        if tk_distance > 0:
            range_buffer = max(range_buffer, tk_distance * 0.2)
        
        if signal == 1:  # Buy signal - above cloud
            # For buy signals, prefer higher prices
            min_price = current_price - range_buffer * 0.5
            max_price = current_price + range_buffer * 1.5
        else:  # Sell signal - below cloud
            # For sell signals, prefer lower prices
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
        Calculate adaptive risk targets for Ichimoku strategy.
        Uses cloud levels and ADX strength to determine optimal stop loss and take profit.
        """
        if df.empty or signal == 0:
            return {"stop_loss": current_price, "take_profit": current_price}
        
        # Calculate Ichimoku components for risk analysis
        df_temp = df.copy()
        df_temp['tenkan_sen'] = (df_temp['high'].rolling(window=self.conversion_period).max() + 
                                df_temp['low'].rolling(window=self.conversion_period).min()) / 2
        df_temp['kijun_sen'] = (df_temp['high'].rolling(window=self.base_period).max() + 
                               df_temp['low'].rolling(window=self.base_period).min()) / 2
        df_temp['senkou_span_a'] = ((df_temp['tenkan_sen'] + df_temp['kijun_sen']) / 2).shift(self.displacement)
        df_temp['senkou_span_b'] = ((df_temp['high'].rolling(window=self.leading_span_b).max() + 
                                    df_temp['low'].rolling(window=self.leading_span_b).min()) / 2).shift(self.displacement)
        
        tenkan_sen = float(df_temp['tenkan_sen'].iloc[-1])
        kijun_sen = float(df_temp['kijun_sen'].iloc[-1])
        senkou_span_a = float(df_temp['senkou_span_a'].iloc[-1])
        senkou_span_b = float(df_temp['senkou_span_b'].iloc[-1])
        
        # Calculate ADX for trend strength
        adx = self._calculate_adx(df_temp, self.adx_period)
        current_adx = float(adx.iloc[-1]) if not adx.empty else 25.0
        
        # Calculate ATR for volatility
        atr = self._calculate_atr(df_temp, 14)
        atr_value = float(atr.iloc[-1]) if not atr.empty else current_price * 0.02
        
        # Calculate cloud levels
        cloud_top = max(senkou_span_a, senkou_span_b)
        cloud_bottom = min(senkou_span_a, senkou_span_b)
        cloud_thickness = cloud_top - cloud_bottom
        
        # Base risk levels
        base_stop_loss_pct = 0.03  # 3%
        base_take_profit_pct = 0.05  # 5%
        
        # Adjust based on ADX strength
        if current_adx > 60:  # Very strong trend - wider stops
            adx_multiplier = 1.4
        elif current_adx > 40:  # Strong trend - normal stops
            adx_multiplier = 1.1
        elif current_adx > 25:  # Moderate trend - tighter stops
            adx_multiplier = 0.9
        else:  # Weak trend - very tight stops
            adx_multiplier = 0.7
        
        # Adjust based on cloud thickness
        cloud_thickness_pct = cloud_thickness / current_price if current_price > 0 else 0.02
        if cloud_thickness_pct > 0.05:  # Thick cloud - wider stops
            cloud_multiplier = 1.3
        elif cloud_thickness_pct < 0.02:  # Thin cloud - tighter stops
            cloud_multiplier = 0.8
        else:  # Normal cloud
            cloud_multiplier = 1.0
        
        # Calculate levels
        if signal == 1:  # Buy signal - above cloud
            # Stop loss below cloud or Tenkan-sen
            cloud_stop = cloud_bottom * 0.98  # 2% below cloud bottom
            tenkan_stop = tenkan_sen * 0.98  # 2% below Tenkan-sen
            atr_stop = current_price - (atr_value * 2.5)  # 2.5 ATR below
            stop_loss = max(cloud_stop, tenkan_stop, atr_stop)
            
            # Take profit above cloud or ATR-based
            cloud_target = cloud_top * 1.05  # 5% above cloud top
            atr_target = current_price + (atr_value * 4)  # 4 ATR above
            take_profit = min(cloud_target, atr_target)
            
        else:  # Sell signal - below cloud
            # Stop loss above cloud or Tenkan-sen
            cloud_stop = cloud_top * 1.02  # 2% above cloud top
            tenkan_stop = tenkan_sen * 1.02  # 2% above Tenkan-sen
            atr_stop = current_price + (atr_value * 2.5)  # 2.5 ATR above
            stop_loss = min(cloud_stop, tenkan_stop, atr_stop)
            
            # Take profit below cloud or ATR-based
            cloud_target = cloud_bottom * 0.95  # 5% below cloud bottom
            atr_target = current_price - (atr_value * 4)  # 4 ATR below
            take_profit = max(cloud_target, atr_target)
        
        # Apply multipliers
        combined_multiplier = (adx_multiplier + cloud_multiplier) / 2
        
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
    
    def _calculate_adx(self, df: pd.DataFrame, period: int) -> pd.Series:
        """Calculate ADX indicator."""
        plus_dm = df['high'].diff()
        minus_dm = -df['low'].diff()
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0
        tr = pd.concat([df['high'] - df['low'], abs(df['high'] - df['close'].shift(1)), abs(df['low'] - df['close'].shift(1))], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(window=period).mean()
        return adx

