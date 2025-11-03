"""Walk-forward analysis engine for strategy validation."""
import logging
from typing import List, Dict, Any, Optional, Tuple
import pandas as pd
from datetime import datetime, timedelta
import numpy as np

from strategies.strategy_base import StrategyBase
from backtest.engine import BacktestEngine, CostModel
from backtest.analysis import compute_composite_score

logger = logging.getLogger(__name__)


class WalkForwardEngine:
    """Engine for walk-forward optimization and validation."""
    
    def __init__(
        self,
        train_size: float = 0.7,
        test_size: float = 0.3,
        step_size: float = 0.1,
        min_train_periods: int = 100,
        initial_capital: float = 10000.0,
        position_size_pct: float = 0.1,
        cost_model: Optional[CostModel] = None,
    ):
        """
        Initialize walk-forward engine.
        
        Args:
            train_size: Fraction of data for training (0-1)
            test_size: Fraction of data for testing (0-1)
            step_size: Fraction to slide forward each iteration (0-1)
            min_train_periods: Minimum periods required for training
            initial_capital: Starting capital
            position_size_pct: Position size as fraction of equity
            cost_model: Cost model configuration
        """
        self.train_size = train_size
        self.test_size = test_size
        self.step_size = step_size
        self.min_train_periods = min_train_periods
        self.backtest_engine = BacktestEngine(
            initial_capital=initial_capital,
            position_size_pct=position_size_pct,
            cost_model=cost_model or CostModel()
        )
        self.logger = logging.getLogger(__name__)
    
    def split_data(
        self, 
        df: pd.DataFrame, 
        train_start: int, 
        train_end: int,
        test_start: int,
        test_end: int
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Split data into train and test sets."""
        train_df = df[(df.index >= train_start) & (df.index < train_end)].copy()
        test_df = df[(df.index >= test_start) & (df.index < test_end)].copy()
        return train_df, test_df
    
    def compute_metrics(
        self,
        trades: List[Dict],
        equity_curve: List[float],
        returns_pct: List[float],
        max_drawdown_pct: float,
        period_start: datetime,
        period_end: datetime,
    ) -> Dict[str, Any]:
        """Compute comprehensive metrics from backtest results."""
        total_trades = len(trades)
        
        if total_trades == 0:
            return {
                'total_trades': 0,
                'total_return_pct': 0.0,
                'max_drawdown_pct': 0.0,
                'sharpe_ratio': 0.0,
                'calmar_ratio': 0.0,
                'win_rate': 0.0,
                'profit_factor': 0.0,
                'expectancy': 0.0,
                'period_start': period_start.isoformat(),
                'period_end': period_end.isoformat(),
            }
        
        # Calculate returns
        total_return_pct = (equity_curve[-1] / equity_curve[0] - 1) * 100 if equity_curve else 0.0
        
        # Calculate period duration for annualization
        period_days = (period_end - period_start).days if period_end > period_start else 1
        annualization_factor = 365.0 / period_days if period_days > 0 else 1.0
        
        # Annualized return
        annualized_return = ((1 + total_return_pct / 100) ** annualization_factor - 1) * 100
        
        # Sharpe Ratio (assuming risk-free rate = 0)
        returns_array = np.array(returns_pct)
        if len(returns_array) > 1 and returns_array.std() > 0:
            sharpe_ratio = (returns_array.mean() / returns_array.std()) * np.sqrt(annualization_factor * 252)
        else:
            sharpe_ratio = 0.0
        
        # Calmar Ratio (Return / Max Drawdown)
        calmar_ratio = annualized_return / max_drawdown_pct if max_drawdown_pct > 0 else 0.0
        
        # Trading metrics
        winning_trades = [t for t in trades if t.get('pnl', 0) > 0]
        losing_trades = [t for t in trades if t.get('pnl', 0) <= 0]
        
        win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0.0
        
        gross_profit = sum(t.get('pnl', 0) for t in winning_trades) if winning_trades else 0.0
        gross_loss = abs(sum(t.get('pnl', 0) for t in losing_trades)) if losing_trades else 0.0
        
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else (gross_profit if gross_profit > 0 else 0.0)
        
        total_pnl = sum(t.get('pnl', 0) for t in trades)
        expectancy = total_pnl / total_trades if total_trades > 0 else 0.0
        
        # Average win/loss ratio
        avg_win = np.mean([t.get('pnl', 0) for t in winning_trades]) if winning_trades else 0.0
        avg_loss = abs(np.mean([t.get('pnl', 0) for t in losing_trades])) if losing_trades else 0.0
        win_loss_ratio = avg_win / avg_loss if avg_loss > 0 else 0.0
        
        return {
            'total_trades': total_trades,
            'total_return_pct': total_return_pct,
            'annualized_return_pct': annualized_return,
            'max_drawdown_pct': max_drawdown_pct,
            'sharpe_ratio': sharpe_ratio,
            'calmar_ratio': calmar_ratio,
            'sortino_ratio': 0.0,  # TODO: Implement Sortino
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'expectancy': expectancy,
            'avg_win_loss_ratio': win_loss_ratio,
            'gross_profit': gross_profit,
            'gross_loss': gross_loss,
            'period_start': period_start.isoformat(),
            'period_end': period_end.isoformat(),
            'period_days': period_days,
            'composite_score': compute_composite_score({
                'total_return_pct': total_return_pct,
                'max_drawdown_pct': max_drawdown_pct,
                'profit_factor': profit_factor,
                'win_rate': win_rate,
                'expectancy': expectancy,
                'total_trades': total_trades,
            })
        }
    
    def run_walk_forward(
        self,
        strategy_class: type,
        df: pd.DataFrame,
        parameter_space: Dict[str, List[Any]],
        optimize_fn: Optional[callable] = None,
    ) -> Dict[str, Any]:
        """
        Run walk-forward optimization.
        
        Args:
            strategy_class: Strategy class (not instance)
            df: Full dataset
            parameter_space: Parameter space for optimization
            optimize_fn: Optional custom optimization function
            
        Returns:
            Dictionary with walk-forward results
        """
        if len(df) < self.min_train_periods:
            raise ValueError(f"Insufficient data: {len(df)} < {self.min_train_periods}")
        
        # Reset index to numeric for easier slicing
        df = df.reset_index(drop=True)
        total_periods = len(df)
        
        # Calculate split sizes
        train_periods = int(total_periods * self.train_size)
        test_periods = int(total_periods * self.test_size)
        step_periods = int(total_periods * self.step_size)
        
        # Ensure minimum train size
        if train_periods < self.min_train_periods:
            train_periods = self.min_train_periods
            test_periods = min(test_periods, total_periods - train_periods)
        
        results = {
            'iterations': [],
            'summary': {},
        }
        
        # Walk forward through data
        current_pos = 0
        iteration = 0
        
        while current_pos + train_periods + test_periods <= total_periods:
            iteration += 1
            
            train_start = current_pos
            train_end = train_start + train_periods
            test_start = train_end
            test_end = test_start + test_periods
            
            train_df = df.iloc[train_start:train_end].copy()
            test_df = df.iloc[test_start:test_end].copy()
            
            # Get timestamps for metrics
            period_start = test_df['timestamp'].iloc[0] if 'timestamp' in test_df.columns else None
            period_end = test_df['timestamp'].iloc[-1] if 'timestamp' in test_df.columns else None
            
            if period_start and isinstance(period_start, (int, float)):
                period_start = datetime.fromtimestamp(period_start / 1000) if period_start > 1e10 else datetime.fromtimestamp(period_start)
            if period_end and isinstance(period_end, (int, float)):
                period_end = datetime.fromtimestamp(period_end / 1000) if period_end > 1e10 else datetime.fromtimestamp(period_end)
            
            self.logger.info(f"Iteration {iteration}: Train[{train_start}:{train_end}], Test[{test_start}:{test_end}]")
            
            # Optimize parameters on training set
            if optimize_fn:
                best_params = optimize_fn(strategy_class, train_df, parameter_space)
            else:
                best_params = self._grid_search_optimize(strategy_class, train_df, parameter_space)
            
            # Validate on test set
            strategy = strategy_class(**best_params)
            test_result = self.backtest_engine.backtest(strategy, test_df)
            
            # Compute metrics
            equity_curve = test_result.get('equity_curve', [])
            returns_pct = test_result.get('returns_pct', [])
            max_dd = test_result.get('max_drawdown_pct', 0.0)
            trades = test_result.get('trades', [])
            
            metrics = self.compute_metrics(
                trades=trades,
                equity_curve=equity_curve,
                returns_pct=returns_pct,
                max_drawdown_pct=max_dd,
                period_start=period_start or datetime.now(),
                period_end=period_end or datetime.now(),
            )
            
            iteration_result = {
                'iteration': iteration,
                'train_start': train_start,
                'train_end': train_end,
                'test_start': test_start,
                'test_end': test_end,
                'optimal_parameters': best_params,
                'metrics': metrics,
            }
            
            results['iterations'].append(iteration_result)
            
            # Slide forward
            current_pos += step_periods
        
        # Compute summary statistics
        if results['iterations']:
            all_metrics = [it['metrics'] for it in results['iterations']]
            
            results['summary'] = {
                'total_iterations': len(results['iterations']),
                'avg_sharpe_ratio': np.mean([m.get('sharpe_ratio', 0) for m in all_metrics]),
                'avg_calmar_ratio': np.mean([m.get('calmar_ratio', 0) for m in all_metrics]),
                'avg_return_pct': np.mean([m.get('total_return_pct', 0) for m in all_metrics]),
                'avg_max_drawdown_pct': np.mean([m.get('max_drawdown_pct', 0) for m in all_metrics]),
                'avg_win_rate': np.mean([m.get('win_rate', 0) for m in all_metrics]),
                'avg_profit_factor': np.mean([m.get('profit_factor', 0) for m in all_metrics]),
                'consistency_score': self._compute_consistency(all_metrics),
            }
        
        return results
    
    def _grid_search_optimize(
        self,
        strategy_class: type,
        train_df: pd.DataFrame,
        parameter_space: Dict[str, List[Any]],
    ) -> Dict[str, Any]:
        """Optimize parameters using grid search on training data."""
        from itertools import product
        
        best_score = float('-inf')
        best_params = {}
        
        # Generate all parameter combinations
        param_names = list(parameter_space.keys())
        param_values = [parameter_space[name] for name in param_names]
        
        total_combinations = np.prod([len(v) for v in param_values])
        self.logger.info(f"Testing {total_combinations} parameter combinations...")
        
        for combination in product(*param_values):
            params = dict(zip(param_names, combination))
            
            try:
                strategy = strategy_class(**params)
                result = self.backtest_engine.backtest(strategy, train_df)
                
                # Use composite score for optimization
                score = compute_composite_score(result)
                
                if score > best_score:
                    best_score = score
                    best_params = params.copy()
                    
            except Exception as e:
                self.logger.warning(f"Error testing parameters {params}: {e}")
                continue
        
        self.logger.info(f"Best parameters: {best_params} (score: {best_score})")
        return best_params
    
    def _compute_consistency(self, metrics_list: List[Dict]) -> float:
        """Compute consistency score (stability across iterations)."""
        if not metrics_list:
            return 0.0
        
        sharpe_ratios = [m.get('sharpe_ratio', 0) for m in metrics_list]
        
        if len(sharpe_ratios) < 2:
            return 1.0
        
        # Coefficient of variation (lower is better, so invert)
        mean_sharpe = np.mean(sharpe_ratios)
        std_sharpe = np.std(sharpe_ratios)
        
        if mean_sharpe == 0:
            return 0.0
        
        cv = std_sharpe / abs(mean_sharpe)
        consistency = 1.0 / (1.0 + cv)  # Normalize to 0-1
        
        return consistency

