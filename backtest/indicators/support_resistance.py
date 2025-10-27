"""
Support and Resistance Level Detection Module.

This module provides functionality to identify key support and resistance levels
from historical price data using various methods including pivot points,
fractal analysis, and volume-based levels.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass


@dataclass
class SupportResistanceLevel:
    """Represents a support or resistance level."""
    price: float
    strength: float  # 0.0 to 1.0
    level_type: str  # 'support' or 'resistance'
    touches: int  # Number of times price touched this level
    last_touch: Optional[pd.Timestamp] = None
    volume_profile: Optional[float] = None  # Average volume at this level


class SupportResistanceDetector:
    """Detects support and resistance levels from price data."""
    
    def __init__(self, min_touches: int = 2, lookback_period: int = 20, 
                 strength_threshold: float = 0.3):
        """
        Initialize the detector.
        
        Args:
            min_touches: Minimum number of touches required for a level
            lookback_period: Period for fractal analysis
            strength_threshold: Minimum strength for a level to be considered
        """
        self.min_touches = min_touches
        self.lookback_period = lookback_period
        self.strength_threshold = strength_threshold
    
    def detect_levels(self, df: pd.DataFrame) -> List[SupportResistanceLevel]:
        """
        Detect support and resistance levels from price data.
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            List of SupportResistanceLevel objects
        """
        levels = []
        
        # Method 1: Pivot Points
        pivot_levels = self._detect_pivot_levels(df)
        levels.extend(pivot_levels)
        
        # Method 2: Fractal Analysis
        fractal_levels = self._detect_fractal_levels(df)
        levels.extend(fractal_levels)
        
        # Method 3: Volume Profile
        volume_levels = self._detect_volume_levels(df)
        levels.extend(volume_levels)
        
        # Method 4: Moving Average Levels
        ma_levels = self._detect_ma_levels(df)
        levels.extend(ma_levels)
        
        # Filter and merge similar levels
        filtered_levels = self._filter_and_merge_levels(levels, df)
        
        return filtered_levels
    
    def _detect_pivot_levels(self, df: pd.DataFrame) -> List[SupportResistanceLevel]:
        """Detect levels using pivot point analysis."""
        levels = []
        
        # Find local highs and lows
        highs = df['high'].rolling(window=self.lookback_period, center=True).max()
        lows = df['low'].rolling(window=self.lookback_period, center=True).min()
        
        # Identify pivot highs and lows
        pivot_highs = df[df['high'] == highs]['high']
        pivot_lows = df[df['low'] == lows]['low']
        
        # Create resistance levels from pivot highs
        for idx, price in pivot_highs.items():
            touches = self._count_touches(df, price, 'resistance')
            if touches >= self.min_touches:
                strength = min(touches / 5.0, 1.0)  # Normalize to 0-1
                levels.append(SupportResistanceLevel(
                    price=float(price),
                    strength=strength,
                    level_type='resistance',
                    touches=touches,
                    last_touch=idx
                ))
        
        # Create support levels from pivot lows
        for idx, price in pivot_lows.items():
            touches = self._count_touches(df, price, 'support')
            if touches >= self.min_touches:
                strength = min(touches / 5.0, 1.0)  # Normalize to 0-1
                levels.append(SupportResistanceLevel(
                    price=float(price),
                    strength=strength,
                    level_type='support',
                    touches=touches,
                    last_touch=idx
                ))
        
        return levels
    
    def _detect_fractal_levels(self, df: pd.DataFrame) -> List[SupportResistanceLevel]:
        """Detect levels using fractal analysis."""
        levels = []
        
        # Find fractal highs and lows
        fractal_highs = self._find_fractal_highs(df)
        fractal_lows = self._find_fractal_lows(df)
        
        # Group similar fractal levels
        for price in fractal_highs:
            touches = self._count_touches(df, price, 'resistance')
            if touches >= self.min_touches:
                strength = min(touches / 3.0, 1.0)
                levels.append(SupportResistanceLevel(
                    price=float(price),
                    strength=strength,
                    level_type='resistance',
                    touches=touches
                ))
        
        for price in fractal_lows:
            touches = self._count_touches(df, price, 'support')
            if touches >= self.min_touches:
                strength = min(touches / 3.0, 1.0)
                levels.append(SupportResistanceLevel(
                    price=float(price),
                    strength=strength,
                    level_type='support',
                    touches=touches
                ))
        
        return levels
    
    def _detect_volume_levels(self, df: pd.DataFrame) -> List[SupportResistanceLevel]:
        """Detect levels based on volume profile."""
        levels = []
        
        if 'volume' not in df.columns:
            return levels
        
        # Create price bins for volume analysis
        price_range = df['high'].max() - df['low'].min()
        bin_size = price_range / 50  # 50 bins
        
        # Calculate volume at each price level
        volume_profile = {}
        for _, row in df.iterrows():
            price_bin = round(row['close'] / bin_size) * bin_size
            if price_bin not in volume_profile:
                volume_profile[price_bin] = 0
            volume_profile[price_bin] += row['volume']
        
        # Find high volume levels
        max_volume = max(volume_profile.values()) if volume_profile else 1
        for price, volume in volume_profile.items():
            if volume > max_volume * 0.3:  # 30% of max volume
                # Determine if it's support or resistance
                level_type = 'support' if price < df['close'].iloc[-1] else 'resistance'
                touches = self._count_touches(df, price, level_type)
                
                if touches >= self.min_touches:
                    strength = min(volume / max_volume, 1.0)
                    levels.append(SupportResistanceLevel(
                        price=float(price),
                        strength=strength,
                        level_type=level_type,
                        touches=touches,
                        volume_profile=volume
                    ))
        
        return levels
    
    def _detect_ma_levels(self, df: pd.DataFrame) -> List[SupportResistanceLevel]:
        """Detect levels based on moving averages."""
        levels = []
        
        # Calculate various moving averages
        ma_periods = [20, 50, 100, 200]
        
        for period in ma_periods:
            if len(df) >= period:
                ma = df['close'].rolling(window=period).mean()
                current_ma = float(ma.iloc[-1])
                
                # Check if MA acts as support/resistance
                touches = self._count_touches(df, current_ma, 'both')
                if touches >= self.min_touches:
                    strength = min(touches / 4.0, 1.0)
                    level_type = 'support' if current_ma < df['close'].iloc[-1] else 'resistance'
                    
                    levels.append(SupportResistanceLevel(
                        price=current_ma,
                        strength=strength,
                        level_type=level_type,
                        touches=touches
                    ))
        
        return levels
    
    def _find_fractal_highs(self, df: pd.DataFrame) -> List[float]:
        """Find fractal high points."""
        highs = []
        window = 5  # 5-bar fractal
        
        for i in range(window, len(df) - window):
            current_high = df['high'].iloc[i]
            is_fractal = True
            
            # Check if current high is higher than surrounding bars
            for j in range(i - window, i + window + 1):
                if j != i and df['high'].iloc[j] >= current_high:
                    is_fractal = False
                    break
            
            if is_fractal:
                highs.append(current_high)
        
        return highs
    
    def _find_fractal_lows(self, df: pd.DataFrame) -> List[float]:
        """Find fractal low points."""
        lows = []
        window = 5  # 5-bar fractal
        
        for i in range(window, len(df) - window):
            current_low = df['low'].iloc[i]
            is_fractal = True
            
            # Check if current low is lower than surrounding bars
            for j in range(i - window, i + window + 1):
                if j != i and df['low'].iloc[j] <= current_low:
                    is_fractal = False
                    break
            
            if is_fractal:
                lows.append(current_low)
        
        return lows
    
    def _count_touches(self, df: pd.DataFrame, price: float, level_type: str, 
                      tolerance: float = 0.005) -> int:
        """Count how many times price touched a level."""
        touches = 0
        price_tolerance = price * tolerance
        
        for _, row in df.iterrows():
            if level_type == 'support' or level_type == 'both':
                if abs(row['low'] - price) <= price_tolerance:
                    touches += 1
            if level_type == 'resistance' or level_type == 'both':
                if abs(row['high'] - price) <= price_tolerance:
                    touches += 1
        
        return touches
    
    def _filter_and_merge_levels(self, levels: List[SupportResistanceLevel], 
                                df: pd.DataFrame) -> List[SupportResistanceLevel]:
        """Filter and merge similar levels."""
        if not levels:
            return []
        
        # Sort by strength
        levels.sort(key=lambda x: x.strength, reverse=True)
        
        filtered_levels = []
        current_price = float(df['close'].iloc[-1])
        price_tolerance = current_price * 0.01  # 1% tolerance
        
        for level in levels:
            # Skip if too close to current price
            if abs(level.price - current_price) < price_tolerance:
                continue
            
            # Check if similar level already exists
            similar_exists = False
            for existing in filtered_levels:
                if (abs(level.price - existing.price) < price_tolerance and 
                    level.level_type == existing.level_type):
                    # Merge levels (keep stronger one)
                    if level.strength > existing.strength:
                        existing.price = level.price
                        existing.strength = level.strength
                        existing.touches = level.touches
                    similar_exists = True
                    break
            
            if not similar_exists and level.strength >= self.strength_threshold:
                filtered_levels.append(level)
        
        # Sort by price
        filtered_levels.sort(key=lambda x: x.price)
        
        return filtered_levels
    
    def get_relevant_levels(self, levels: List[SupportResistanceLevel], 
                           current_price: float, 
                           price_range: float = 0.1) -> List[SupportResistanceLevel]:
        """
        Get levels within a price range of current price.
        
        Args:
            levels: List of support/resistance levels
            current_price: Current market price
            price_range: Price range as percentage (0.1 = 10%)
            
        Returns:
            List of relevant levels
        """
        relevant_levels = []
        min_price = current_price * (1 - price_range)
        max_price = current_price * (1 + price_range)
        
        for level in levels:
            if min_price <= level.price <= max_price:
                relevant_levels.append(level)
        
        return relevant_levels


def calculate_support_resistance_levels(df: pd.DataFrame, 
                                      min_touches: int = 2,
                                      lookback_period: int = 20,
                                      strength_threshold: float = 0.3) -> List[SupportResistanceLevel]:
    """
    Convenience function to calculate support and resistance levels.
    
    Args:
        df: DataFrame with OHLCV data
        min_touches: Minimum number of touches required
        lookback_period: Period for fractal analysis
        strength_threshold: Minimum strength threshold
        
    Returns:
        List of SupportResistanceLevel objects
    """
    detector = SupportResistanceDetector(
        min_touches=min_touches,
        lookback_period=lookback_period,
        strength_threshold=strength_threshold
    )
    
    return detector.detect_levels(df)
