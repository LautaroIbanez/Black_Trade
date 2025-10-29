"""Configurable strategy registry for enabling/disabling strategies."""
import json
import os
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from strategies.strategy_base import StrategyBase
from strategies.ema_rsi_strategy import EMARSIStrategy
from strategies.ichimoku_strategy import IchimokuStrategy
from strategies.breakout_strategy import BreakoutStrategy
from strategies.mean_reversion_strategy import MeanReversionStrategy
from strategies.momentum_strategy import MomentumStrategy
from strategies.bollinger_breakout_strategy import BollingerBreakoutStrategy
from strategies.ichimoku_trend_strategy import IchimokuTrendStrategy
from strategies.rsi_divergence_strategy import RSIDivergenceStrategy
from strategies.macd_crossover_strategy import MACDCrossoverStrategy
from strategies.stochastic_strategy import StochasticStrategy
from strategies.crypto_rotation_strategy import CryptoRotationStrategy
from strategies.order_flow_strategy import OrderFlowStrategy


@dataclass
class StrategyConfig:
    """Configuration for a strategy."""
    name: str
    enabled: bool
    class_name: str
    parameters: Dict[str, Any]
    commission: float = 0.001
    slippage: float = 0.0005
    description: str = ""


class StrategyRegistry:
    """Registry for managing strategy configurations."""
    
    def __init__(self, config_file: str = "backend/config/strategies.json"):
        """Initialize strategy registry with configuration file."""
        self.config_file = config_file
        self.strategies: Dict[str, StrategyConfig] = {}
        self.strategy_classes = {
            'EMARSIStrategy': EMARSIStrategy,
            'IchimokuStrategy': IchimokuStrategy,
            'BreakoutStrategy': BreakoutStrategy,
            'MeanReversionStrategy': MeanReversionStrategy,
            'MomentumStrategy': MomentumStrategy,
            'BollingerBreakoutStrategy': BollingerBreakoutStrategy,
            'IchimokuTrendStrategy': IchimokuTrendStrategy,
            'RSIDivergenceStrategy': RSIDivergenceStrategy,
            'MACDCrossoverStrategy': MACDCrossoverStrategy,
            'StochasticStrategy': StochasticStrategy,
            'CryptoRotationStrategy': CryptoRotationStrategy,
            'OrderFlowStrategy': OrderFlowStrategy
        }
        self._load_config()
    
    def _load_config(self):
        """Load strategy configurations from file."""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    config_data = json.load(f)
                    for strategy_data in config_data.get('strategies', []):
                        config = StrategyConfig(**strategy_data)
                        self.strategies[config.name] = config
            except (json.JSONDecodeError, KeyError, TypeError) as e:
                print(f"Error loading strategy config: {e}")
                self._create_default_config()
        else:
            self._create_default_config()
    
    def _create_default_config(self):
        """Create default strategy configuration."""
        default_strategies = [
            StrategyConfig(
                name="EMA_RSI",
                enabled=True,
                class_name="EMARSIStrategy",
                parameters={"fast_period": 12, "slow_period": 26, "rsi_period": 14, "rsi_oversold": 30, "rsi_overbought": 70},
                commission=0.001,
                slippage=0.0005,
                description="EMA Crossover with RSI filter"
            ),
            StrategyConfig(
                name="Ichimoku_ADX",
                enabled=True,
                class_name="IchimokuStrategy",
                parameters={"conversion_period": 9, "base_period": 26, "leading_span_b": 52, "displacement": 26, "adx_period": 14, "adx_threshold": 25},
                commission=0.001,
                slippage=0.0005,
                description="Ichimoku Cloud with ADX confirmation"
            ),
            StrategyConfig(
                name="Breakout",
                enabled=True,
                class_name="BreakoutStrategy",
                parameters={"lookback": 20, "multiplier": 2.0, "trailing_percent": 0.01},
                commission=0.001,
                slippage=0.0005,
                description="Volatility breakout with trailing stop"
            ),
            StrategyConfig(
                name="Mean_Reversion",
                enabled=True,
                class_name="MeanReversionStrategy",
                parameters={"period": 20, "bb_std": 2.0, "rsi_period": 14},
                commission=0.001,
                slippage=0.0005,
                description="Mean reversion with Bollinger Bands and RSI"
            ),
            StrategyConfig(
                name="Momentum",
                enabled=True,
                class_name="MomentumStrategy",
                parameters={"rsi_period": 14, "macd_fast": 12, "macd_slow": 26, "macd_signal": 9},
                commission=0.001,
                slippage=0.0005,
                description="Momentum strategy with MACD and RSI"
            ),
            StrategyConfig(
                name="CryptoRotation",
                enabled=False,
                class_name="CryptoRotationStrategy",
                parameters={"lookback": 50},
                commission=0.001,
                slippage=0.0005,
                description="Rotation proxy based on relative strength vs EMA"
            ),
            StrategyConfig(
                name="OrderFlow",
                enabled=False,
                class_name="OrderFlowStrategy",
                parameters={"vol_mult": 1.8, "lookback": 30},
                commission=0.001,
                slippage=0.0005,
                description="Order-flow proxy using abnormal volume and price delta"
            )
        ]
        
        for strategy in default_strategies:
            self.strategies[strategy.name] = strategy
        
        self._save_config()
    
    def _save_config(self):
        """Save strategy configurations to file."""
        os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
        
        config_data = {
            "strategies": [asdict(strategy) for strategy in self.strategies.values()]
        }
        
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config_data, f, indent=2)
        except Exception as e:
            print(f"Error saving strategy config: {e}")
    
    def get_enabled_strategies(self) -> List[StrategyBase]:
        """Get list of enabled strategy instances."""
        enabled_strategies = []
        
        for config in self.strategies.values():
            if config.enabled and config.class_name in self.strategy_classes:
                try:
                    strategy_class = self.strategy_classes[config.class_name]
                    strategy = strategy_class(
                        commission=config.commission,
                        slippage=config.slippage,
                        **config.parameters
                    )
                    enabled_strategies.append(strategy)
                except Exception as e:
                    print(f"Error creating strategy {config.name}: {e}")
                    continue
        
        return enabled_strategies
    
    def get_all_strategies(self) -> List[StrategyBase]:
        """Get list of all strategy instances (enabled and disabled)."""
        all_strategies = []
        
        for config in self.strategies.values():
            if config.class_name in self.strategy_classes:
                try:
                    strategy_class = self.strategy_classes[config.class_name]
                    strategy = strategy_class(
                        commission=config.commission,
                        slippage=config.slippage,
                        **config.parameters
                    )
                    all_strategies.append(strategy)
                except Exception as e:
                    print(f"Error creating strategy {config.name}: {e}")
                    continue
        
        return all_strategies
    
    def enable_strategy(self, name: str) -> bool:
        """Enable a strategy by name."""
        if name in self.strategies:
            self.strategies[name].enabled = True
            self._save_config()
            return True
        return False
    
    def disable_strategy(self, name: str) -> bool:
        """Disable a strategy by name."""
        if name in self.strategies:
            self.strategies[name].enabled = False
            self._save_config()
            return True
        return False
    
    def update_strategy_config(self, name: str, **kwargs) -> bool:
        """Update strategy configuration."""
        if name in self.strategies:
            config = self.strategies[name]
            for key, value in kwargs.items():
                if hasattr(config, key):
                    setattr(config, key, value)
            self._save_config()
            return True
        return False
    
    def get_strategy_config(self, name: str) -> Optional[StrategyConfig]:
        """Get strategy configuration by name."""
        return self.strategies.get(name)
    
    def list_strategies(self) -> List[Dict[str, Any]]:
        """List all strategies with their configurations."""
        return [asdict(config) for config in self.strategies.values()]
    
    def add_strategy(self, config: StrategyConfig) -> bool:
        """Add a new strategy configuration."""
        if config.name not in self.strategies and config.class_name in self.strategy_classes:
            self.strategies[config.name] = config
            self._save_config()
            return True
        return False
    
    def remove_strategy(self, name: str) -> bool:
        """Remove a strategy configuration."""
        if name in self.strategies:
            del self.strategies[name]
            self._save_config()
            return True
        return False
    
    def reload_config(self):
        """Reload configuration from file."""
        self._load_config()
    
    def get_strategy_info(self) -> Dict[str, Any]:
        """Get information about all strategies."""
        info = {
            "total_strategies": len(self.strategies),
            "enabled_strategies": len([s for s in self.strategies.values() if s.enabled]),
            "disabled_strategies": len([s for s in self.strategies.values() if not s.enabled]),
            "available_classes": list(self.strategy_classes.keys()),
            "strategies": self.list_strategies()
        }
        return info


# Global registry instance
strategy_registry = StrategyRegistry()
