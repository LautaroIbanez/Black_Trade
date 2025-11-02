#!/usr/bin/env python3
"""Initialize risk management system with exchange adapter."""
import os
import sys
from pathlib import Path
import logging

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.integrations.binance_adapter import BinanceAdapter
from backend.integrations.simulated_adapter import SimulatedAdapter
from backend.risk.engine import RiskEngine, RiskLimits
from backend.risk.monitor import RiskMonitor
from backend.risk.alerts import AlertManager
from backend.api.routes.risk import set_risk_engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init_risk_system(use_simulated: bool = True):
    """
    Initialize risk management system.
    
    Args:
        use_simulated: If True, use simulated adapter (default: True)
    """
    # Choose adapter
    if use_simulated or not os.getenv('BINANCE_API_KEY'):
        logger.info("Using simulated adapter for risk management")
        adapter = SimulatedAdapter(initial_capital=10000.0)
    else:
        logger.info("Using Binance adapter for risk management")
        adapter = BinanceAdapter(testnet=os.getenv('BINANCE_TESTNET', 'false').lower() == 'true')
    
    # Configure risk limits from environment
    limits = RiskLimits(
        max_exposure_pct=float(os.getenv('MAX_EXPOSURE_PCT', '80.0')),
        max_position_pct=float(os.getenv('MAX_POSITION_PCT', '25.0')),
        max_drawdown_pct=float(os.getenv('MAX_DRAWDOWN_PCT', '20.0')),
        daily_loss_limit_pct=float(os.getenv('DAILY_LOSS_LIMIT_PCT', '5.0')),
        var_limit_1d_95=float(os.getenv('VAR_LIMIT_1D_95', '0.03')),
        var_limit_1w_95=float(os.getenv('VAR_LIMIT_1W_95', '0.10')),
    )
    
    # Create risk engine
    engine = RiskEngine(
        exchange_adapter=adapter,
        risk_limits=limits,
    )
    
    # Set global instance for API
    set_risk_engine(engine)
    
    logger.info("Risk management system initialized")
    logger.info(f"Limits: max_exposure={limits.max_exposure_pct}%, max_drawdown={limits.max_drawdown_pct}%")
    
    return engine, adapter


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Initialize risk management system')
    parser.add_argument('--real', action='store_true', help='Use real Binance adapter (default: simulated)')
    
    args = parser.parse_args()
    
    engine, adapter = init_risk_system(use_simulated=not args.real)
    
    # Test getting metrics
    metrics = engine.get_risk_metrics()
    print(f"\nInitial Risk Metrics:")
    print(f"  Capital: ${metrics.total_capital:,.2f}")
    print(f"  Equity: ${metrics.equity:,.2f}")
    print(f"  Exposure: {metrics.exposure_pct:.2f}%")
    print(f"  Drawdown: {metrics.current_drawdown_pct:.2f}%")

