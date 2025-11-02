"""Database models for strategy backtest results and optimal parameters."""
from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, Text
from sqlalchemy.sql import func
from datetime import datetime

from backend.models.base import Base


class BacktestResult(Base):
    """Model for storing backtest results."""
    __tablename__ = 'backtest_results'
    
    id = Column(Integer, primary_key=True)
    strategy_name = Column(String(100), nullable=False, index=True)
    dataset_name = Column(String(100), index=True)
    period_start = Column(DateTime(timezone=True))
    period_end = Column(DateTime(timezone=True))
    split_type = Column(String(20))  # 'is' (in-sample) or 'oos' (out-of-sample)
    parameters = Column(JSON)  # Strategy parameters used
    metrics = Column(JSON)  # Backtest metrics
    trades_count = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'strategy_name': self.strategy_name,
            'dataset_name': self.dataset_name,
            'period_start': self.period_start.isoformat() if self.period_start else None,
            'period_end': self.period_end.isoformat() if self.period_end else None,
            'split_type': self.split_type,
            'parameters': self.parameters,
            'metrics': self.metrics,
            'trades_count': self.trades_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class OptimalParameters(Base):
    """Model for storing optimal parameters from walk-forward optimization."""
    __tablename__ = 'optimal_parameters'
    
    id = Column(Integer, primary_key=True)
    strategy_name = Column(String(100), nullable=False, index=True)
    dataset_name = Column(String(100), index=True)
    validation_period_start = Column(DateTime(timezone=True))
    validation_period_end = Column(DateTime(timezone=True))
    parameters = Column(JSON, nullable=False)  # Optimal parameters
    validation_metrics = Column(JSON)  # Out-of-sample metrics
    train_metrics = Column(JSON)  # In-sample metrics (optional)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'strategy_name': self.strategy_name,
            'dataset_name': self.dataset_name,
            'validation_period_start': self.validation_period_start.isoformat() if self.validation_period_start else None,
            'validation_period_end': self.validation_period_end.isoformat() if self.validation_period_end else None,
            'parameters': self.parameters,
            'validation_metrics': self.validation_metrics,
            'train_metrics': self.train_metrics,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

