"""Backtest engine for running strategy backtests."""
import math
from dataclasses import dataclass
import pandas as pd
from typing import List, Dict, Any, Tuple, Optional
from strategies.strategy_base import StrategyBase
from backtest.analysis import compute_composite_score


@dataclass
class CostModel:
    """Exchange cost and spread configuration."""
    commission_pct: float = 0.0002   # 0.02%
    slippage_pct: float = 0.0001     # 0.01%
    spread_mode: str = "fixed"       # "fixed" or "atr"
    spread_atr_multiplier: float = 0.25  # if spread_mode == "atr", use this * ATR/current_price


class BacktestEngine:
    """Engine for running backtests on strategies with equity, percent metrics, and OOS analysis."""
    
    def __init__(
        self,
        initial_capital: float = 10000.0,
        position_size_pct: float = 0.1,
        cost_model: Optional[CostModel] = None,
    ):
        """Initialize backtest engine.
        
        Args:
            initial_capital: Starting equity in quote currency.
            position_size_pct: Fraction of current equity allocated per trade (0-1).
            cost_model: Optional cost model to override per-strategy defaults.
        """
        self.initial_capital = initial_capital
        self.position_size_pct = max(0.0, min(1.0, position_size_pct))
        self.cost_model = cost_model or CostModel()
    
    def _apply_cost_overrides(self, strategy: StrategyBase):
        """Override strategy costs from engine cost model, if provided."""
        if self.cost_model is not None:
            strategy.commission = self.cost_model.commission_pct
            # Use slippage as base; spread handled in equity simulation phase
            strategy.slippage = self.cost_model.slippage_pct

    def _equity_curve_from_trades(
        self,
        trades: List[Dict[str, Any]],
        df: pd.DataFrame,
    ) -> Tuple[List[float], List[float], float, float]:
        """Build equity curve, returns %, and drawdowns from trades.
        
        Uses position sizing as fraction of current equity and applies variable spread costs if configured.
        """
        if not trades:
            return [self.initial_capital], [0.0], 0.0, 0.0

        equity = self.initial_capital
        equity_curve: List[float] = [equity]
        returns_pct: List[float] = [0.0]
        peak: float = equity
        max_drawdown_abs: float = 0.0
        max_drawdown_pct: float = 0.0

        # Index df by timestamp for quick ATR lookup
        ts_col = 'timestamp' if 'timestamp' in df.columns else None
        # Precompute ATR if needed for spread model
        atr_series = None
        if self.cost_model.spread_mode == 'atr':
            high_low = df['high'] - df['low']
            high_close = (df['high'] - df['close'].shift()).abs()
            low_close = (df['low'] - df['close'].shift()).abs()
            true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            atr_series = true_range.rolling(window=14).mean()
            if ts_col:
                atr_series.index = df['timestamp']

        for trade in trades:
            trade_pnl = trade.get('net_pnl', trade.get('pnl', 0.0))
            entry_price = trade.get('entry_price', 0.0)
            exit_price = trade.get('exit_price', 0.0)

            # Determine variable spread cost if configured
            extra_spread_cost = 0.0
            if self.cost_model.spread_mode == 'atr' and ts_col and atr_series is not None and entry_price and exit_price:
                entry_time = trade.get('entry_time')
                if entry_time in atr_series.index:
                    atr = float(atr_series.loc[entry_time])
                    price = float(entry_price)
                    if price > 0 and not math.isnan(atr):
                        spread_pct = min(max((atr / price) * self.cost_model.spread_atr_multiplier, 0.0), 0.02)
                        extra_spread_cost = (entry_price + exit_price) * spread_pct

            # Determine position size in units based on equity
            notional = equity * self.position_size_pct
            units = notional / entry_price if entry_price > 0 else 0.0
            scaled_pnl = trade_pnl * units

            # Apply extra spread cost
            scaled_pnl -= extra_spread_cost

            new_equity = equity + scaled_pnl
            ret = (new_equity / equity) - 1.0 if equity > 0 else 0.0
            equity = new_equity
            equity_curve.append(equity)
            returns_pct.append(ret)
            if equity > peak:
                peak = equity
            dd_abs = peak - equity
            dd_pct = dd_abs / peak if peak > 0 else 0.0
            max_drawdown_abs = max(max_drawdown_abs, dd_abs)
            max_drawdown_pct = max(max_drawdown_pct, dd_pct)

        return equity_curve, returns_pct, max_drawdown_abs, max_drawdown_pct

    def run_backtest(self, strategy: StrategyBase, data: pd.DataFrame, timeframe: str) -> Dict[str, Any]:
        """Run backtest for a strategy on given data with normalized metrics and equity curve."""
        self._apply_cost_overrides(strategy)
        metrics = strategy.backtest(data)
        metrics['timeframe'] = timeframe
        metrics['strategy_name'] = strategy.name

        trades = metrics.get('trades') or []
        equity_curve, returns_pct, dd_abs_eq, dd_pct = self._equity_curve_from_trades(trades, data)
        metrics['initial_capital'] = self.initial_capital
        metrics['position_size_pct'] = self.position_size_pct
        metrics['equity_curve'] = equity_curve
        metrics['returns_pct'] = returns_pct
        metrics['max_drawdown_pct'] = dd_pct
        if equity_curve:
            metrics['total_return_pct'] = (equity_curve[-1] / equity_curve[0]) - 1.0
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
    
    def split_train_test(self, df: pd.DataFrame, split: float = 0.7) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Split a dataframe into train/test by chronological order."""
        split = max(0.1, min(0.95, split))
        n = len(df)
        idx = int(n * split)
        train = df.iloc[:idx].copy()
        test = df.iloc[idx:].copy()
        return train, test

    def run_backtest_with_split(self, strategy: StrategyBase, df: pd.DataFrame, timeframe: str, split: float = 0.7) -> Dict[str, Any]:
        """Run backtest with train/test split and return separated metrics."""
        train, test = self.split_train_test(df, split)
        in_sample = self.run_backtest(strategy, train, timeframe)
        out_sample = self.run_backtest(strategy, test, timeframe)
        return {
            'strategy_name': strategy.name,
            'timeframe': timeframe,
            'split': split,
            'in_sample': in_sample,
            'out_of_sample': out_sample,
        }

    def run_walk_forward(
        self,
        strategy: StrategyBase,
        df: pd.DataFrame,
        timeframe: str,
        train_window: int,
        test_window: int,
        step: int,
    ) -> Dict[str, Any]:
        """Run walk-forward analysis with rolling train/test windows."""
        n = len(df)
        segments: List[Dict[str, Any]] = []
        start = 0
        while start + train_window + test_window <= n:
            train = df.iloc[start:start + train_window]
            test = df.iloc[start + train_window:start + train_window + test_window]
            in_sample = self.run_backtest(strategy, train, timeframe)
            out_sample = self.run_backtest(strategy, test, timeframe)
            segments.append({
                'start_idx': int(start),
                'train_window': int(train_window),
                'test_window': int(test_window),
                'in_sample': in_sample,
                'out_of_sample': out_sample,
            })
            start += max(1, step)

        summary = {
            'num_segments': len(segments),
            'avg_in_sample_return_pct': float(pd.Series([s['in_sample']['total_return_pct'] for s in segments]).mean()) if segments else 0.0,
            'avg_out_sample_return_pct': float(pd.Series([s['out_of_sample']['total_return_pct'] for s in segments]).mean()) if segments else 0.0,
        }
        return {
            'strategy_name': strategy.name,
            'timeframe': timeframe,
            'walk_forward': segments,
            'summary': summary,
        }

    def rank_strategies(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Rank strategies based on composite score (no hard 1.0 caps).

        Combines total return, relative drawdown, and trade count (plus stability metrics)
        before any scaling. Strategies with zero trades are penalized.
        """
        for result in results:
            result['score'] = compute_composite_score(result)
        
        # Sort by score descending
        results.sort(key=lambda x: x.get('score', 0), reverse=True)
        return results

