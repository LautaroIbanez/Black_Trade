"""Backtest engine for running strategy backtests."""
import pandas as pd
from typing import List, Dict, Any
from strategies.strategy_base import StrategyBase


class BacktestEngine:
    """Engine for running backtests on strategies."""
    
    def __init__(self):
        """Initialize backtest engine."""
        pass
    
    def run_backtest(self, strategy: StrategyBase, data: pd.DataFrame, timeframe: str) -> Dict[str, Any]:
        """Run backtest for a strategy on given data."""
        metrics = strategy.backtest(data)
        metrics['timeframe'] = timeframe
        metrics['strategy_name'] = strategy.name
        return metrics
    
    def run_multiple_backtests(self, strategies: List[StrategyBase], data: pd.DataFrame, timeframe: str) -> List[Dict[str, Any]]:
        """Run backtests for multiple strategies."""
        results = []
        for strategy in strategies:
            try:
                result = self.run_backtest(strategy, data, timeframe)
                results.append(result)
            except Exception as e:
                print(f"Error running backtest for {strategy.name}: {e}")
                continue
        return results
    
    def rank_strategies(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Rank strategies based on weighted metrics."""
        for result in results:
            # Calculate composite score
            score = 0.0
            if result.get('win_rate', 0) > 0:
                score += result['win_rate'] * 0.3
            if result.get('profit_factor', 0) > 0:
                score += min(result['profit_factor'] / 2.0, 1.0) * 0.3
            if result.get('net_pnl', 0) > 0:
                score += min(abs(result['net_pnl']) / 10000, 1.0) * 0.2
            if result.get('expectancy', 0) > 0:
                score += min(result['expectancy'] / 100, 1.0) * 0.2
            result['score'] = score
        
        # Sort by score descending
        results.sort(key=lambda x: x.get('score', 0), reverse=True)
        return results

