"""Database models for risk metrics."""
from sqlalchemy import Column, Integer, String, Numeric, DateTime
from sqlalchemy.sql import func
from datetime import datetime

from backend.models.base import Base


class RiskMetric(Base):
    """Model for storing risk metrics over time."""
    __tablename__ = 'risk_metrics'
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    total_capital = Column(Numeric(30, 8))
    total_exposure = Column(Numeric(30, 8))
    exposure_pct = Column(Numeric(10, 4))
    var_1d_95 = Column(Numeric(30, 8))
    var_1d_99 = Column(Numeric(30, 8))
    var_1w_95 = Column(Numeric(30, 8))
    var_1w_99 = Column(Numeric(30, 8))
    current_drawdown_pct = Column(Numeric(10, 4))
    max_drawdown_pct = Column(Numeric(10, 4))
    unrealized_pnl = Column(Numeric(30, 8))
    daily_pnl = Column(Numeric(30, 8))
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'total_capital': float(self.total_capital) if self.total_capital else 0,
            'total_exposure': float(self.total_exposure) if self.total_exposure else 0,
            'exposure_pct': float(self.exposure_pct) if self.exposure_pct else 0,
            'var_1d_95': float(self.var_1d_95) if self.var_1d_95 else 0,
            'var_1d_95': float(self.var_1d_99) if self.var_1d_99 else 0,
            'var_1w_95': float(self.var_1w_95) if self.var_1w_95 else 0,
            'var_1w_99': float(self.var_1w_99) if self.var_1w_99 else 0,
            'current_drawdown_pct': float(self.current_drawdown_pct) if self.current_drawdown_pct else 0,
            'max_drawdown_pct': float(self.max_drawdown_pct) if self.max_drawdown_pct else 0,
            'unrealized_pnl': float(self.unrealized_pnl) if self.unrealized_pnl else 0,
            'daily_pnl': float(self.daily_pnl) if self.daily_pnl else 0,
        }


class AccountBalance(Base):
    """Model for storing account balance snapshots."""
    __tablename__ = 'account_balances'
    
    id = Column(Integer, primary_key=True)
    account_id = Column(String(50))  # Reference to account/exchange
    asset = Column(String(10))  # Asset symbol
    free_balance = Column(Numeric(30, 8))
    locked_balance = Column(Numeric(30, 8))
    total_balance = Column(Numeric(30, 8))
    usd_value = Column(Numeric(30, 8))
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'account_id': self.account_id,
            'asset': self.asset,
            'free_balance': float(self.free_balance) if self.free_balance else 0,
            'locked_balance': float(self.locked_balance) if self.locked_balance else 0,
            'total_balance': float(self.total_balance) if self.total_balance else 0,
            'usd_value': float(self.usd_value) if self.usd_value else 0,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
        }


class Position(Base):
    """Model for storing position snapshots."""
    __tablename__ = 'positions'
    
    id = Column(Integer, primary_key=True)
    account_id = Column(String(50))
    symbol = Column(String(20))  # Trading pair
    side = Column(String(10))  # 'long' or 'short'
    size = Column(Numeric(30, 8))
    entry_price = Column(Numeric(20, 8))
    current_price = Column(Numeric(20, 8))
    unrealized_pnl = Column(Numeric(30, 8))
    strategy_name = Column(String(100))
    entry_time = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'account_id': self.account_id,
            'symbol': self.symbol,
            'side': self.side,
            'size': float(self.size) if self.size else 0,
            'entry_price': float(self.entry_price) if self.entry_price else 0,
            'current_price': float(self.current_price) if self.current_price else 0,
            'unrealized_pnl': float(self.unrealized_pnl) if self.unrealized_pnl else 0,
            'strategy_name': self.strategy_name,
            'entry_time': self.entry_time.isoformat() if self.entry_time else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

