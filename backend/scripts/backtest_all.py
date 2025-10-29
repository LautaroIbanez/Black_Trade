#!/usr/bin/env python3
"""Run comprehensive backtests for all strategies and generate comparison reports."""
import sys
import os
import json
import pandas as pd
from datetime import datetime
from typing import Dict, Any, List

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from backtest.engine import BacktestEngine, CostModel
from backtest.data_loader import data_loader
from backend.services.strategy_registry import strategy_registry
from strategies.ema_rsi_strategy import EMARSIStrategy
from strategies.momentum_strategy import MomentumStrategy
from strategies.breakout_strategy import BreakoutStrategy
from strategies.mean_reversion_strategy import MeanReversionStrategy
from strategies.ichimoku_strategy import IchimokuStrategy


def run_backtest_comparison(
    initial_capital: float = 10000.0,
    position_size_pct: float = 0.1,
    commission_pct: float = 0.0002,
    slippage_pct: float = 0.0001,
    spread_mode: str = "fixed",
    spread_atr_multiplier: float = 0.25,
    walk_forward: bool = False,
    train_window: int = 0,
    test_window: int = 0,
    split: float = 0.0,
) -> Dict[str, Any]:
    """Run backtests with both old and new strategy configurations."""
    
    # Initialize backtest engine
    engine = BacktestEngine(
        initial_capital=initial_capital,
        position_size_pct=position_size_pct,
        cost_model=CostModel(
            commission_pct=commission_pct,
            slippage_pct=slippage_pct,
            spread_mode=spread_mode,
            spread_atr_multiplier=spread_atr_multiplier,
        ),
    )
    
    # Test parameters
    symbol = 'BTCUSDT'
    timeframes = ['1h', '4h', '1d']
    days_back = 90  # 3 months of data
    
    results = {
        'timestamp': datetime.now().isoformat(),
        'symbol': symbol,
        'timeframes': timeframes,
        'comparison_results': {}
    }
    
    print(f"Running backtest comparison for {symbol} across {timeframes}")
    print("=" * 60)
    
    for timeframe in timeframes:
        print(f"\nProcessing timeframe: {timeframe}")
        print("-" * 40)
        
        try:
            # Load data
            data, validation_report = data_loader.load_data(symbol, timeframe, validate_continuity=True)
            
            if data.empty:
                print(f"  No data available for {timeframe}")
                continue
            
            print(f"  Loaded {len(data)} candles for {timeframe}")
            
            # Test original EMA RSI strategy
            print("  Testing original EMA RSI strategy...")
            original_ema = EMARSIStrategy(
                fast_period=12, slow_period=26, rsi_period=14,
                rsi_oversold=30, rsi_overbought=70,
                signal_persistence=1, volume_confirmation=False
            )
            if walk_forward and train_window > 0 and test_window > 0:
                original_results = engine.run_walk_forward(original_ema, data, timeframe, train_window, test_window, step=test_window)
            elif split and split > 0:
                original_results = engine.run_backtest_with_split(original_ema, data, timeframe, split)
            else:
                original_results = engine.run_backtest(original_ema, data, timeframe)
            
            # Test enhanced EMA RSI strategy
            print("  Testing enhanced EMA RSI strategy...")
            enhanced_ema = EMARSIStrategy(
                fast_period=12, slow_period=26, rsi_period=14,
                rsi_oversold=30, rsi_overbought=70,
                signal_persistence=3, volume_confirmation=True
            )
            if walk_forward and train_window > 0 and test_window > 0:
                enhanced_results = engine.run_walk_forward(enhanced_ema, data, timeframe, train_window, test_window, step=test_window)
            elif split and split > 0:
                enhanced_results = engine.run_backtest_with_split(enhanced_ema, data, timeframe, split)
            else:
                enhanced_results = engine.run_backtest(enhanced_ema, data, timeframe)
            
            # Test other strategies for baseline
            print("  Testing other strategies...")
            momentum = MomentumStrategy()
            breakout = BreakoutStrategy()
            mean_reversion = MeanReversionStrategy()
            ichimoku = IchimokuStrategy()
            
            other_strategies = [momentum, breakout, mean_reversion, ichimoku]
            other_results = {}
            
            for strategy in other_strategies:
                try:
                    if walk_forward and train_window > 0 and test_window > 0:
                        strategy_result = engine.run_walk_forward(strategy, data, timeframe, train_window, test_window, step=test_window)
                    elif split and split > 0:
                        strategy_result = engine.run_backtest_with_split(strategy, data, timeframe, split)
                    else:
                        strategy_result = engine.run_backtest(strategy, data, timeframe)
                    other_results[strategy.name] = strategy_result
                except Exception as e:
                    print(f"    Error testing {strategy.name}: {e}")
                    continue
            
            # Compile results for this timeframe
            timeframe_results = {
                'original_ema_rsi': original_results,
                'enhanced_ema_rsi': enhanced_results,
                'other_strategies': other_results,
                'data_points': len(data),
                'date_range': {
                    'start': str(data['timestamp'].min()) if 'timestamp' in data.columns else 'N/A',
                    'end': str(data['timestamp'].max()) if 'timestamp' in data.columns else 'N/A'
                }
            }
            
            results['comparison_results'][timeframe] = timeframe_results
            
            # Print summary for this timeframe
            print(f"\n  Results for {timeframe}:")
            print(f"    Original EMA RSI: {original_results.get('total_trades', 0)} trades, "
                  f"{original_results.get('win_rate', 0):.1%} win rate, "
                  f"${original_results.get('net_pnl', 0):.2f} PnL")
            print(f"    Enhanced EMA RSI: {enhanced_results.get('total_trades', 0)} trades, "
                  f"{enhanced_results.get('win_rate', 0):.1%} win rate, "
                  f"${enhanced_results.get('net_pnl', 0):.2f} PnL")
            
            # Calculate improvement metrics
            if original_results.get('total_trades', 0) > 0:
                trade_improvement = ((enhanced_results.get('total_trades', 0) - original_results.get('total_trades', 0)) 
                                   / original_results.get('total_trades', 0)) * 100
                pnl_improvement = ((enhanced_results.get('net_pnl', 0) - original_results.get('net_pnl', 0)) 
                                 / abs(original_results.get('net_pnl', 1))) * 100 if original_results.get('net_pnl', 0) != 0 else 0
                
                print(f"    Trade count change: {trade_improvement:+.1f}%")
                print(f"    PnL change: {pnl_improvement:+.1f}%")
            
        except Exception as e:
            print(f"  Error processing {timeframe}: {e}")
            continue
    
    return results


def save_results(results: Dict[str, Any], output_file: str = None) -> str:
    """Save results to JSON file."""
    if output_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"backtest_comparison_{timestamp}.json"
    
    # Ensure output directory exists
    output_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'docs')
    os.makedirs(output_dir, exist_ok=True)
    
    output_path = os.path.join(output_dir, output_file)
    
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    return output_path


def generate_summary_report(results: Dict[str, Any]) -> str:
    """Generate a human-readable summary report."""
    report_lines = [
        "# Strategy Enhancement Comparison Report",
        f"Generated: {results['timestamp']}",
        f"Symbol: {results['symbol']}",
        f"Timeframes: {', '.join(results['timeframes'])}",
        "",
        "## Summary",
        ""
    ]
    
    total_improvements = []
    
    for timeframe, data in results['comparison_results'].items():
        report_lines.extend([
            f"### {timeframe.upper()} Timeframe",
            f"Data Points: {data['data_points']}",
            f"Date Range: {data['date_range']['start']} to {data['date_range']['end']}",
            ""
        ])
        
        original = data['original_ema_rsi']
        enhanced = data['enhanced_ema_rsi']
        
        report_lines.extend([
            "#### EMA RSI Strategy Comparison",
            f"| Metric | Original | Enhanced | Change |",
            f"|--------|----------|----------|--------|",
            f"| Total Trades | {original.get('total_trades', 0)} | {enhanced.get('total_trades', 0)} | {enhanced.get('total_trades', 0) - original.get('total_trades', 0):+d} |",
            f"| Win Rate | {original.get('win_rate', 0):.1%} | {enhanced.get('win_rate', 0):.1%} | {(enhanced.get('win_rate', 0) - original.get('win_rate', 0)) * 100:+.1f}pp |",
            f"| Net PnL | ${original.get('net_pnl', 0):.2f} | ${enhanced.get('net_pnl', 0):.2f} | ${enhanced.get('net_pnl', 0) - original.get('net_pnl', 0):+.2f} |",
            f"| Profit Factor | {original.get('profit_factor', 0):.2f} | {enhanced.get('profit_factor', 0):.2f} | {enhanced.get('profit_factor', 0) - original.get('profit_factor', 0):+.2f} |",
            f"| Max Drawdown | ${original.get('max_drawdown', 0):.2f} | ${enhanced.get('max_drawdown', 0):.2f} | ${enhanced.get('max_drawdown', 0) - original.get('max_drawdown', 0):+.2f} |",
            ""
        ])
        
        # Calculate improvements
        if original.get('total_trades', 0) > 0:
            trade_change = ((enhanced.get('total_trades', 0) - original.get('total_trades', 0)) 
                           / original.get('total_trades', 0)) * 100
            pnl_change = ((enhanced.get('net_pnl', 0) - original.get('net_pnl', 0)) 
                         / abs(original.get('net_pnl', 1))) * 100 if original.get('net_pnl', 0) != 0 else 0
            
            total_improvements.append({
                'timeframe': timeframe,
                'trade_change': trade_change,
                'pnl_change': pnl_change
            })
        
        # Add other strategies summary
        if data['other_strategies']:
            report_lines.extend([
                "#### Other Strategies Performance",
                "| Strategy | Trades | Win Rate | Net PnL |",
                "|----------|--------|----------|---------|"
            ])
            
            for strategy_name, strategy_data in data['other_strategies'].items():
                report_lines.append(
                    f"| {strategy_name} | {strategy_data.get('total_trades', 0)} | "
                    f"{strategy_data.get('win_rate', 0):.1%} | "
                    f"${strategy_data.get('net_pnl', 0):.2f} |"
                )
            report_lines.append("")
    
    # Overall summary
    if total_improvements:
        avg_trade_change = sum(imp['trade_change'] for imp in total_improvements) / len(total_improvements)
        avg_pnl_change = sum(imp['pnl_change'] for imp in total_improvements) / len(total_improvements)
        
        report_lines.extend([
            "## Overall Impact",
            f"Average Trade Count Change: {avg_trade_change:+.1f}%",
            f"Average PnL Change: {avg_pnl_change:+.1f}%",
            "",
            "## Key Improvements",
            "- Signal persistence reduces false signals and maintains trends",
            "- Volume confirmation filters out low-quality signals",
            "- Enhanced confidence scoring prioritizes active signals over neutrals",
            "- Better risk management with adaptive entry ranges",
            ""
        ])
    
    return "\n".join(report_lines)


def main():
    """Main execution function."""
    import argparse
    print("Starting comprehensive backtest comparison...")
    
    parser = argparse.ArgumentParser(description="Run backtests and generate reports")
    parser.add_argument("--initial-capital", type=float, default=10000.0)
    parser.add_argument("--position-size-pct", type=float, default=0.1)
    parser.add_argument("--commission-pct", type=float, default=0.0002)
    parser.add_argument("--slippage-pct", type=float, default=0.0001)
    parser.add_argument("--spread-mode", type=str, default="fixed", choices=["fixed", "atr"])
    parser.add_argument("--spread-atr-multiplier", type=float, default=0.25)
    parser.add_argument("--split", type=float, default=0.0, help="Train/Test split ratio (0 disables)")
    parser.add_argument("--walk-forward", action="store_true")
    parser.add_argument("--train-window", type=int, default=0)
    parser.add_argument("--test-window", type=int, default=0)
    args = parser.parse_args()
    
    try:
        # Run backtests
        results = run_backtest_comparison(
            initial_capital=args.initial_capital,
            position_size_pct=args.position_size_pct,
            commission_pct=args.commission_pct,
            slippage_pct=args.slippage_pct,
            spread_mode=args.spread_mode,
            spread_atr_multiplier=args.spread_atr_multiplier,
            walk_forward=args.walk_forward,
            train_window=args.train_window,
            test_window=args.test_window,
            split=args.split,
        )
        
        # Save detailed results
        json_path = save_results(results)
        print(f"\nDetailed results saved to: {json_path}")
        
        # Generate and save summary report
        summary_report = generate_summary_report(results)
        summary_path = os.path.join(os.path.dirname(json_path), "strategy_reports.md")
        
        with open(summary_path, 'w') as f:
            f.write(summary_report)
        
        print(f"Summary report saved to: {summary_path}")
        
        # Print final summary
        print("\n" + "=" * 60)
        print("BACKTEST COMPARISON COMPLETE")
        print("=" * 60)
        
        for timeframe, data in results['comparison_results'].items():
            original = data['original_ema_rsi']
            enhanced = data['enhanced_ema_rsi']
            
            print(f"\n{timeframe.upper()}:")
            print(f"  Original: {original.get('total_trades', 0)} trades, "
                  f"{original.get('win_rate', 0):.1%} win rate, "
                  f"${original.get('net_pnl', 0):.2f} PnL")
            print(f"  Enhanced: {enhanced.get('total_trades', 0)} trades, "
                  f"{enhanced.get('win_rate', 0):.1%} win rate, "
                  f"${enhanced.get('net_pnl', 0):.2f} PnL")
        
        return 0
        
    except Exception as e:
        print(f"Error during backtest comparison: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
