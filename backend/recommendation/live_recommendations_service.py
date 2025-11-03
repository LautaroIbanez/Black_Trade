"""Service for publishing and retrieving live recommendations without manual refresh."""
from typing import Dict, Any, List, Optional
from datetime import datetime

from backend.repositories.live_results_repository import LiveResultsRepository


_cache: Dict[str, Any] = {
    'last_results': {},
    'freshness_ts': None,
}


class LiveRecommendationsService:
    def __init__(self):
        self.repo = LiveResultsRepository()

    def publish(self, symbol: str, timeframes: List[str], payload: Dict[str, Any]) -> None:
        # Update in-memory cache structure similar to last_results by timeframe
        global _cache
        _cache['last_results'] = {
            tf: [payload] for tf in timeframes
        }
        _cache['freshness_ts'] = datetime.utcnow()

    def get_freshness(self) -> Optional[datetime]:
        return _cache.get('freshness_ts')

    def get_cached_results(self) -> Dict[str, Any]:
        return _cache.get('last_results') or {}

    def get_latest_snapshot(self, symbol: str, timeframes: List[str]) -> Optional[Dict[str, Any]]:
        # Try in-memory cache first
        cached = self.get_cached_results()
        if cached:
            # Return the first available timeframe item
            for tf in timeframes:
                items = cached.get(tf)
                if items:
                    return items[0]
        # Fallback to DB: fetch latest per a preferred timeframe order
        for tf in timeframes:
            latest = self.repo.get_latest(symbol, tf, limit=1)
            if latest:
                return latest[0]['payload']
        return None


# Global instance
live_recommendations_service = LiveRecommendationsService()


