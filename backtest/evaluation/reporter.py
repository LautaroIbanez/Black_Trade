"""Generate comparative reports for strategy evaluation."""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class StrategyReporter:
    """Generate reports comparing strategy performance across evaluations."""
    
    def __init__(self):
        """Initialize reporter."""
        self.logger = logging.getLogger(__name__)
    
    def generate_comparison_report(
        self,
        evaluation_results: List[Dict[str, Any]],
        output_file: Optional[str] = None,
    ) -> str:
        """Generate a comparative report from evaluation results."""
        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("STRATEGY EVALUATION COMPARISON REPORT")
        report_lines.append("=" * 80)
        report_lines.append(f"Generated: {datetime.now().isoformat()}")
        report_lines.append("")
        
        # Summary table
        report_lines.append("SUMMARY TABLE")
        report_lines.append("-" * 80)
        report_lines.append(f"{'Strategy':<20} {'Sharpe':<10} {'Calmar':<10} {'Return%':<10} {'MaxDD%':<10} {'WinRate':<10} {'PF':<10} {'Passed':<10}")
        report_lines.append("-" * 80)
        
        for result in evaluation_results:
            strategy_name = result.get('strategy_name', 'Unknown')
            summary = result.get('summary', {})
            
            sharpe = summary.get('avg_sharpe_ratio', 0)
            calmar = summary.get('avg_calmar_ratio', 0)
            ret = summary.get('avg_return_pct', 0)
            maxdd = summary.get('avg_max_drawdown_pct', 0)
            wr = summary.get('avg_win_rate', 0)
            pf = summary.get('avg_profit_factor', 0)
            passed = "✓" if result.get('acceptance_check', {}).get('passed', False) else "✗"
            
            report_lines.append(
                f"{strategy_name:<20} {sharpe:>8.2f} {calmar:>8.2f} {ret:>8.2f} "
                f"{maxdd:>8.2f} {wr:>8.2%} {pf:>8.2f} {passed:>10}"
            )
        
        report_lines.append("")
        
        # Detailed per-dataset results
        report_lines.append("DETAILED RESULTS BY DATASET")
        report_lines.append("-" * 80)
        
        for result in evaluation_results:
            strategy_name = result.get('strategy_name', 'Unknown')
            datasets = result.get('datasets', [])
            
            report_lines.append(f"\n{strategy_name}:")
            
            for dataset in datasets:
                dataset_name = dataset.get('name', 'Unknown')
                
                if 'error' in dataset:
                    report_lines.append(f"  {dataset_name}: ERROR - {dataset['error']}")
                    continue
                
                wf_result = dataset.get('walk_forward_result', {})
                wf_summary = wf_result.get('summary', {})
                
                report_lines.append(f"  {dataset_name}:")
                report_lines.append(f"    Iterations: {wf_summary.get('total_iterations', 0)}")
                report_lines.append(f"    Avg Sharpe: {wf_summary.get('avg_sharpe_ratio', 0):.2f}")
                report_lines.append(f"    Avg Return: {wf_summary.get('avg_return_pct', 0):.2f}%")
                report_lines.append(f"    Consistency: {wf_summary.get('consistency_score', 0):.2f}")
        
        report_lines.append("")
        
        # Acceptance criteria check
        report_lines.append("ACCEPTANCE CRITERIA")
        report_lines.append("-" * 80)
        
        for result in evaluation_results:
            strategy_name = result.get('strategy_name', 'Unknown')
            acceptance = result.get('acceptance_check', {})
            
            report_lines.append(f"\n{strategy_name}:")
            
            if acceptance.get('passed', False):
                report_lines.append("  Status: PASSED")
            else:
                report_lines.append("  Status: FAILED")
            
            checks = acceptance.get('checks', {})
            for check_name, check_passed in checks.items():
                status = "✓" if check_passed else "✗"
                report_lines.append(f"    {check_name}: {status}")
        
        report_lines.append("")
        report_lines.append("=" * 80)
        
        report_text = "\n".join(report_lines)
        
        if output_file:
            with open(output_file, 'w') as f:
                f.write(report_text)
            self.logger.info(f"Report written to {output_file}")
        
        return report_text
    
    def generate_json_report(
        self,
        evaluation_results: List[Dict[str, Any]],
        output_file: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate JSON report for programmatic access."""
        report = {
            'generated_at': datetime.now().isoformat(),
            'strategies': evaluation_results,
        }
        
        if output_file:
            with open(output_file, 'w') as f:
                json.dump(report, f, indent=2)
            self.logger.info(f"JSON report written to {output_file}")
        
        return report

