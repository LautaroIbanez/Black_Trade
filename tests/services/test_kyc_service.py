"""Unit tests for KYC service."""
import pytest
from datetime import datetime

from backend.compliance.kyc_aml import KYCService, KYCRecord


def test_register_user():
    """Test user registration for KYC."""
    kyc = KYCService()
    record = kyc.register_user(
        user_id="test_user",
        name="Test User",
        email="test@example.com",
        country="AR",
        document_type="passport",
        document_number="ABC123"
    )
    
    assert isinstance(record, KYCRecord)
    assert record.user_id == "test_user"
    assert record.name == "Test User"
    assert record.email == "test@example.com"
    assert record.country == "AR"
    assert record.verified == False
    assert record.document_type == "passport"
    assert record.document_number == "ABC123"


def test_verify_user():
    """Test user verification."""
    kyc = KYCService()
    kyc.register_user("test_user", "Test User", "test@example.com", "AR")
    
    result = kyc.verify_user("test_user", {"document_type": "passport", "document_number": "ABC123"})
    assert result == True
    
    record = kyc.get_verification_status("test_user")
    assert record is not None
    assert record.verified == True
    assert record.verification_date is not None


def test_verify_user_not_found():
    """Test verification fails for non-existent user."""
    kyc = KYCService()
    result = kyc.verify_user("nonexistent", {})
    assert result == False


def test_get_verification_status():
    """Test getting verification status."""
    kyc = KYCService()
    
    # Not registered
    status = kyc.get_verification_status("unknown")
    assert status is None
    
    # Registered but not verified
    kyc.register_user("user1", "User One", "user1@example.com", "US")
    status = kyc.get_verification_status("user1")
    assert status is not None
    assert status.verified == False
    
    # Verified
    kyc.verify_user("user1", {})
    status = kyc.get_verification_status("user1")
    assert status.verified == True


def test_is_verified():
    """Test checking if user is verified."""
    kyc = KYCService()
    
    assert kyc.is_verified("unknown") == False
    
    kyc.register_user("user2", "User Two", "user2@example.com", "CA")
    assert kyc.is_verified("user2") == False
    
    kyc.verify_user("user2", {})
    assert kyc.is_verified("user2") == True

