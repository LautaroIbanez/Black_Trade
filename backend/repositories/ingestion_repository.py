"""Repository for ingestion status tracking."""
from typing import List, Dict, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_

from backend.models.ohlcv import IngestionStatus, IngestionMetric
from backend.db.session import db_session


class IngestionRepository:
    """Repository for ingestion status and metrics."""
    
    def update_status(self, symbol: str, timeframe: str, status_data: Dict, db: Session = None) -> bool:
        """Update or create ingestion status."""
        should_close = db is None
        if db is None:
            db = next(db_session())
        
        try:
            status = db.query(IngestionStatus).filter(
                and_(
                    IngestionStatus.symbol == symbol,
                    IngestionStatus.timeframe == timeframe
                )
            ).first()
            
            if status:
                # Update existing
                for key, value in status_data.items():
                    if hasattr(status, key):
                        setattr(status, key, value)
                status.updated_at = datetime.utcnow()
            else:
                # Create new
                status = IngestionStatus(
                    symbol=symbol,
                    timeframe=timeframe,
                    **status_data
                )
                db.add(status)
            
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            raise
        finally:
            if should_close:
                db.close()
    
    def get_status(self, symbol: str, timeframe: str, db: Session = None) -> Optional[Dict]:
        """Get ingestion status for a symbol/timeframe."""
        should_close = db is None
        if db is None:
            db = next(db_session())
        
        try:
            status = db.query(IngestionStatus).filter(
                and_(
                    IngestionStatus.symbol == symbol,
                    IngestionStatus.timeframe == timeframe
                )
            ).first()
            
            return status.to_dict() if status else None
        finally:
            if should_close:
                db.close()
    
    def get_all_statuses(self, db: Session = None) -> List[Dict]:
        """Get all ingestion statuses."""
        should_close = db is None
        if db is None:
            db = next(db_session())
        
        try:
            statuses = db.query(IngestionStatus).all()
            return [status.to_dict() for status in statuses]
        finally:
            if should_close:
                db.close()
    
    def record_metric(self, symbol: str, timeframe: str, metric_type: str, 
                     metric_value: float, db: Session = None) -> bool:
        """Record an ingestion metric."""
        should_close = db is None
        if db is None:
            db = next(db_session())
        
        try:
            metric = IngestionMetric(
                symbol=symbol,
                timeframe=timeframe,
                metric_type=metric_type,
                metric_value=metric_value,
                timestamp=datetime.utcnow()
            )
            db.add(metric)
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            raise
        finally:
            if should_close:
                db.close()

