#!/usr/bin/env python3
"""Script to validate a strategy using walk-forward analysis and evaluation."""
import sys
import os
from pathlib import Path
import pandas as pd
import logging

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from strategies.ema_rsi_strategy import EMARSIStrategy
from strategies.strategy_config import EMARSIConfig
from backtest.engine.walk_forward import WalkForwardEngine
from backtest.evaluation.evaluator import StrategyEvaluator
from backtest.evaluation.reporter import StrategyReporter
from backend.repositories.strategy_results_repository import StrategyResultsRepository
from backend.db.session import init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """Main validation function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Validate a trading strategy')
    parser.add_argument('--strategy', default='EMA_RSI', help='Strategy name')
    parser.add_argument('--dataset', help='Historical dataset file (CSV)')
    parser.add_argument('--synthetic', action='store_true', help='Use synthetic datasets')
    parser.add_argument('--output', help='Output directory for reports')
    parser.add_argument('--save-db', action='store_true', help='Save results to database')
    
    args = parser.parse_args()
    
    # Initialize database if saving
    if args.save_db:
        init_db()
        logger.info("Database initialized")
    
    # 1. Setup configuration
    config = EMARSIConfig()
    parameter_space = config.get_parameter_space()
    
    logger.info(f"Parameter space: {parameter_space}")
    
    # 2. Setup walk-forward engine
    wf_engine = WalkForwardEngine(
        train_size=0.7,
        test_size=0.3,
        step_size=0.1,
        min_train_periods=100,
    )
    
    # 3. Setup evaluator
    evaluator = StrategyEvaluator(walk_forward_engine=wf_engine)
    
    # 4. Evaluate on synthetic datasets
    if args.synthetic:
        logger.info("Evaluating on synthetic datasets...")
        synthetic_results = evaluator.evaluate_on_synthetic(
            strategy_class=EMARSIStrategy,
            parameter_space=parameter_space,
        )
        synthetic_results['strategy_name'] = args.strategy
        
        # Check acceptance
        acceptance = evaluator.check_acceptance_criteria(
            metrics=synthetic_results['summary'],
        )
        synthetic_results['acceptance_check'] = acceptance
        
        logger.info(f"Acceptance check: {acceptance['passed']}")
        
        # Save to DB if requested
        if args.save_db:
            repo = StrategyResultsRepository()
            # Save synthetic results...
    
    # 5. Evaluate on historical dataset if provided
    historical_results = None
    if args.dataset:
        logger.info(f"Evaluating on historical dataset: {args.dataset}")
        
        # Load dataset
        df = pd.read_csv(args.dataset)
        if 'timestamp' not in df.columns:
            logger.error("Dataset must have 'timestamp' column")
            return
        
        # Convert timestamp to datetime if needed
        if df['timestamp'].dtype == 'int64':
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        historical_results = evaluator.evaluate_on_historical(
            strategy_class=EMARSIStrategy,
            parameter_space=parameter_space,
            historical_dfs=[df],
            dataset_names=[Path(args.dataset).stem],
        )
        historical_results['strategy_name'] = args.strategy
        
        # Check acceptance
        acceptance = evaluator.check_acceptance_criteria(
            metrics=historical_results['summary'],
        )
        historical_results['acceptance_check'] = acceptance
        
        logger.info(f"Acceptance check: {acceptance['passed']}")
        
        # Save to DB if requested
        if args.save_db:
            repo = StrategyResultsRepository()
            from datetime import datetime
            
            for dataset in historical_results['datasets']:
                if 'error' in dataset:
                    continue
                
                wf_result = dataset.get('walk_forward_result', {})
                for iteration in wf_result.get('iterations', []):
                    try:
                        period_start = datetime.fromisoformat(
                            iteration['metrics']['period_start']
                        )
                        period_end = datetime.fromisoformat(
                            iteration['metrics']['period_end']
                        )
                    except:
                        period_start = None
                        period_end = None
                    
                    repo.save_backtest_result(
                        strategy_name=args.strategy,
                        parameters=iteration['optimal_parameters'],
                        metrics=iteration['metrics'],
                        dataset_name=dataset['name'],
                        period_start=period_start,
                        period_end=period_end,
                        split_type='oos',
                    )
            
            logger.info("Results saved to database")
    
    # 6. Generate report
    if args.output:
        output_dir = Path(args.output)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        reporter = StrategyReporter()
        
        # Collect all results
        all_results = []
        if args.synthetic:
            all_results.append(synthetic_results)
        if historical_results:
            all_results.append(historical_results)
        
        if all_results:
            # Text report
            report_file = output_dir / f"{args.strategy}_validation_report.txt"
            reporter.generate_comparison_report(all_results, output_file=str(report_file))
            
            # JSON report
            json_file = output_dir / f"{args.strategy}_validation_report.json"
            reporter.generate_json_report(all_results, output_file=str(json_file))
            
            logger.info(f"Reports written to {output_dir}")
    
    logger.info("Validation complete")


if __name__ == '__main__':
    main()

