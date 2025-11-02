"""Risk management engine with capital tracking and position sizing."""
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from dataclasses import dataclass

from backend.integrations.base import ExchangeAdapter

logger = logging.getLogger(__name__)


@dataclass
class RiskLimits:
    """Risk limits configuration."""
    max_exposure_pct: float = 80.0
    max_position_pct: float = 25.0
    max_drawdown_pct: float = 20.0
    daily_loss_limit_pct: float = 5.0
    var_limit_1d_95: float = 0.03  # 3% of capital
    var_limit_1w_95: float = 0.10  # 10% of capital


@dataclass
class RiskMetrics:
    """Current risk metrics."""
    total_capital: float
    total_exposure: float
    exposure_pct: float
    var_1d_95: float
    var_1d_99: float
    var_1w_95: float
    var_1w_99: float
    current_drawdown_pct: float
    max_drawdown_pct: float
    unrealized_pnl: float
    daily_pnl: float
    peak_equity: float
    equity: float
    timestamp: datetime


class RiskEngine:
    """Engine for real-time risk management."""
    
    def __init__(
        self,
        exchange_adapter: ExchangeAdapter,
        risk_limits: Optional[RiskLimits] = None,
        strategy_limits: Optional[Dict[str, Dict[str, float]]] = None,
    ):
        """
        Initialize risk engine.
        
        Args:
            exchange_adapter: Exchange adapter for account data
            risk_limits: Global risk limits
            strategy_limits: Per-strategy risk limits
        """
        self.adapter = exchange_adapter
        self.risk_limits = risk_limits or RiskLimits()
        self.strategy_limits = strategy_limits or {}
        
        # Historical data for VaR calculation
        self.equity_history: List[Tuple[datetime, float]] = []
        self.returns_history: List[float] = []
        
        # Peak tracking
        self.peak_equity = 0.0
        self.peak_timestamp: Optional[datetime] = None
        
        # Daily tracking
        self.daily_start_equity = 0.0
        self.daily_start_date: Optional[datetime] = None
        
        self.logger = logging.getLogger(__name__)
    
    def calculate_exposure(self, positions: Optional[List[Dict]] = None) -> Dict[str, float]:
        """
        Calculate total exposure and exposure by asset/strategy.
        
        Args:
            positions: List of positions (if None, fetches from adapter)
            
        Returns:
            Dictionary with exposure metrics
        """
        if positions is None:
            positions = self.adapter.get_positions()
        
        # Calculate total exposure
        total_exposure = sum(p.get('usd_value', 0) * p.get('leverage', 1.0) for p in positions)
        
        # Get total capital
        account_status = self.adapter.get_account_status()
        total_capital = account_status.get('equity', account_status.get('total_capital', 0))
        
        exposure_pct = (total_exposure / total_capital * 100) if total_capital > 0 else 0.0
        
        # Calculate exposure by asset
        exposure_by_asset = {}
        for position in positions:
            asset = position.get('asset', position.get('symbol', ''))
            exposure = position.get('usd_value', 0) * position.get('leverage', 1.0)
            exposure_by_asset[asset] = exposure_by_asset.get(asset, 0) + exposure
        
        # Calculate exposure by strategy
        exposure_by_strategy = {}
        for position in positions:
            strategy = position.get('strategy_name', 'unknown')
            exposure = position.get('usd_value', 0) * position.get('leverage', 1.0)
            exposure_by_strategy[strategy] = exposure_by_strategy.get(strategy, 0) + exposure
        
        return {
            'total_exposure': total_exposure,
            'total_capital': total_capital,
            'exposure_pct': exposure_pct,
            'exposure_by_asset': exposure_by_asset,
            'exposure_by_strategy': exposure_by_strategy,
            'positions_count': len(positions),
        }
    
    def calculate_var(
        self,
        confidence_levels: List[float] = [0.95, 0.99],
        horizons: List[int] = [1, 7],  # days
    ) -> Dict[str, float]:
        """
        Calculate Value at Risk using historical simulation.
        
        Args:
            confidence_levels: Confidence levels (e.g., 0.95, 0.99)
            horizons: Time horizons in days
            
        Returns:
            Dictionary with VaR values (e.g., 'var_1d_95', 'var_1w_99')
        """
        if len(self.returns_history) < 100:
            # Not enough data, return conservative estimates
            account_status = self.adapter.get_account_status()
            equity = account_status.get('equity', 0)
            
            return {
                f'var_{h}d_{int(c*100)}': equity * 0.05  # 5% conservative estimate
                for h in horizons for c in confidence_levels
            }
        
        # Convert returns to numpy array
        returns = np.array(self.returns_history[-252:])  # Use last year
        
        # Calculate VaR for each confidence/horizon combination
        var_results = {}
        
        for horizon in horizons:
            # Scale returns for horizon (assuming sqrt of time)
            horizon_returns = returns * np.sqrt(horizon)
            
            for confidence in confidence_levels:
                # Calculate percentile
                var_value = np.percentile(horizon_returns, (1 - confidence) * 100)
                
                # Get current equity
                account_status = self.adapter.get_account_status()
                equity = account_status.get('equity', 0)
                
                # VaR as absolute value
                var_absolute = abs(var_value * equity)
                
                key = f'var_{horizon}d_{int(confidence*100)}'
                var_results[key] = var_absolute
                
                # Also store as percentage
                var_results[f'{key}_pct'] = abs(var_value) * 100
        
        return var_results
    
    def calculate_drawdown(self) -> Dict[str, float]:
        """
        Calculate current and maximum drawdown.
        
        Returns:
            Dictionary with drawdown metrics
        """
        account_status = self.adapter.get_account_status()
        equity = account_status.get('equity', 0)
        
        # Update peak
        if equity > self.peak_equity:
            self.peak_equity = equity
            self.peak_timestamp = datetime.now()
        
        # Calculate current drawdown
        if self.peak_equity > 0:
            current_drawdown_pct = ((self.peak_equity - equity) / self.peak_equity) * 100
        else:
            current_drawdown_pct = 0.0
        
        # Track in history
        self.equity_history.append((datetime.now(), equity))
        
        # Calculate return
        if len(self.equity_history) >= 2:
            prev_equity = self.equity_history[-2][1]
            if prev_equity > 0:
                daily_return = (equity - prev_equity) / prev_equity
                self.returns_history.append(daily_return)
        
        # Keep history limited (last 365 days)
        if len(self.equity_history) > 365:
            self.equity_history = self.equity_history[-365:]
        if len(self.returns_history) > 365:
            self.returns_history = self.returns_history[-365:]
        
        # Calculate maximum drawdown from history
        max_drawdown_pct = 0.0
        if len(self.equity_history) >= 2:
            equity_values = [e[1] for e in self.equity_history]
            peak_values = np.maximum.accumulate(equity_values)
            drawdowns = ((peak_values - equity_values) / peak_values) * 100
            max_drawdown_pct = float(np.max(drawdowns)) if len(drawdowns) > 0 else 0.0
        
        return {
            'current_drawdown_pct': current_drawdown_pct,
            'max_drawdown_pct': max_drawdown_pct,
            'peak_equity': self.peak_equity,
            'peak_timestamp': self.peak_timestamp.isoformat() if self.peak_timestamp else None,
            'equity': equity,
        }
    
    def calculate_daily_pnl(self) -> float:
        """Calculate daily P&L."""
        account_status = self.adapter.get_account_status()
        equity = account_status.get('equity', 0)
        current_date = datetime.now().date()
        
        # Reset daily tracking if new day
        if self.daily_start_date != current_date:
            self.daily_start_equity = equity
            self.daily_start_date = current_date
        
        daily_pnl = equity - self.daily_start_equity
        daily_pnl_pct = ((equity - self.daily_start_equity) / self.daily_start_equity * 100) if self.daily_start_equity > 0 else 0.0
        
        return daily_pnl
    
    def calculate_position_size(
        self,
        entry_price: float,
        stop_loss: float,
        risk_amount: float,
        strategy_name: Optional[str] = None,
        method: str = 'risk_based',
    ) -> Dict[str, float]:
        """
        Calculate optimal position size.
        
        Args:
            entry_price: Entry price
            stop_loss: Stop loss price
            risk_amount: Maximum amount to risk (in base currency)
            strategy_name: Strategy name for strategy-specific limits
            method: Sizing method ('risk_based', 'kelly', 'fixed_fractional', 'volatility')
            
        Returns:
            Dictionary with position size and related metrics
        """
        account_status = self.adapter.get_account_status()
        equity = account_status.get('equity', 0)
        
        # Get strategy limits if available
        strategy_limit_pct = self.risk_limits.max_position_pct
        if strategy_name and strategy_name in self.strategy_limits:
            strategy_limit_pct = self.strategy_limits[strategy_name].get('max_position_pct', strategy_limit_pct)
        
        # Calculate risk per unit
        if entry_price > 0 and stop_loss > 0:
            risk_per_unit = abs(entry_price - stop_loss)
        else:
            risk_per_unit = entry_price * 0.02  # Default 2% risk
        
        # Method 1: Risk-based (default)
        if method == 'risk_based':
            if risk_per_unit > 0:
                position_size = risk_amount / risk_per_unit
            else:
                position_size = 0
        
        # Method 2: Fixed fractional
        elif method == 'fixed_fractional':
            position_pct = strategy_limit_pct / 100.0
            position_size = (equity * position_pct) / entry_price
        
        # Method 3: Volatility-based (simplified)
        elif method == 'volatility':
            # Use ATR or volatility estimate (simplified)
            volatility = entry_price * 0.02  # 2% default
            position_size = (equity * (strategy_limit_pct / 100.0)) / volatility
        
        # Method 4: Kelly Criterion (simplified)
        elif method == 'kelly':
            # Simplified Kelly: requires win rate and avg win/loss
            # For now, use conservative fraction
            kelly_fraction = 0.1  # 10% of equity (conservative)
            position_size = (equity * kelly_fraction) / entry_price
        else:
            position_size = risk_amount / risk_per_unit if risk_per_unit > 0 else 0
        
        # Apply maximum position size limit
        max_position_value = equity * (strategy_limit_pct / 100.0)
        max_position_size = max_position_value / entry_price if entry_price > 0 else 0
        position_size = min(position_size, max_position_size)
        
        # Calculate position value
        position_value = position_size * entry_price
        
        return {
            'position_size': position_size,
            'position_value': position_value,
            'position_value_pct': (position_value / equity * 100) if equity > 0 else 0,
            'risk_amount': risk_amount,
            'risk_per_unit': risk_per_unit,
            'max_position_size': max_position_size,
            'method': method,
        }
    
    def get_risk_metrics(self) -> RiskMetrics:
        """Get current risk metrics."""
        account_status = self.adapter.get_account_status()
        exposure_data = self.calculate_exposure()
        drawdown_data = self.calculate_drawdown()
        var_data = self.calculate_var()
        daily_pnl = self.calculate_daily_pnl()
        
        return RiskMetrics(
            total_capital=exposure_data['total_capital'],
            total_exposure=exposure_data['total_exposure'],
            exposure_pct=exposure_data['exposure_pct'],
            var_1d_95=var_data.get('var_1d_95', 0.0),
            var_1d_99=var_data.get('var_1d_99', 0.0),
            var_1w_95=var_data.get('var_1w_95', 0.0),
            var_1w_99=var_data.get('var_1w_99', 0.0),
            current_drawdown_pct=drawdown_data['current_drawdown_pct'],
            max_drawdown_pct=drawdown_data['max_drawdown_pct'],
            unrealized_pnl=account_status.get('unrealized_pnl', 0.0),
            daily_pnl=daily_pnl,
            peak_equity=drawdown_data['peak_equity'],
            equity=drawdown_data['equity'],
            timestamp=datetime.now(),
        )
    
    def check_risk_limits(self, metrics: Optional[RiskMetrics] = None) -> Dict[str, Dict[str, bool]]:
        """
        Check if current metrics violate risk limits.
        
        Args:
            metrics: Risk metrics (if None, calculates fresh)
            
        Returns:
            Dictionary with limit checks
        """
        if metrics is None:
            metrics = self.get_risk_metrics()
        
        checks = {
            'exposure': {
                'violated': metrics.exposure_pct > self.risk_limits.max_exposure_pct,
                'value': metrics.exposure_pct,
                'limit': self.risk_limits.max_exposure_pct,
            },
            'drawdown': {
                'violated': metrics.current_drawdown_pct > self.risk_limits.max_drawdown_pct,
                'value': metrics.current_drawdown_pct,
                'limit': self.risk_limits.max_drawdown_pct,
            },
            'daily_loss': {
                'violated': metrics.daily_pnl < 0 and abs(metrics.daily_pnl / metrics.total_capital * 100) > self.risk_limits.daily_loss_limit_pct,
                'value': metrics.daily_pnl,
                'limit_pct': self.risk_limits.daily_loss_limit_pct,
            },
            'var_1d_95': {
                'violated': metrics.var_1d_95 > metrics.total_capital * self.risk_limits.var_limit_1d_95,
                'value': metrics.var_1d_95,
                'limit': metrics.total_capital * self.risk_limits.var_limit_1d_95,
            },
            'var_1w_95': {
                'violated': metrics.var_1w_95 > metrics.total_capital * self.risk_limits.var_limit_1w_95,
                'value': metrics.var_1w_95,
                'limit': metrics.total_capital * self.risk_limits.var_limit_1w_95,
            },
        }
        
        return checks

