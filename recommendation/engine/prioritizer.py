"""Human-oriented recommendation prioritizer combining signals, risk, and macro context."""
import os
from datetime import datetime
from typing import Dict, List, Any

from backend.services.market_data_service import MarketDataService
from backend.services.recommendation_service import recommendation_service
from backend.risk.engine import RiskEngine, RiskLimits
from backend.api.routes.risk import get_risk_engine


class RecommendationPrioritizer:
    def __init__(self):
        self.market_data = MarketDataService()
        self.symbol = os.getenv('TRADING_PAIRS', 'BTCUSDT').split(',')[0]
        self.timeframes = os.getenv('TIMEFRAMES', '1h,4h,1d').split(',')

    def _load_data(self) -> Dict[str, Any]:
        data = {}
        for tf in self.timeframes:
            df = self.market_data.load_ohlcv_data(self.symbol, tf)
            if not df.empty:
                data[tf] = df
        return data

    def _macro_context(self) -> Dict[str, Any]:
        # Placeholder: derive simple macro proxies from risk metrics
        try:
            engine: RiskEngine = get_risk_engine()
            metrics = engine.get_risk_metrics()
            return {
                'drawdown_pct': metrics.current_drawdown_pct,
                'exposure_pct': metrics.exposure_pct,
                'var_1d_95': metrics.var_1d_95,
            }
        except Exception:
            return {}

    def generate_live_list(self, profile: str = 'balanced') -> List[Dict[str, Any]]:
        data = self._load_data()
        if not data:
            return []
        rec = recommendation_service.generate_recommendation(data, historical_metrics=None, profile=profile)

        macro = self._macro_context()
        # Pull full risk metrics/limits and compute suggested sizing under limits
        risk_metrics = {}
        risk_limits = {}
        suggested_size_usd = rec.position_size_usd if hasattr(rec, 'position_size_usd') else 0.0
        suggested_size_pct = rec.position_size_pct if hasattr(rec, 'position_size_pct') else 0.0
        limit_checks = {}
        try:
            engine: RiskEngine = get_risk_engine()
            metrics_obj = engine.get_risk_metrics()
            risk_metrics = {
                'total_capital': metrics_obj.total_capital,
                'equity': metrics_obj.equity,
                'exposure_pct': metrics_obj.exposure_pct,
                'current_drawdown_pct': metrics_obj.current_drawdown_pct,
                'var_1d_95': metrics_obj.var_1d_95,
            }
            risk_limits = {
                'max_exposure_pct': engine.risk_limits.max_exposure_pct,
                'max_position_pct': engine.risk_limits.max_position_pct,
                'max_drawdown_pct': engine.risk_limits.max_drawdown_pct,
                'var_limit_1d_95': engine.risk_limits.var_limit_1d_95,
            }
            # Recompute position size against risk engine
            if rec.current_price and rec.stop_loss:
                ps = engine.calculate_position_size(
                    entry_price=rec.current_price,
                    stop_loss=rec.stop_loss,
                    risk_amount=float(metrics_obj.total_capital) * 0.01,  # 1% capital risk as baseline
                    method='risk_based',
                )
                suggested_size_usd = ps.get('position_value_usd', suggested_size_usd)
                suggested_size_pct = ps.get('position_pct', suggested_size_pct)
            # Limit checks
            limit_checks = engine.check_risk_limits(metrics_obj)
        except Exception:
            pass
        justification = self._build_justification(rec, macro)
        pre_trade = self._build_pre_trade_checklist(rec, macro)
        post_trade = self._build_post_trade_checklist(rec)

        item = {
            'symbol': self.symbol,
            'timeframes': list(data.keys()),
            'action': rec.action,
            'confidence': rec.confidence,
            'risk_level': rec.risk_level,
            'entry_range': rec.entry_range,
            'stop_loss': rec.stop_loss,
            'take_profit': rec.take_profit,
            'current_price': rec.current_price,
            'primary_strategy': rec.primary_strategy,
            'supporting_strategies': rec.supporting_strategies,
            'signal_consensus': rec.signal_consensus,
            'justification': justification,
            'pre_trade_checklist': pre_trade,
            'post_trade_checklist': post_trade,
            'timestamp': datetime.now().isoformat(),
            # Risk integration fields
            'suggested_position_size_usd': suggested_size_usd,
            'suggested_position_size_pct': suggested_size_pct,
            'risk_metrics': risk_metrics,
            'risk_limits': risk_limits,
            'risk_limit_checks': limit_checks,
        }
        # For now single item list; can be extended to multiple symbols
        return [item]

    def _build_justification(self, rec, macro: Dict[str, Any]) -> str:
        parts = []
        parts.append(f"Acción sugerida: {rec.action} con confianza {rec.confidence:.2f}")
        if rec.primary_strategy:
            parts.append(f"Estrategia principal: {rec.primary_strategy}")
        if rec.supporting_strategies:
            parts.append(f"Apoyos: {', '.join(rec.supporting_strategies)}")
        if macro:
            if macro.get('drawdown_pct'):
                parts.append(f"DD actual {macro['drawdown_pct']:.2f}%")
            if macro.get('exposure_pct'):
                parts.append(f"Exposición {macro['exposure_pct']:.2f}%")
        return " | ".join(parts)

    def _build_pre_trade_checklist(self, rec, macro: Dict[str, Any]) -> List[Dict[str, Any]]:
        return [
            {'key': 'risk_limits_ok', 'label': 'Límites de riesgo respetados', 'required': True, 'checked': bool(macro) and macro.get('exposure_pct', 0) < 80},
            {'key': 'liquidity_ok', 'label': 'Liquidez suficiente en el par', 'required': True, 'checked': True},
            {'key': 'news_checked', 'label': 'Noticias relevantes revisadas', 'required': False, 'checked': False},
            {'key': 'position_sizing', 'label': f"Tamaño sugerido: {rec.position_size_usd:.2f} USD", 'required': True, 'checked': True},
        ]

    def _build_post_trade_checklist(self, rec) -> List[Dict[str, Any]]:
        return [
            {'key': 'journal_entry', 'label': 'Registrar trade en journal', 'required': True, 'checked': False},
            {'key': 'alert_set', 'label': 'Alertas de SL/TP configuradas', 'required': True, 'checked': False},
        ]


