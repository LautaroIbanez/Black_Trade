"""API routes for strategy management and walk-forward results."""
from fastapi import APIRouter, HTTPException, Query
from typing import Dict, List, Any, Optional
from pydantic import BaseModel

from backend.services.strategy_registry import strategy_registry
from backend.repositories.strategy_results_repository import StrategyResultsRepository

router = APIRouter(prefix="/api/strategies", tags=["strategies"])

# Initialize repository
results_repo = StrategyResultsRepository()


class StrategyInfo(BaseModel):
    """Strategy information."""
    name: str
    enabled: bool
    parameters: Dict[str, Any]
    description: str = ""


class OptimalParametersResponse(BaseModel):
    """Response for optimal parameters."""
    strategy_name: str
    parameters: Dict[str, Any]
    validation_metrics: Dict[str, Any]
    train_metrics: Optional[Dict[str, Any]] = None
    validation_period_start: Optional[str] = None
    validation_period_end: Optional[str] = None
    created_at: Optional[str] = None


class BacktestResultResponse(BaseModel):
    """Response for backtest results."""
    id: int
    strategy_name: str
    parameters: Dict[str, Any]
    metrics: Dict[str, Any]
    period_start: Optional[str] = None
    period_end: Optional[str] = None
    split_type: Optional[str] = None
    trades_count: Optional[int] = None
    created_at: Optional[str] = None


class StrategyMetricsResponse(BaseModel):
    """Response for strategy metrics summary."""
    strategy_name: str
    latest_optimal_parameters: Optional[OptimalParametersResponse] = None
    recent_results: List[BacktestResultResponse] = []
    summary_metrics: Dict[str, Any] = {}


@router.get("/")
async def list_strategies() -> Dict[str, Any]:
    """List all available strategies with their configurations."""
    strategies = strategy_registry.get_enabled_strategies(use_optimal_parameters=False)
    # Get disabled strategies (all strategies minus enabled)
    all_configs = strategy_registry.list_strategies()
    enabled_names = {s.name for s in strategies}
    disabled_configs = [c for c in all_configs if c['name'] not in enabled_names]
    
    result = {
        "enabled": [
            {
                "name": s.name,
                "class_name": s.__class__.__name__,
                "parameters": strategy_registry.get_strategy_config(s.name, use_optimal=False).parameters if strategy_registry.get_strategy_config(s.name) else {},
            }
            for s in strategies
        ],
        "disabled": [
            {
                "name": c['name'],
                "class_name": c.get('class_name', ''),
            }
            for c in disabled_configs
        ],
    }
    
    return result


@router.get("/{strategy_name}/optimal-parameters")
async def get_optimal_parameters(strategy_name: str) -> OptimalParametersResponse:
    """Get latest optimal parameters for a strategy from walk-forward optimization."""
    optimal = results_repo.get_latest_optimal_parameters(strategy_name)
    
    if not optimal:
        raise HTTPException(
            status_code=404,
            detail=f"No optimal parameters found for strategy: {strategy_name}"
        )
    
    return OptimalParametersResponse(**optimal)


@router.get("/{strategy_name}/results")
async def get_strategy_results(
    strategy_name: str,
    limit: int = Query(10, ge=1, le=100),
    split_type: Optional[str] = Query(None, description="Filter by split type: 'is' or 'oos'"),
) -> Dict[str, Any]:
    """Get backtest results for a strategy."""
    results = results_repo.get_latest_results(strategy_name=strategy_name, limit=limit)
    
    # Filter by split_type if specified
    if split_type:
        results = [r for r in results if r.get('split_type') == split_type]
    
    return {
        "strategy_name": strategy_name,
        "count": len(results),
        "results": results,
    }


@router.get("/{strategy_name}/metrics")
async def get_strategy_metrics(strategy_name: str) -> StrategyMetricsResponse:
    """Get comprehensive metrics for a strategy including walk-forward results."""
    # Get latest optimal parameters
    optimal = results_repo.get_latest_optimal_parameters(strategy_name)
    
    # Get recent results
    recent_results = results_repo.get_latest_results(strategy_name=strategy_name, limit=10)
    
    # Calculate summary metrics from recent results
    summary_metrics = {}
    if recent_results:
        all_metrics = [r.get('metrics', {}) for r in recent_results if r.get('metrics')]
        if all_metrics:
            # Calculate averages
            summary_metrics = {
                'avg_sharpe_ratio': sum(m.get('sharpe_ratio', 0) for m in all_metrics) / len(all_metrics),
                'avg_win_rate': sum(m.get('win_rate', 0) for m in all_metrics) / len(all_metrics),
                'avg_profit_factor': sum(m.get('profit_factor', 0) for m in all_metrics) / len(all_metrics),
                'avg_max_drawdown': sum(m.get('max_drawdown_pct', 0) for m in all_metrics) / len(all_metrics),
                'total_results': len(all_metrics),
            }
    
    return StrategyMetricsResponse(
        strategy_name=strategy_name,
        latest_optimal_parameters=OptimalParametersResponse(**optimal) if optimal else None,
        recent_results=[BacktestResultResponse(**r) for r in recent_results[:5]],
        summary_metrics=summary_metrics,
    )


@router.get("/{strategy_name}/performance")
async def get_strategy_performance(strategy_name: str) -> Dict[str, Any]:
    """Get performance metrics and trends for a strategy."""
    # Get all results
    all_results = results_repo.get_latest_results(strategy_name=strategy_name, limit=100)
    
    if not all_results:
        raise HTTPException(
            status_code=404,
            detail=f"No results found for strategy: {strategy_name}"
        )
    
    # Separate IS and OOS results
    is_results = [r for r in all_results if r.get('split_type') == 'is']
    oos_results = [r for r in all_results if r.get('split_type') == 'oos']
    
    # Calculate performance trends
    def calc_avg_metric(results, metric_key):
        if not results:
            return None
        metrics = [r.get('metrics', {}) for r in results if r.get('metrics')]
        if not metrics:
            return None
        values = [m.get(metric_key, 0) for m in metrics if metric_key in m]
        return sum(values) / len(values) if values else None
    
    performance = {
        "strategy_name": strategy_name,
        "in_sample": {
            "avg_sharpe": calc_avg_metric(is_results, 'sharpe_ratio'),
            "avg_win_rate": calc_avg_metric(is_results, 'win_rate'),
            "avg_profit_factor": calc_avg_metric(is_results, 'profit_factor'),
            "results_count": len(is_results),
        },
        "out_of_sample": {
            "avg_sharpe": calc_avg_metric(oos_results, 'sharpe_ratio'),
            "avg_win_rate": calc_avg_metric(oos_results, 'win_rate'),
            "avg_profit_factor": calc_avg_metric(oos_results, 'profit_factor'),
            "results_count": len(oos_results),
        },
        "consistency": {
            "is_oos_sharpe_ratio": None,
            "is_oos_win_rate_ratio": None,
        }
    }
    
    # Calculate IS/OOS consistency ratios
    if performance["in_sample"]["avg_sharpe"] and performance["out_of_sample"]["avg_sharpe"]:
        is_sharpe = performance["in_sample"]["avg_sharpe"]
        oos_sharpe = performance["out_of_sample"]["avg_sharpe"]
        if is_sharpe > 0:
            performance["consistency"]["is_oos_sharpe_ratio"] = oos_sharpe / is_sharpe
    
    if performance["in_sample"]["avg_win_rate"] and performance["out_of_sample"]["avg_win_rate"]:
        is_wr = performance["in_sample"]["avg_win_rate"]
        oos_wr = performance["out_of_sample"]["avg_win_rate"]
        if is_wr > 0:
            performance["consistency"]["is_oos_win_rate_ratio"] = oos_wr / is_wr
    
    return performance

