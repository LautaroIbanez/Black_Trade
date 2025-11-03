"""Integration tests for recommendation tracking (accept/reject/outcome)."""
import pytest
from datetime import datetime
from typing import Dict, Any

from backend.repositories.recommendation_tracking_repository import RecommendationTrackingRepository
from backend.repositories.kyc_repository import KYCRepository
from backend.db.init_db import initialize_database
from backend.models.recommendations import RecommendationLog


@pytest.fixture
def test_db():
    """Initialize test database."""
    initialize_database()


@pytest.fixture
def tracking_repo(test_db):
    """Create tracking repository instance."""
    return RecommendationTrackingRepository()


@pytest.fixture
def sample_payload():
    """Sample recommendation payload for testing."""
    return {
        "symbol": "BTCUSDT",
        "action": "BUY",
        "confidence": 0.85,
        "primary_strategy": "EMA_RSI",
        "current_price": 45000.0,
        "stop_loss": 44000.0,
        "take_profit": 48000.0,
        "timeframe": "1h",
        "reason": "Strong bullish consensus from multiple strategies"
    }


@pytest.fixture
def sample_checklist():
    """Sample checklist data for testing."""
    return {
        "pre_trade": [
            {"key": "liquidity_check", "label": "Liquidity OK", "checked": True, "required": True},
            {"key": "risk_limits", "label": "Within risk limits", "checked": True, "required": True},
            {"key": "market_conditions", "label": "Favorable conditions", "checked": True, "required": False}
        ],
        "post_trade": []
    }


class TestRecommendationTrackingFlow:
    """Test complete recommendation tracking flow."""
    
    def test_create_accepted_recommendation(self, tracking_repo, sample_payload, sample_checklist):
        """Test creating an accepted recommendation."""
        rec_id = tracking_repo.create(
            status='accepted',
            symbol='BTCUSDT',
            timeframe='1h',
            payload=sample_payload,
            user_id='test_user',
            checklist=sample_checklist,
            notes='Good opportunity'
        )
        
        assert rec_id > 0
        
        # Verify record was created
        history = tracking_repo.history(limit=1)
        assert len(history) > 0
        rec = history[0]
        assert rec['id'] == rec_id
        assert rec['status'] == 'accepted'
        assert rec['symbol'] == 'BTCUSDT'
        assert rec['user_id'] == 'test_user'
        assert rec['checklist']['pre_trade'][0]['checked'] is True
    
    def test_create_rejected_recommendation(self, tracking_repo, sample_payload):
        """Test creating a rejected recommendation."""
        rec_id = tracking_repo.create(
            status='rejected',
            symbol='ETHUSDT',
            timeframe='4h',
            payload=sample_payload,
            user_id='test_user',
            notes='Too risky'
        )
        
        assert rec_id > 0
        
        history = tracking_repo.history(limit=1)
        rec = history[0]
        assert rec['status'] == 'rejected'
        assert 'Too risky' in rec['notes']
    
    def test_update_to_outcome(self, tracking_repo, sample_payload, sample_checklist):
        """Test updating recommendation with outcome and PnL."""
        # Create accepted recommendation
        rec_id = tracking_repo.create(
            status='accepted',
            symbol='BTCUSDT',
            timeframe='1h',
            payload=sample_payload,
            user_id='test_user',
            checklist=sample_checklist
        )
        
        # Update with outcome
        ok = tracking_repo.update(
            rec_id=rec_id,
            outcome='win',
            realized_pnl=250.50,
            notes='TP hit at 48000'
        )
        
        assert ok is True
        
        # Verify outcome was recorded
        history = tracking_repo.history(limit=1)
        rec = history[0]
        assert rec['id'] == rec_id
        assert rec['outcome'] == 'win'
        assert rec['realized_pnl'] == 250.50
        assert rec['decided_at'] is not None
        assert 'TP hit' in rec['notes']
    
    def test_update_with_loss_outcome(self, tracking_repo, sample_payload):
        """Test updating recommendation with loss outcome."""
        rec_id = tracking_repo.create(
            status='accepted',
            symbol='BTCUSDT',
            timeframe='1h',
            payload=sample_payload,
            user_id='test_user'
        )
        
        ok = tracking_repo.update(
            rec_id=rec_id,
            outcome='loss',
            realized_pnl=-100.0,
            notes='SL triggered'
        )
        
        assert ok is True
        
        history = tracking_repo.history(limit=1)
        rec = history[0]
        assert rec['outcome'] == 'loss'
        assert rec['realized_pnl'] == -100.0
    
    def test_update_checklist_only(self, tracking_repo, sample_payload, sample_checklist):
        """Test updating checklist without changing status."""
        rec_id = tracking_repo.create(
            status='accepted',
            symbol='BTCUSDT',
            timeframe='1h',
            payload=sample_payload,
            user_id='test_user',
            checklist=sample_checklist
        )
        
        # Update only checklist
        updated_checklist = {
            "pre_trade": sample_checklist['pre_trade'],
            "post_trade": [
                {"key": "risk_management", "label": "Risk managed", "checked": True}
            ]
        }
        
        ok = tracking_repo.update(
            rec_id=rec_id,
            checklist=updated_checklist
        )
        
        assert ok is True
        
        history = tracking_repo.history(limit=1)
        rec = history[0]
        assert len(rec['checklist']['post_trade']) > 0
    
    def test_update_nonexistent_recommendation(self, tracking_repo):
        """Test updating non-existent recommendation returns False."""
        ok = tracking_repo.update(
            rec_id=99999,
            status='accepted'
        )
        
        assert ok is False
    
    def test_get_metrics_with_multiple_recommendations(self, tracking_repo, sample_payload):
        """Test metrics calculation with multiple tracked recommendations."""
        # Create various recommendations
        tracking_repo.create('accepted', 'BTCUSDT', '1h', sample_payload, checklist={})
        tracking_repo.create('rejected', 'ETHUSDT', '1h', sample_payload)
        tracking_repo.create('accepted', 'SOLUSDT', '1h', sample_payload)
        
        # Add outcomes for accepted ones
        history = tracking_repo.history(limit=10)
        for rec in history[:3]:
            if rec['status'] == 'accepted':
                tracking_repo.update(rec['id'], outcome='win', realized_pnl=100.0)
                break  # Only update first accepted
        
        metrics = tracking_repo.get_metrics(days=30)
        
        assert metrics['total_decisions'] >= 3
        assert metrics['accepted'] >= 2
        assert metrics['rejected'] >= 1
        assert metrics['accepted_rate'] > 0
        assert metrics['tracked_outcomes'] >= 1
        assert metrics['wins'] >= 1
        assert metrics['hit_ratio'] > 0
        assert isinstance(metrics['total_realized_pnl'], float)
    
    def test_metrics_empty_history(self, tracking_repo):
        """Test metrics with no history returns zero values."""
        metrics = tracking_repo.get_metrics(days=30)
        
        assert metrics['total_decisions'] == 0
        assert metrics['accepted'] == 0
        assert metrics['rejected'] == 0
        assert metrics['accepted_rate'] == 0
        assert metrics['hit_ratio'] == 0
        assert metrics['total_realized_pnl'] == 0.0
    
    def test_history_ordering(self, tracking_repo, sample_payload):
        """Test history returns records in descending order by created_at."""
        tracking_repo.create('accepted', 'BTCUSDT', '1h', sample_payload)
        tracking_repo.create('accepted', 'ETHUSDT', '1h', sample_payload)
        tracking_repo.create('accepted', 'SOLUSDT', '1h', sample_payload)
        
        history = tracking_repo.history(limit=10)
        
        # Check ordering (most recent first)
        for i in range(len(history) - 1):
            if history[i]['created_at'] and history[i+1]['created_at']:
                assert history[i]['created_at'] >= history[i+1]['created_at']
    
    def test_history_limit(self, tracking_repo, sample_payload):
        """Test history respects limit parameter."""
        # Create 10 recommendations
        for i in range(10):
            tracking_repo.create('accepted', f'SYMBOL{i}', '1h', sample_payload)
        
        # Request only 5
        history = tracking_repo.history(limit=5)
        assert len(history) == 5


class TestRecommendationModel:
    """Test RecommendationLog model serialization."""
    
    def test_to_dict_serialization(self, tracking_repo, sample_payload, sample_checklist):
        """Test RecommendationLog.to_dict() serialization."""
        rec_id = tracking_repo.create(
            status='accepted',
            symbol='BTCUSDT',
            timeframe='1h',
            payload=sample_payload,
            user_id='test_user',
            checklist=sample_checklist,
            notes='Test note'
        )
        
        history = tracking_repo.history(limit=1)
        rec_dict = history[0]
        
        # Verify all expected fields are present
        assert 'id' in rec_dict
        assert 'status' in rec_dict
        assert 'symbol' in rec_dict
        assert 'timeframe' in rec_dict
        assert 'user_id' in rec_dict
        assert 'payload' in rec_dict
        assert 'checklist' in rec_dict
        assert 'notes' in rec_dict
        assert 'created_at' in rec_dict
        assert 'updated_at' in rec_dict
        assert 'outcome' in rec_dict
        assert 'realized_pnl' in rec_dict
        assert 'decided_at' in rec_dict
        
        # Verify types
        assert isinstance(rec_dict['id'], int)
        assert isinstance(rec_dict['payload'], dict)
        assert isinstance(rec_dict['checklist'], dict)
    
    def test_to_dict_with_outcome(self, tracking_repo, sample_payload):
        """Test to_dict with outcome and PnL populated."""
        rec_id = tracking_repo.create(
            status='accepted',
            symbol='BTCUSDT',
            timeframe='1h',
            payload=sample_payload
        )
        
        tracking_repo.update(rec_id, outcome='win', realized_pnl=500.75)
        
        history = tracking_repo.history(limit=1)
        rec_dict = history[0]
        
        assert rec_dict['outcome'] == 'win'
        assert rec_dict['realized_pnl'] == 500.75
        assert rec_dict['decided_at'] is not None
        assert isinstance(rec_dict['realized_pnl'], float)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

