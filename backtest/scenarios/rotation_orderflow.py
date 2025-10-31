"""Backtest scenarios for CryptoRotation and OrderFlow strategies."""
from typing import Dict, List
from strategies.crypto_rotation_strategy import CryptoRotationStrategy
from strategies.order_flow_strategy import OrderFlowStrategy
from data.feeds.rotation_loader import (
    load_rotation_universe, 
    default_universe, 
    align_universe_timestamps
)


def run_rotation_scenario(symbols: List[str] = None, timeframe: str = "1h", 
                         ranking_method: str = "strength", min_divergence: float = 0.02) -> Dict:
    """Run rotation scenario with multi-asset strategy.
    
    This scenario:
    1. Loads multiple symbols from the universe
    2. Aligns timestamps across all symbols
    3. Runs backtest for each symbol using rotation strategy
    4. Aggregates results across all symbols
    
    Args:
        symbols: List of symbols to include (None = use default)
        timeframe: Timeframe for data
        ranking_method: Method for ranking ("strength", "returns", "sharpe")
        min_divergence: Minimum divergence threshold
        
    Returns:
        Dictionary with aggregated results or error message
    """
    symbols = symbols or default_universe()
    universe = load_rotation_universe(symbols, timeframe)
    if not universe:
        return {"error": "No data available for symbols"}
    
    # Align timestamps
    universe = align_universe_timestamps(universe)
    if not universe:
        return {"error": "Failed to align timestamps"}
    
    # Initialize strategy with full universe
    strat = CryptoRotationStrategy(
        lookback=50,
        universe=list(universe.keys()),
        ranking_method=ranking_method,
        min_divergence=min_divergence,
        top_n=1,
        bottom_n=1,
        rebalance_periods=5
    )
    
    # Run backtest for each symbol
    all_results = []
    for sym, df in universe.items():
        if df is None or df.empty:
            continue
        
        # Set current symbol for ranking context
        strat._current_symbol = sym
        try:
            # Generate signals with current symbol context
            signals_df = strat.generate_signals(df, timeframe=timeframe, current_symbol=sym)
            trades = strat.generate_trades(signals_df)
            
            # Calculate metrics for this symbol
            if trades:
                total_trades = len(trades)
                winning_trades = [t for t in trades if t.get('pnl', 0) > 0]
                win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0.0
                total_pnl = sum(t.get('pnl', 0) for t in trades)
            else:
                total_trades = 0
                win_rate = 0.0
                total_pnl = 0.0
            
            all_results.append({
                "symbol": sym,
                "total_trades": total_trades,
                "win_rate": win_rate,
                "net_pnl": total_pnl
            })
        except Exception as e:
            all_results.append({
                "symbol": sym,
                "error": str(e)
            })
    
    if not all_results:
        return {"error": "No valid results from any symbol"}
    
    # Aggregate results
    total_trades_all = sum(r.get("total_trades", 0) for r in all_results)
    total_pnl_all = sum(r.get("net_pnl", 0) for r in all_results)
    avg_win_rate = sum(r.get("win_rate", 0) for r in all_results) / len(all_results) if all_results else 0.0
    
    return {
        "total_symbols": len(all_results),
        "total_trades": total_trades_all,
        "average_win_rate": avg_win_rate,
        "net_pnl": total_pnl_all,
        "symbol_results": all_results
    }


def run_orderflow_scenario(symbols: List[str] = None, timeframe: str = "1h") -> Dict:
    symbols = symbols or default_universe()
    universe = load_rotation_universe(symbols, timeframe)
    # Use first available symbol for simple scenario
    for sym in symbols:
        df = universe.get(sym)
        if df is not None and not df.empty:
            strat = OrderFlowStrategy(vol_mult=1.5, lookback=30)
            return strat.backtest(df)
    return {"error": "No data"}


