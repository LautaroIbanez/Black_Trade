"""Repository for storing and retrieving strategy backtest results."""
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc

from backend.models.strategy_results import BacktestResult, OptimalParameters
from backend.db.session import get_db_session


class StrategyResultsRepository:
    """Repository for strategy backtest results and optimal parameters."""
    
    def save_backtest_result(
        self,
        strategy_name: str,
        parameters: Dict[str, Any],
        metrics: Dict[str, Any],
        dataset_name: Optional[str] = None,
        period_start: Optional[datetime] = None,
        period_end: Optional[datetime] = None,
        split_type: Optional[str] = None,
        db: Session = None,
    ) -> int:
        """Save a backtest result."""
        should_close = db is None
        if db is None:
            db = get_db_session()
        
        try:
            result = BacktestResult(
                strategy_name=strategy_name,
                dataset_name=dataset_name,
                period_start=period_start,
                period_end=period_end,
                split_type=split_type,
                parameters=parameters,
                metrics=metrics,
                trades_count=metrics.get('total_trades', 0),
            )
            db.add(result)
            db.commit()
            db.refresh(result)
            return result.id
        except Exception as e:
            db.rollback()
            raise
        finally:
            if should_close:
                db.close()
    
    def get_latest_results(
        self,
        strategy_name: Optional[str] = None,
        dataset_name: Optional[str] = None,
        limit: int = 100,
        db: Session = None,
    ) -> List[Dict[str, Any]]:
        """Get latest backtest results."""
        should_close = db is None
        if db is None:
            db = get_db_session()
        
        try:
            query = db.query(BacktestResult)
            
            if strategy_name:
                query = query.filter(BacktestResult.strategy_name == strategy_name)
            if dataset_name:
                query = query.filter(BacktestResult.dataset_name == dataset_name)
            
            results = query.order_by(desc(BacktestResult.created_at)).limit(limit).all()
            return [r.to_dict() for r in results]
        finally:
            if should_close:
                db.close()
    
    def save_optimal_parameters(
        self,
        strategy_name: str,
        parameters: Dict[str, Any],
        validation_metrics: Dict[str, Any],
        dataset_name: Optional[str] = None,
        validation_period_start: Optional[datetime] = None,
        validation_period_end: Optional[datetime] = None,
        train_metrics: Optional[Dict[str, Any]] = None,
        db: Session = None,
    ) -> int:
        """Save optimal parameters from walk-forward optimization."""
        should_close = db is None
        if db is None:
            db = get_db_session()
        
        try:
            optimal = OptimalParameters(
                strategy_name=strategy_name,
                dataset_name=dataset_name,
                validation_period_start=validation_period_start,
                validation_period_end=validation_period_end,
                parameters=parameters,
                validation_metrics=validation_metrics,
                train_metrics=train_metrics,
            )
            db.add(optimal)
            db.commit()
            db.refresh(optimal)
            return optimal.id
        except Exception as e:
            db.rollback()
            raise
        finally:
            if should_close:
                db.close()
    
    def get_latest_optimal_parameters(
        self,
        strategy_name: str,
        dataset_name: Optional[str] = None,
        db: Session = None,
    ) -> Optional[Dict[str, Any]]:
        """Get latest optimal parameters for a strategy."""
        should_close = db is None
        if db is None:
            db = get_db_session()
        
        try:
            query = db.query(OptimalParameters).filter(
                OptimalParameters.strategy_name == strategy_name
            )
            
            if dataset_name:
                query = query.filter(OptimalParameters.dataset_name == dataset_name)
            
            optimal = query.order_by(desc(OptimalParameters.created_at)).first()
            return optimal.to_dict() if optimal else None
        finally:
            if should_close:
                db.close()


