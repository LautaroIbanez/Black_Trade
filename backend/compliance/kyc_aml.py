"""KYC/AML compliance checks."""
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class KYCRecord:
    """KYC record for a user."""
    user_id: str
    name: str
    email: str
    verified: bool = False
    verification_date: Optional[datetime] = None
    document_type: Optional[str] = None
    document_number: Optional[str] = None
    country: Optional[str] = None
    risk_level: str = "LOW"  # LOW, MEDIUM, HIGH
    created_at: datetime = None
    updated_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()


@dataclass
class AMLAlert:
    """AML alert record."""
    alert_id: str
    user_id: str
    alert_type: str
    severity: str  # LOW, MEDIUM, HIGH
    description: str
    transaction_ids: List[str]
    created_at: datetime
    status: str = "OPEN"  # OPEN, INVESTIGATING, RESOLVED, FALSE_POSITIVE


class KYCService:
    """KYC (Know Your Customer) service."""
    
    def __init__(self):
        """Initialize KYC service."""
        # In production, integrate with KYC provider (Onfido, Jumio, etc.)
        self.records: Dict[str, KYCRecord] = {}
        self.logger = logging.getLogger(__name__)
    
    def register_user(
        self,
        user_id: str,
        name: str,
        email: str,
        country: str,
        document_type: str = None,
        document_number: str = None,
    ) -> KYCRecord:
        """
        Register a new user for KYC.
        
        Args:
            user_id: Unique user ID
            name: Full name
            email: Email address
            country: Country of residence
            document_type: Type of ID document
            document_number: Document number
            
        Returns:
            KYC record
        """
        record = KYCRecord(
            user_id=user_id,
            name=name,
            email=email,
            country=country,
            document_type=document_type,
            document_number=document_number,
            verified=False,
        )
        
        self.records[user_id] = record
        
        self.logger.info(f"KYC record created for user {user_id}")
        
        return record
    
    def verify_user(self, user_id: str, document_data: dict = None) -> bool:
        """
        Verify a user's identity.
        
        Args:
            user_id: User ID to verify
            document_data: Document verification data
            
        Returns:
            True if verified successfully
        """
        if user_id not in self.records:
            return False
        
        record = self.records[user_id]
        record.verified = True
        record.verification_date = datetime.now()
        record.updated_at = datetime.now()
        
        # In production, integrate with verification provider
        # For now, just mark as verified
        
        self.logger.info(f"User {user_id} verified for KYC")
        
        return True
    
    def get_verification_status(self, user_id: str) -> Optional[KYCRecord]:
        """Get KYC verification status for user."""
        return self.records.get(user_id)
    
    def is_verified(self, user_id: str) -> bool:
        """Check if user is KYC verified."""
        record = self.records.get(user_id)
        return record.verified if record else False


class AMLService:
    """AML (Anti-Money Laundering) service."""
    
    def __init__(self):
        """Initialize AML service."""
        self.alerts: List[AMLAlert] = []
        self.logger = logging.getLogger(__name__)
        
        # Thresholds for suspicious activity
        self.thresholds = {
            'large_transaction_usd': 10000.0,
            'rapid_transactions_count': 10,
            'rapid_transactions_window_hours': 24,
            'unusual_pattern_deviation': 3.0,  # standard deviations
        }
    
    def check_transaction(
        self,
        user_id: str,
        transaction_id: str,
        amount_usd: float,
        transaction_type: str,
        metadata: dict = None,
    ) -> tuple[bool, Optional[AMLAlert]]:
        """
        Check if transaction triggers AML alerts.
        
        Args:
            user_id: User ID
            transaction_id: Transaction ID
            amount_usd: Amount in USD
            transaction_type: Type of transaction
            metadata: Additional metadata
            
        Returns:
            Tuple of (is_suspicious, alert_if_any)
        """
        alert = None
        
        # Check for large transaction
        if amount_usd >= self.thresholds['large_transaction_usd']:
            alert = self._create_alert(
                user_id=user_id,
                alert_type="LARGE_TRANSACTION",
                severity="MEDIUM",
                description=f"Large transaction detected: ${amount_usd:,.2f}",
                transaction_ids=[transaction_id],
            )
        
        # Check for rapid transactions
        recent_transactions = self._get_recent_transactions(
            user_id,
            hours=self.thresholds['rapid_transactions_window_hours']
        )
        if len(recent_transactions) >= self.thresholds['rapid_transactions_count']:
            alert = self._create_alert(
                user_id=user_id,
                alert_type="RAPID_TRANSACTIONS",
                severity="HIGH",
                description=f"Rapid transaction pattern: {len(recent_transactions)} transactions in 24h",
                transaction_ids=recent_transactions,
            )
        
        # Check for unusual patterns
        if self._is_unusual_pattern(user_id, amount_usd):
            alert = self._create_alert(
                user_id=user_id,
                alert_type="UNUSUAL_PATTERN",
                severity="MEDIUM",
                description="Transaction amount deviates significantly from user's typical pattern",
                transaction_ids=[transaction_id],
            )
        
        if alert:
            self.alerts.append(alert)
            self.logger.warning(f"AML alert generated: {alert.alert_id} for user {user_id}")
            return True, alert
        
        return False, None
    
    def _create_alert(
        self,
        user_id: str,
        alert_type: str,
        severity: str,
        description: str,
        transaction_ids: List[str],
    ) -> AMLAlert:
        """Create an AML alert."""
        alert_id = f"AML_{datetime.now().timestamp()}"
        return AMLAlert(
            alert_id=alert_id,
            user_id=user_id,
            alert_type=alert_type,
            severity=severity,
            description=description,
            transaction_ids=transaction_ids,
            created_at=datetime.now(),
        )
    
    def _get_recent_transactions(self, user_id: str, hours: int) -> List[str]:
        """Get recent transaction IDs for user (mock implementation)."""
        # In production, query from transaction database
        return []
    
    def _is_unusual_pattern(self, user_id: str, amount: float) -> bool:
        """Check if transaction amount is unusual for user (mock implementation)."""
        # In production, analyze user's transaction history
        return False
    
    def get_active_alerts(self, user_id: Optional[str] = None) -> List[AMLAlert]:
        """Get active AML alerts."""
        alerts = [a for a in self.alerts if a.status == "OPEN"]
        if user_id:
            alerts = [a for a in alerts if a.user_id == user_id]
        return alerts


# Global instances
_kyc_service: Optional[KYCService] = None
_aml_service: Optional[AMLService] = None


def get_kyc_service() -> KYCService:
    """Get global KYC service instance."""
    global _kyc_service
    if _kyc_service is None:
        _kyc_service = KYCService()
    return _kyc_service


def get_aml_service() -> AMLService:
    """Get global AML service instance."""
    global _aml_service
    if _aml_service is None:
        _aml_service = AMLService()
    return _aml_service

