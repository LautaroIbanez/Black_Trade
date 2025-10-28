"""Ichimoku trend-following strategy with cloud analysis."""
import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple, List, Optional
from .strategy_base import StrategyBase


class IchimokuTrendStrategy(StrategyBase):
    """Ichimoku trend-following strategy with cloud analysis."""
    
    def __init__(self, conversion_period: int = 9, base_period: int = 26, leading_span_b: int = 52,
                 displacement: int = 26, trend_strength: float = 0.6, cloud_thickness: float = 0.5,
                 commission: float = 0.001, slippage: float = 0.0005):
        """
        Initialize Ichimoku Trend strategy.
        
        Args:
            conversion_period: Tenkan-sen period
            base_period: Kijun-sen period
            leading_span_b: Senkou Span B period
            displacement: Leading span displacement
            trend_strength: Minimum trend strength threshold
            cloud_thickness: Minimum cloud thickness threshold
            commission: Trading commission rate
            slippage: Trading slippage rate
        """
        super().__init__("IchimokuTrend", {
            "conversion_period": conversion_period,
            "base_period": base_period,
            "leading_span_b": leading_span_b,
            "displacement": displacement,
            "trend_strength": trend_strength,
            "cloud_thickness": cloud_thickness
        }, commission, slippage)
        self.conversion_period = conversion_period
        self.base_period = base_period
        self.leading_span_b = leading_span_b
        self.displacement = displacement
        self.trend_strength = trend_strength
        self.cloud_thickness = cloud_thickness
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate Ichimoku indicators."""
        df = df.copy()
        
        # Tenkan-sen (Conversion Line)
        high_9 = df['high'].rolling(window=self.conversion_period).max()
        low_9 = df['low'].rolling(window=self.conversion_period).min()
        df['tenkan_sen'] = (high_9 + low_9) / 2
        
        # Kijun-sen (Base Line)
        high_26 = df['high'].rolling(window=self.base_period).max()
        low_26 = df['low'].rolling(window=self.base_period).min()
        df['kijun_sen'] = (high_26 + low_26) / 2
        
        # Senkou Span A (Leading Span A)
        df['senkou_span_a'] = ((df['tenkan_sen'] + df['kijun_sen']) / 2).shift(self.displacement)
        
        # Senkou Span B (Leading Span B)
        high_52 = df['high'].rolling(window=self.leading_span_b).max()
        low_52 = df['low'].rolling(window=self.leading_span_b).min()
        df['senkou_span_b'] = ((high_52 + low_52) / 2).shift(self.displacement)
        
        # Chikou Span (Lagging Span)
        df['chikou_span'] = df['close'].shift(-self.displacement)
        
        # Cloud analysis
        df['cloud_top'] = np.maximum(df['senkou_span_a'], df['senkou_span_b'])
        df['cloud_bottom'] = np.minimum(df['senkou_span_a'], df['senkou_span_b'])
        df['cloud_thickness'] = (df['cloud_top'] - df['cloud_bottom']) / df['close']
        
        # Price position relative to cloud
        df['above_cloud'] = df['close'] > df['cloud_top']
        df['below_cloud'] = df['close'] < df['cloud_bottom']
        df['in_cloud'] = (df['close'] >= df['cloud_bottom']) & (df['close'] <= df['cloud_top'])
        
        # Trend strength calculation
        df['trend_strength'] = abs(df['tenkan_sen'] - df['kijun_sen']) / df['close']
        
        # Cloud color (bullish if senkou_span_a > senkou_span_b)
        df['cloud_bullish'] = df['senkou_span_a'] > df['senkou_span_b']
        
        return df
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate trading signals from price data."""
        df = self.calculate_indicators(df)
        df['signal'] = 0
        df['strength'] = 0.0
        df['reason'] = "No signal"
        
        for i in range(len(df)):
            if i < max(self.leading_span_b, self.displacement):
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
    
    def _generate_signal(self, df: pd.DataFrame) -> Tuple[int, float, str]:
        """
        Generate trading signal based on Ichimoku trend analysis.
        
        Returns:
            Tuple of (signal, strength, reason)
            signal: -1 (sell), 0 (hold), 1 (buy)
            strength: Signal strength (0.0 to 1.0)
            reason: Signal reason
        """
        if len(df) < max(self.leading_span_b, self.displacement) + 1:
            return 0, 0.0, "Insufficient data"
        
        current = df.iloc[-1]
        prev = df.iloc[-2]
        
        # Check for valid indicators
        if (pd.isna(current['tenkan_sen']) or pd.isna(current['kijun_sen']) or 
            pd.isna(current['senkou_span_a']) or pd.isna(current['senkou_span_b'])):
            return 0, 0.0, "Invalid indicators"
        
        signal = 0
        strength = 0.0
        reason = "No signal"
        
        # Cloud thickness check
        cloud_thick_enough = current['cloud_thickness'] >= self.cloud_thickness / 100
        
        # Trend strength check
        trend_strong_enough = current['trend_strength'] >= self.trend_strength / 100
        
        # Price position analysis
        above_cloud = current['above_cloud']
        below_cloud = current['below_cloud']
        in_cloud = current['in_cloud']
        
        # Cloud color analysis
        cloud_bullish = current['cloud_bullish']
        cloud_bearish = not cloud_bullish
        
        # Tenkan/Kijun relationship
        tenkan_above_kijun = current['tenkan_sen'] > current['kijun_sen']
        tenkan_below_kijun = current['tenkan_sen'] < current['kijun_sen']
        
        # Price vs Tenkan/Kijun
        price_above_tenkan = current['close'] > current['tenkan_sen']
        price_below_tenkan = current['close'] < current['tenkan_sen']
        price_above_kijun = current['close'] > current['kijun_sen']
        price_below_kijun = current['close'] < current['kijun_sen']
        
        # Strong bullish signal
        if (above_cloud and cloud_bullish and tenkan_above_kijun and 
            price_above_tenkan and price_above_kijun and 
            cloud_thick_enough and trend_strong_enough):
            signal = 1
            strength = min(0.9 + current['trend_strength'] * 100, 1.0)
            reason = "Strong bullish: Above bullish cloud, all lines aligned"
        
        # Strong bearish signal
        elif (below_cloud and cloud_bearish and tenkan_below_kijun and 
              price_below_tenkan and price_below_kijun and 
              cloud_thick_enough and trend_strong_enough):
            signal = -1
            strength = min(0.9 + current['trend_strength'] * 100, 1.0)
            reason = "Strong bearish: Below bearish cloud, all lines aligned"
        
        # Moderate bullish signal
        elif (above_cloud and tenkan_above_kijun and price_above_tenkan and 
              cloud_thick_enough):
            signal = 1
            strength = 0.7
            reason = "Moderate bullish: Above cloud, tenkan above kijun"
        
        # Moderate bearish signal
        elif (below_cloud and tenkan_below_kijun and price_below_tenkan and 
              cloud_thick_enough):
            signal = -1
            strength = 0.7
            reason = "Moderate bearish: Below cloud, tenkan below kijun"
        
        # Weak bullish signal (in cloud but bullish setup)
        elif (in_cloud and cloud_bullish and tenkan_above_kijun and 
              price_above_kijun and trend_strong_enough):
            signal = 1
            strength = 0.5
            reason = "Weak bullish: In bullish cloud, price above kijun"
        
        # Weak bearish signal (in cloud but bearish setup)
        elif (in_cloud and cloud_bearish and tenkan_below_kijun and 
              price_below_kijun and trend_strong_enough):
            signal = -1
            strength = 0.5
            reason = "Weak bearish: In bearish cloud, price below kijun"
        
        return signal, strength, reason
    
    def calculate_exit_levels(self, df: pd.DataFrame, signal: int, entry_price: float) -> Dict[str, float]:
        """
        Calculate explicit take profit and stop loss levels for Ichimoku Trend strategy.
        Uses Ichimoku lines and cloud levels for dynamic exit levels.
        """
        if df.empty or signal == 0:
            return {"stop_loss": entry_price, "take_profit": entry_price}
        
        # Get current Ichimoku levels
        current = df.iloc[-1]
        tenkan_sen = current['tenkan_sen']
        kijun_sen = current['kijun_sen']
        cloud_top = current['cloud_top']
        cloud_bottom = current['cloud_bottom']
        
        # Calculate ATR for volatility
        atr = self._calculate_atr(df, 14)
        atr_value = float(atr.iloc[-1]) if not atr.empty else entry_price * 0.02
        
        # Calculate trend strength multiplier
        trend_strength = current['trend_strength'] if not pd.isna(current['trend_strength']) else 0.01
        trend_multiplier = min(trend_strength * 100, 2.0)  # Cap at 2x
        trend_multiplier = max(trend_multiplier, 0.5)  # Minimum 0.5x
        
        if signal == 1:  # Buy signal
            # Stop loss: Below kijun-sen or cloud bottom
            kijun_stop = kijun_sen * 0.98  # 2% below kijun
            cloud_stop = cloud_bottom * 0.95  # 5% below cloud bottom
            atr_stop = entry_price - (atr_value * 2)  # 2 ATR below entry
            stop_loss = max(kijun_stop, cloud_stop, atr_stop)
            
            # Take profit: Above cloud top or ATR-based
            cloud_target = cloud_top * 1.05  # 5% above cloud top
            atr_target = entry_price + (atr_value * 4)  # 4 ATR above entry
            take_profit = min(cloud_target, atr_target)
            
        else:  # Sell signal
            # Stop loss: Above kijun-sen or cloud top
            kijun_stop = kijun_sen * 1.02  # 2% above kijun
            cloud_stop = cloud_top * 1.05  # 5% above cloud top
            atr_stop = entry_price + (atr_value * 2)  # 2 ATR above entry
            stop_loss = min(kijun_stop, cloud_stop, atr_stop)
            
            # Take profit: Below cloud bottom or ATR-based
            cloud_target = cloud_bottom * 0.95  # 5% below cloud bottom
            atr_target = entry_price - (atr_value * 4)  # 4 ATR below entry
            take_profit = max(cloud_target, atr_target)
        
        # Apply trend strength multiplier
        if signal == 1:
            stop_loss = entry_price - ((entry_price - stop_loss) * trend_multiplier)
            take_profit = entry_price + ((take_profit - entry_price) * trend_multiplier)
        else:
            stop_loss = entry_price + ((stop_loss - entry_price) * trend_multiplier)
            take_profit = entry_price - ((entry_price - take_profit) * trend_multiplier)
        
        return {
            "stop_loss": stop_loss,
            "take_profit": take_profit
        }
    
    def get_parameters(self) -> Dict[str, Any]:
        """Get strategy parameters."""
        return {
            "conversion_period": self.conversion_period,
            "base_period": self.base_period,
            "leading_span_b": self.leading_span_b,
            "displacement": self.displacement,
            "trend_strength": self.trend_strength,
            "cloud_thickness": self.cloud_thickness
        }
