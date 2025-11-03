"""Transaction journal for audit trail."""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
import json

logger = logging.getLogger(__name__)


class JournalEntryType(str, Enum):
    """Types of journal entries."""
    ORDER_CREATED = "order_created"
    ORDER_SUBMITTED = "order_submitted"
    ORDER_FILLED = "order_filled"
    ORDER_CANCELLED = "order_cancelled"
    ORDER_REJECTED = "order_rejected"
    ORDER_UPDATED = "order_updated"
    MANUAL_INTERVENTION = "manual_intervention"
    RISK_CHECK = "risk_check"
    COORDINATION_BLOCK = "coordination_block"
    ERROR = "error"
    SYSTEM_EVENT = "system_event"


from backend.repositories.journal_repository import JournalRepository


class TransactionJournal:
    """Transaction journal for audit trail."""
    
    def __init__(self):
        """Initialize journal."""
        # In-memory cache for quick reads; DB is source of truth
        self.entries: List[Dict[str, Any]] = []
        self.logger = logging.getLogger(__name__)
        self.repo = JournalRepository()
    
    def log(
        self,
        entry_type: JournalEntryType,
        order_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        user: Optional[str] = None,
    ) -> str:
        """
        Log a journal entry.
        
        Args:
            entry_type: Type of journal entry
            order_id: Related order ID (if applicable)
            details: Additional details
            user: User who triggered the action (if manual)
            
        Returns:
            Entry ID
        """
        entry = {
            'entry_id': f"ENTRY_{len(self.entries) + 1}",
            'timestamp': datetime.now().isoformat(),
            'type': entry_type.value,
            'order_id': order_id,
            'user': user or 'system',
            'details': details or {},
        }
        
        self.entries.append(entry)
        # Persist to DB (best-effort)
        try:
            self.repo.add_entry(entry_type.value, order_id, entry['user'], entry['details'])
        except Exception as e:
            self.logger.error(f"Failed to persist journal entry: {e}")
        
        # Log to logger
        self.logger.info(f"Journal: {entry_type.value} - Order: {order_id or 'N/A'}")
        
        return entry['entry_id']
    
    def get_entries(
        self,
        order_id: Optional[str] = None,
        entry_type: Optional[JournalEntryType] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Get journal entries with filters.
        
        Args:
            order_id: Filter by order ID
            entry_type: Filter by entry type
            start_time: Start time filter
            end_time: End time filter
            limit: Maximum entries to return
            
        Returns:
            List of journal entries
        """
        # Prefer DB entries; fall back to memory if DB fails
        try:
            from_date = start_time
            to_date = end_time
            db_entries = self.repo.get_entries(order_id=order_id, entry_type=entry_type.value if entry_type else None, start_time=from_date, end_time=to_date, limit=limit)
            return db_entries
        except Exception:
            filtered = self.entries
        
        if order_id:
            filtered = [e for e in filtered if e.get('order_id') == order_id]
        
        if entry_type:
            filtered = [e for e in filtered if e.get('type') == entry_type.value]
        
        if start_time:
            filtered = [e for e in filtered if datetime.fromisoformat(e['timestamp']) >= start_time]
        
        if end_time:
            filtered = [e for e in filtered if datetime.fromisoformat(e['timestamp']) <= end_time]
        
        # Sort by timestamp descending
        filtered.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return filtered[:limit]
    
    def get_order_history(self, order_id: str) -> List[Dict[str, Any]]:
        """Get complete history for an order."""
        return self.get_entries(order_id=order_id)
    
    def log_order_created(self, order: 'Order') -> str:
        """Log order creation."""
        return self.log(
            JournalEntryType.ORDER_CREATED,
            order_id=order.order_id,
            details={
                'symbol': order.symbol,
                'side': order.side.value,
                'quantity': order.quantity,
                'price': order.price,
                'strategy': order.strategy_name,
            },
        )
    
    def log_order_submitted(self, order_id: str, exchange_order_id: str) -> str:
        """Log order submission."""
        return self.log(
            JournalEntryType.ORDER_SUBMITTED,
            order_id=order_id,
            details={'exchange_order_id': exchange_order_id},
        )
    
    def log_order_filled(self, order_id: str, fill_data: Dict[str, Any]) -> str:
        """Log order fill."""
        return self.log(
            JournalEntryType.ORDER_FILLED,
            order_id=order_id,
            details=fill_data,
        )
    
    def log_order_cancelled(self, order_id: str, reason: str, user: Optional[str] = None) -> str:
        """Log order cancellation."""
        return self.log(
            JournalEntryType.ORDER_CANCELLED,
            order_id=order_id,
            details={'reason': reason},
            user=user,
        )
    
    def log_manual_intervention(self, action: str, details: Dict[str, Any], user: str) -> str:
        """Log manual intervention."""
        return self.log(
            JournalEntryType.MANUAL_INTERVENTION,
            details={'action': action, **details},
            user=user,
        )
    
    def log_coordination_block(self, order_id: str, reason: str) -> str:
        """Log coordination rule block."""
        return self.log(
            JournalEntryType.COORDINATION_BLOCK,
            order_id=order_id,
            details={'reason': reason},
        )
    
    def export_json(self, filepath: str) -> bool:
        """Export journal to JSON file."""
        try:
            with open(filepath, 'w') as f:
                json.dump(self.entries, f, indent=2)
            self.logger.info(f"Journal exported to {filepath}")
            return True
        except Exception as e:
            self.logger.error(f"Error exporting journal: {e}")
            return False


# Global journal instance
transaction_journal = TransactionJournal()

