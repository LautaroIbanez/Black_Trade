#!/usr/bin/env python3
"""Initialize execution system with orchestrator and coordinator."""
import os
import sys
from pathlib import Path
import logging

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from recommendation.orchestrator import SignalOrchestrator
from backend.execution.engine import ExecutionEngine
from backend.execution.coordinator import ExecutionCoordinator
from backend.api.routes.execution import set_execution_coordinator

# Import adapters
from backend.integrations.binance_adapter import BinanceAdapter
from backend.integrations.simulated_adapter import SimulatedAdapter

# Import risk engine
from backend.risk.engine import RiskEngine, RiskLimits

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init_execution_system(
    use_simulated_adapter: bool = True,
    use_risk_engine: bool = True,
    max_capital_per_strategy: dict = None,
):
    """
    Initialize complete execution system.
    
    Args:
        use_simulated_adapter: If True, use simulated adapter
        use_risk_engine: If True, initialize with risk engine
        max_capital_per_strategy: Max capital % per strategy
    """
    # Initialize exchange adapter
    if use_simulated_adapter or not os.getenv('BINANCE_API_KEY'):
        logger.info("Using simulated adapter for execution")
        adapter = SimulatedAdapter(initial_capital=10000.0)
    else:
        logger.info("Using Binance adapter for execution")
        adapter = BinanceAdapter(testnet=os.getenv('BINANCE_TESTNET', 'false').lower() == 'true')
    
    # Initialize risk engine if requested
    risk_engine = None
    if use_risk_engine:
        limits = RiskLimits(
            max_exposure_pct=float(os.getenv('MAX_EXPOSURE_PCT', '80.0')),
            max_position_pct=float(os.getenv('MAX_POSITION_PCT', '25.0')),
            max_drawdown_pct=float(os.getenv('MAX_DRAWDOWN_PCT', '20.0')),
            daily_loss_limit_pct=float(os.getenv('DAILY_LOSS_LIMIT_PCT', '5.0')),
            var_limit_1d_95=float(os.getenv('VAR_LIMIT_1D_95', '0.03')),
            var_limit_1w_95=float(os.getenv('VAR_LIMIT_1W_95', '0.10')),
        )
        risk_engine = RiskEngine(exchange_adapter=adapter, risk_limits=limits)
        logger.info("Risk engine initialized")
    
    # Initialize signal orchestrator
    orchestrator = SignalOrchestrator(
        risk_engine=risk_engine,
        max_capital_per_strategy=max_capital_per_strategy or {},
    )
    logger.info("Signal orchestrator initialized")
    
    # Initialize execution engine
    execution_engine = ExecutionEngine(
        exchange_adapter=adapter,
        max_retries=int(os.getenv('ORDER_MAX_RETRIES', '3')),
        retry_delay=int(os.getenv('ORDER_RETRY_DELAY', '5')),
        order_timeout=int(os.getenv('ORDER_TIMEOUT', '300')),
    )
    logger.info("Execution engine initialized")
    
    # Initialize execution coordinator
    coordinator = ExecutionCoordinator(
        execution_engine=execution_engine,
        max_capital_per_strategy=max_capital_per_strategy or {},
        prevent_opposite_signals=os.getenv('PREVENT_OPPOSITE_SIGNALS', 'true').lower() == 'true',
        max_simultaneous_orders=int(os.getenv('MAX_SIMULTANEOUS_ORDERS', '5')),
    )
    logger.info("Execution coordinator initialized")
    
    # Set global coordinator for API
    set_execution_coordinator(coordinator)
    
    logger.info("Execution system fully initialized")
    
    return {
        'orchestrator': orchestrator,
        'execution_engine': execution_engine,
        'coordinator': coordinator,
        'risk_engine': risk_engine,
        'adapter': adapter,
    }


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Initialize execution system')
    parser.add_argument('--real', action='store_true', help='Use real Binance adapter')
    parser.add_argument('--no-risk', action='store_true', help='Disable risk engine')
    
    args = parser.parse_args()
    
    components = init_execution_system(
        use_simulated_adapter=not args.real,
        use_risk_engine=not args.no_risk,
    )
    
    print("\n✅ Execution system initialized successfully!")
    print(f"  Adapter: {'Simulated' if args.real else 'Real'}")
    print(f"  Risk Engine: {'Enabled' if components['risk_engine'] else 'Disabled'}")
    print(f"  Coordinator: Ready")
    print(f"  Execution Engine: Ready")

