"""Configuration schema for dynamic strategy parameters."""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, validator
from enum import Enum


class RiskProfile(str, Enum):
    """Risk profile types."""
    CONSERVATIVE = "conservative"
    BALANCED = "balanced"
    AGGRESSIVE = "aggressive"


class StrategyConfig(BaseModel):
    """Base configuration schema for strategies."""
    
    # Strategy identification
    strategy_name: str
    version: str = "1.0.0"
    
    # Risk management
    stop_loss_pct: Optional[float] = Field(None, ge=0.0, le=1.0)
    take_profit_pct: Optional[float] = Field(None, ge=0.0, le=1.0)
    position_size_pct: float = Field(0.1, ge=0.0, le=1.0)
    risk_profile: RiskProfile = RiskProfile.BALANCED
    
    # Trading costs
    commission: float = Field(0.0002, ge=0.0)
    slippage: float = Field(0.0001, ge=0.0)
    
    # Strategy-specific parameters
    parameters: Dict[str, Any] = Field(default_factory=dict)
    
    @validator('stop_loss_pct', 'take_profit_pct')
    def validate_risk_levels(cls, v, values):
        """Validate risk levels make sense."""
        if v is not None and 'take_profit_pct' in values:
            tp = values.get('take_profit_pct')
            if tp is not None and v >= tp:
                raise ValueError("Stop loss must be less than take profit")
        return v
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'strategy_name': self.strategy_name,
            'version': self.version,
            'stop_loss_pct': self.stop_loss_pct,
            'take_profit_pct': self.take_profit_pct,
            'position_size_pct': self.position_size_pct,
            'risk_profile': self.risk_profile.value,
            'commission': self.commission,
            'slippage': self.slippage,
            'parameters': self.parameters,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StrategyConfig':
        """Create from dictionary."""
        return cls(**data)
    
    def update_parameters(self, new_params: Dict[str, Any]):
        """Update strategy-specific parameters."""
        self.parameters.update(new_params)
    
    def get_parameter_space(self) -> Dict[str, List[Any]]:
        """Get parameter space for optimization (to be overridden by strategies)."""
        return {}


class EMARSIConfig(StrategyConfig):
    """Configuration for EMA+RSI strategy."""
    
    # Technical parameters
    fast_period: int = Field(12, ge=1, le=200)
    slow_period: int = Field(26, ge=1, le=200)
    rsi_period: int = Field(14, ge=2, le=100)
    rsi_oversold: int = Field(30, ge=0, le=50)
    rsi_overbought: int = Field(70, ge=50, le=100)
    signal_persistence: int = Field(3, ge=1, le=20)
    volume_confirmation: bool = True
    
    def get_parameter_space(self) -> Dict[str, List[Any]]:
        """Define parameter space for optimization."""
        return {
            'fast_period': list(range(8, 21, 2)),
            'slow_period': list(range(20, 35, 2)),
            'rsi_period': [12, 14, 16, 18],
            'rsi_oversold': list(range(25, 36, 5)),
            'rsi_overbought': list(range(65, 76, 5)),
            'signal_persistence': list(range(2, 6)),
        }


def create_strategy_config(strategy_name: str, config_dict: Dict[str, Any]) -> StrategyConfig:
    """Factory function to create appropriate config based on strategy name."""
    if strategy_name == "EMA_RSI":
        return EMARSIConfig(strategy_name=strategy_name, **config_dict)
    else:
        # Generic config for unknown strategies
        return StrategyConfig(strategy_name=strategy_name, **config_dict)

