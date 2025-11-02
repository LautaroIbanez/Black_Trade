"""Generate synthetic datasets for strategy testing."""
import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from datetime import datetime, timedelta


class SyntheticDataGenerator:
    """Generate synthetic OHLCV data with controlled characteristics."""
    
    def __init__(self, seed: Optional[int] = None):
        """Initialize generator with optional seed."""
        if seed is not None:
            np.random.seed(seed)
    
    def generate_trending(
        self,
        periods: int = 1000,
        trend_strength: float = 0.001,
        volatility: float = 0.02,
        start_price: float = 50000.0,
    ) -> pd.DataFrame:
        """Generate trending market data."""
        dates = pd.date_range(start='2024-01-01', periods=periods, freq='1h')
        
        # Generate price with trend
        trend = np.linspace(0, trend_strength * periods, periods)
        noise = np.random.randn(periods) * volatility
        log_prices = np.log(start_price) + np.cumsum(trend + noise)
        prices = np.exp(log_prices)
        
        # Generate OHLC from prices
        high_noise = np.abs(np.random.randn(periods) * volatility * 0.5)
        low_noise = np.abs(np.random.randn(periods) * volatility * 0.5)
        
        df = pd.DataFrame({
            'timestamp': dates,
            'open': prices,
            'high': prices * (1 + high_noise),
            'low': prices * (1 - low_noise),
            'close': np.roll(prices, -1)[:-1],  # Next open
            'volume': np.random.uniform(1000, 10000, periods),
        })
        
        # Fix last close
        df.iloc[-1, df.columns.get_loc('close')] = prices[-1]
        
        return df
    
    def generate_ranging(
        self,
        periods: int = 1000,
        range_center: float = 50000.0,
        range_size: float = 0.05,  # 5% range
        volatility: float = 0.01,
    ) -> pd.DataFrame:
        """Generate ranging/mean-reverting market data."""
        dates = pd.date_range(start='2024-01-01', periods=periods, freq='1h')
        
        # Mean-reverting process
        prices = np.zeros(periods)
        prices[0] = range_center
        
        for i in range(1, periods):
            # Mean-reverting component
            reversion = (range_center - prices[i-1]) * 0.1
            noise = np.random.randn() * volatility
            prices[i] = prices[i-1] + reversion + noise
            
            # Bound within range
            if prices[i] > range_center * (1 + range_size):
                prices[i] = range_center * (1 + range_size)
            elif prices[i] < range_center * (1 - range_size):
                prices[i] = range_center * (1 - range_size)
        
        # Generate OHLC
        high_noise = np.abs(np.random.randn(periods) * volatility * 0.5)
        low_noise = np.abs(np.random.randn(periods) * volatility * 0.5)
        
        df = pd.DataFrame({
            'timestamp': dates,
            'open': prices,
            'high': prices * (1 + high_noise),
            'low': prices * (1 - low_noise),
            'close': np.roll(prices, -1)[:-1],
            'volume': np.random.uniform(1000, 10000, periods),
        })
        
        df.iloc[-1, df.columns.get_loc('close')] = prices[-1]
        
        return df
    
    def generate_volatile(
        self,
        periods: int = 1000,
        base_price: float = 50000.0,
        base_volatility: float = 0.02,
        volatility_spikes: int = 10,
    ) -> pd.DataFrame:
        """Generate volatile market with spikes."""
        dates = pd.date_range(start='2024-01-01', periods=periods, freq='1h')
        
        # Variable volatility
        volatility = np.ones(periods) * base_volatility
        
        # Add volatility spikes
        spike_indices = np.random.choice(periods, size=volatility_spikes, replace=False)
        for idx in spike_indices:
            volatility[idx:idx+20] *= 3.0  # 3x volatility for 20 periods
        
        # Generate prices with variable volatility
        returns = np.random.randn(periods) * volatility
        log_prices = np.log(base_price) + np.cumsum(returns)
        prices = np.exp(log_prices)
        
        # Generate OHLC
        high_noise = np.abs(np.random.randn(periods) * volatility * 0.5)
        low_noise = np.abs(np.random.randn(periods) * volatility * 0.5)
        
        df = pd.DataFrame({
            'timestamp': dates,
            'open': prices,
            'high': prices * (1 + high_noise),
            'low': prices * (1 - low_noise),
            'close': np.roll(prices, -1)[:-1],
            'volume': np.random.uniform(1000, 10000, periods),
        })
        
        df.iloc[-1, df.columns.get_loc('close')] = prices[-1]
        
        return df
    
    def generate_regime_switching(
        self,
        periods: int = 1000,
        regimes: List[str] = ['trending', 'ranging'],
        switch_probability: float = 0.01,
        base_price: float = 50000.0,
    ) -> pd.DataFrame:
        """Generate data that switches between market regimes."""
        dates = pd.date_range(start='2024-01-01', periods=periods, freq='1h')
        
        # Determine regime for each period
        current_regime = regimes[0]
        regime_sequence = [current_regime]
        
        for _ in range(1, periods):
            if np.random.rand() < switch_probability:
                current_regime = np.random.choice(regimes)
            regime_sequence.append(current_regime)
        
        # Generate data based on regime
        all_data = []
        current_price = base_price
        
        for i, regime in enumerate(regime_sequence):
            if regime == 'trending':
                # Trending segment
                trend = np.random.choice([-1, 1]) * 0.0005
                volatility = 0.02
            elif regime == 'ranging':
                # Ranging segment
                trend = (base_price - current_price) * 0.05
                volatility = 0.01
            else:
                trend = 0
                volatility = 0.02
            
            # Generate single period price
            change = trend + np.random.randn() * volatility
            current_price = current_price * (1 + change)
            
            # Generate OHLC for this period
            high_noise = abs(np.random.randn() * volatility * 0.5)
            low_noise = abs(np.random.randn() * volatility * 0.5)
            
            all_data.append({
                'timestamp': dates[i],
                'open': current_price,
                'high': current_price * (1 + high_noise),
                'low': current_price * (1 - low_noise),
                'close': current_price * (1 + np.random.randn() * volatility * 0.3),
                'volume': np.random.uniform(1000, 10000),
            })
            
            # Update current_price to next open
            current_price = all_data[-1]['close']
        
        df = pd.DataFrame(all_data)
        return df

