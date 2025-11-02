"""Automatic evaluation of strategies across multiple datasets."""
import logging
from typing import List, Dict, Any, Optional, Type
import pandas as pd

from strategies.strategy_base import StrategyBase
from backtest.engine.walk_forward import WalkForwardEngine
from backtest.evaluation.synthetic_data import SyntheticDataGenerator

logger = logging.getLogger(__name__)


class StrategyEvaluator:
    """Evaluate strategies across multiple datasets and conditions."""
    
    def __init__(
        self,
        walk_forward_engine: Optional[WalkForwardEngine] = None,
        synthetic_generator: Optional[SyntheticDataGenerator] = None,
    ):
        """Initialize evaluator."""
        self.wf_engine = walk_forward_engine or WalkForwardEngine()
        self.synthetic_gen = synthetic_generator or SyntheticDataGenerator()
        self.logger = logging.getLogger(__name__)
    
    def evaluate_on_synthetic(
        self,
        strategy_class: Type[StrategyBase],
        parameter_space: Dict[str, List[Any]],
        datasets: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Evaluate strategy on synthetic datasets."""
        if datasets is None:
            # Default synthetic datasets
            datasets = [
                {'name': 'trending_up', 'type': 'trending', 'kwargs': {'trend_strength': 0.001}},
                {'name': 'trending_down', 'type': 'trending', 'kwargs': {'trend_strength': -0.001}},
                {'name': 'ranging', 'type': 'ranging', 'kwargs': {}},
                {'name': 'volatile', 'type': 'volatile', 'kwargs': {}},
                {'name': 'regime_switching', 'type': 'regime_switching', 'kwargs': {}},
            ]
        
        results = {
            'datasets': [],
            'summary': {},
        }
        
        for dataset_config in datasets:
            dataset_name = dataset_config['name']
            dataset_type = dataset_config['type']
            dataset_kwargs = dataset_config.get('kwargs', {})
            
            self.logger.info(f"Evaluating on synthetic dataset: {dataset_name}")
            
            # Generate dataset
            if dataset_type == 'trending':
                df = self.synthetic_gen.generate_trending(**dataset_kwargs)
            elif dataset_type == 'ranging':
                df = self.synthetic_gen.generate_ranging(**dataset_kwargs)
            elif dataset_type == 'volatile':
                df = self.synthetic_gen.generate_volatile(**dataset_kwargs)
            elif dataset_type == 'regime_switching':
                df = self.synthetic_gen.generate_regime_switching(**dataset_kwargs)
            else:
                self.logger.warning(f"Unknown dataset type: {dataset_type}")
                continue
            
            # Run walk-forward
            try:
                wf_result = self.wf_engine.run_walk_forward(
                    strategy_class=strategy_class,
                    df=df,
                    parameter_space=parameter_space,
                )
                
                results['datasets'].append({
                    'name': dataset_name,
                    'type': dataset_type,
                    'walk_forward_result': wf_result,
                })
            except Exception as e:
                self.logger.error(f"Error evaluating on {dataset_name}: {e}")
                results['datasets'].append({
                    'name': dataset_name,
                    'type': dataset_type,
                    'error': str(e),
                })
        
        # Compute summary
        successful_results = [r for r in results['datasets'] if 'walk_forward_result' in r]
        if successful_results:
            all_summaries = [r['walk_forward_result']['summary'] for r in successful_results]
            
            results['summary'] = {
                'total_datasets': len(results['datasets']),
                'successful_datasets': len(successful_results),
                'avg_sharpe_across_datasets': sum(s.get('avg_sharpe_ratio', 0) for s in all_summaries) / len(all_summaries),
                'avg_consistency_across_datasets': sum(s.get('consistency_score', 0) for s in all_summaries) / len(all_summaries),
            }
        
        return results
    
    def evaluate_on_historical(
        self,
        strategy_class: Type[StrategyBase],
        parameter_space: Dict[str, List[Any]],
        historical_dfs: List[pd.DataFrame],
        dataset_names: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Evaluate strategy on historical datasets."""
        if dataset_names is None:
            dataset_names = [f"historical_{i}" for i in range(len(historical_dfs))]
        
        results = {
            'datasets': [],
            'summary': {},
        }
        
        for df, name in zip(historical_dfs, dataset_names):
            self.logger.info(f"Evaluating on historical dataset: {name}")
            
            try:
                wf_result = self.wf_engine.run_walk_forward(
                    strategy_class=strategy_class,
                    df=df,
                    parameter_space=parameter_space,
                )
                
                results['datasets'].append({
                    'name': name,
                    'walk_forward_result': wf_result,
                })
            except Exception as e:
                self.logger.error(f"Error evaluating on {name}: {e}")
                results['datasets'].append({
                    'name': name,
                    'error': str(e),
                })
        
        # Compute summary
        successful_results = [r for r in results['datasets'] if 'walk_forward_result' in r]
        if successful_results:
            all_summaries = [r['walk_forward_result']['summary'] for r in successful_results]
            
            results['summary'] = {
                'total_datasets': len(results['datasets']),
                'successful_datasets': len(successful_results),
                'avg_sharpe_across_datasets': sum(s.get('avg_sharpe_ratio', 0) for s in all_summaries) / len(all_summaries),
                'avg_consistency_across_datasets': sum(s.get('consistency_score', 0) for s in all_summaries) / len(all_summaries),
            }
        
        return results
    
    def check_acceptance_criteria(
        self,
        metrics: Dict[str, Any],
        criteria: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Check if results meet acceptance criteria."""
        if criteria is None:
            criteria = {
                'min_sharpe_ratio': 1.0,
                'max_drawdown_pct': 30.0,
                'min_win_rate': 0.45,
                'min_profit_factor': 1.2,
                'min_trades': 20,
            }
        
        checks = {
            'sharpe_ratio': metrics.get('avg_sharpe_ratio', 0) >= criteria.get('min_sharpe_ratio', 1.0),
            'max_drawdown': metrics.get('avg_max_drawdown_pct', 100) <= criteria.get('max_drawdown_pct', 30.0),
            'win_rate': metrics.get('avg_win_rate', 0) >= criteria.get('min_win_rate', 0.45),
            'profit_factor': metrics.get('avg_profit_factor', 0) >= criteria.get('min_profit_factor', 1.2),
            'min_trades': True,  # TODO: Check per iteration
        }
        
        all_passed = all(checks.values())
        
        return {
            'passed': all_passed,
            'checks': checks,
            'criteria': criteria,
        }

