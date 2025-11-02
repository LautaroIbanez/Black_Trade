from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
import numpy as np
from strategies.strategy_base import StrategyBase
from data.feeds.rotation_loader import (
    load_rotation_universe,
    align_universe_timestamps,
    rank_universe_by_strength,
    rank_universe_by_returns,
    rank_universe_by_sharpe,
    default_universe
)


class CryptoRotationStrategy(StrategyBase):
    """Multi-asset rotation strategy that selects winners/losers based on relative strength.

    This strategy:
    1. Loads multiple symbols from the rotation universe
    2. Aligns timestamps across all symbols
    3. Calculates relative strength, returns, or Sharpe ratios for ranking
    4. Generates BUY signals for top-ranked symbols (winners)
    5. Generates SELL signals for bottom-ranked symbols (losers)
    6. Only signals when there's sufficient divergence between symbols
    """

    def __init__(self, 
                 lookback: int = 50,
                 universe: Optional[List[str]] = None,
                 ranking_method: str = "strength",  # "strength", "returns", "sharpe"
                 min_divergence: float = 0.02,  # Minimum spread between top/bottom for signal
                 top_n: int = 1,  # Number of top symbols to buy
                 bottom_n: int = 1,  # Number of bottom symbols to sell
                 rebalance_periods: int = 5,  # Re-evaluate rankings every N periods
                 **kwargs):
        """Initialize CryptoRotation strategy.
        
        Args:
            lookback: EMA period for relative strength calculation
            universe: List of symbols to include (None = use default)
            ranking_method: Method for ranking ("strength", "returns", "sharpe")
            min_divergence: Minimum spread between top/bottom rank for signal (0.02 = 2%)
            top_n: Number of top symbols to signal BUY
            bottom_n: Number of bottom symbols to signal SELL
            rebalance_periods: How often to re-evaluate rankings
        """
        params = {
            "lookback": lookback,
            "ranking_method": ranking_method,
            "min_divergence": min_divergence,
            "top_n": top_n,
            "bottom_n": bottom_n,
            "rebalance_periods": rebalance_periods
        }
        if universe:
            params["universe"] = universe
        
        super().__init__(name="CryptoRotation", params=params, **kwargs)
        self.lookback = lookback
        self.universe = universe or default_universe()
        self.ranking_method = ranking_method
        self.min_divergence = min_divergence
        self.top_n = top_n
        self.bottom_n = bottom_n
        self.rebalance_periods = rebalance_periods

    def _load_and_rank_universe(self, timeframe: str, strict: bool = False) -> Tuple[Dict[str, pd.DataFrame], List[Tuple[str, float]]]:
        """Load universe data and compute rankings.
        
        Args:
            timeframe: Timeframe string (e.g., '1h', '4h')
            strict: If True, raise errors when symbols are missing. If False, warn and continue.
            
        Returns:
            Tuple of (universe dict, ranked symbols list)
            
        Raises:
            RuntimeError: If strict=True and rotation cannot be performed (insufficient symbols)
        """
        import logging
        logger = logging.getLogger(__name__)
        
        # Load universe with validation
        min_required = 2  # Minimum for rotation (at least 2 symbols needed)
        try:
            universe = load_rotation_universe(
                self.universe, 
                timeframe, 
                min_required=min_required,
                strict=strict
            )
        except (ValueError, RuntimeError) as e:
            if strict:
                raise RuntimeError(f"Cannot perform rotation: {str(e)}")
            logger.error(f"Rotation loader error: {str(e)}")
            return {}, []
        
        if not universe:
            error_msg = f"No data loaded for universe {self.universe}"
            if strict:
                raise RuntimeError(error_msg)
            logger.error(error_msg)
            return {}, []
        
        # Log participation metrics
        loaded_symbols = list(universe.keys())
        participation_pct = (len(loaded_symbols) / len(self.universe)) * 100
        logger.info(f"Rotation universe loaded: {len(loaded_symbols)}/{len(self.universe)} symbols ({participation_pct:.1f}%) - {loaded_symbols}")
        
        # Validate sufficient symbols for rotation
        if len(universe) < 2:
            error_msg = f"Insufficient symbols for rotation: {len(universe)} < 2. Cannot perform multi-asset rotation."
            if strict:
                raise RuntimeError(error_msg)
            logger.warning(error_msg)
            return {}, []
        
        # Align timestamps
        universe = align_universe_timestamps(universe)
        
        # Validate alignment result
        if not universe:
            error_msg = "Timestamp alignment failed - no common timestamps found"
            if strict:
                raise RuntimeError(error_msg)
            logger.error(error_msg)
            return {}, []
        
        # Count valid aligned symbols (non-empty after alignment)
        valid_symbols = [sym for sym, df in universe.items() if df is not None and not df.empty]
        if len(valid_symbols) < 2:
            error_msg = f"After alignment, insufficient valid symbols: {len(valid_symbols)} < 2"
            if strict:
                raise RuntimeError(error_msg)
            logger.warning(error_msg)
        
        # Rank by selected method
        try:
            if self.ranking_method == "strength":
                ranked = rank_universe_by_strength(universe, ema_span=self.lookback)
            elif self.ranking_method == "returns":
                ranked = rank_universe_by_returns(universe, periods=self.lookback)
            elif self.ranking_method == "sharpe":
                ranked = rank_universe_by_sharpe(universe, window=self.lookback)
            else:
                ranked = rank_universe_by_strength(universe, ema_span=self.lookback)
            
            # Log ranking result
            if ranked:
                top_symbols = [sym for sym, _ in ranked[:3]]  # Top 3
                logger.debug(f"Ranking (top 3): {top_symbols}")
            
            return universe, ranked
            
        except Exception as e:
            error_msg = f"Error during ranking: {str(e)}"
            if strict:
                raise RuntimeError(error_msg)
            logger.error(error_msg)
            return {}, []
    
    def generate_signals(self, df: pd.DataFrame, timeframe: str = "1h", current_symbol: Optional[str] = None, strict: bool = False) -> pd.DataFrame:
        """Generate rotation signals based on multi-symbol ranking.
        
        The signal for the current symbol depends on its ranking relative to other
        symbols in the universe. Only signals when there's sufficient divergence.
        
        Args:
            df: DataFrame for current symbol (must have 'timestamp' or infer timeframe)
            timeframe: Timeframe for universe data
            current_symbol: Symbol name for current DataFrame (if None, tries to infer)
            
        Returns:
            DataFrame with 'signal', 'strength', and rotation metadata
        """
        data = df.copy()
        if data.empty:
            data['signal'] = 0
            data['strength'] = 0.0
            data['rotation_rank'] = 0
            return data
        
        # Try to infer current symbol from metadata or use first in universe
        if current_symbol is None:
            current_symbol = getattr(self, '_current_symbol', None) or self.universe[0]
        
        # Load universe and rank with strict parameter
        universe, ranked = self._load_and_rank_universe(timeframe, strict=strict)
        
        # Telemetry: record universe state
        data['universe_symbols_count'] = len(universe)
        data['universe_participation'] = len(universe) / len(self.universe) if self.universe else 0.0
        data['rotation_available'] = len(universe) >= 2
        
        if not universe or not ranked:
            # Fallback to single-symbol logic when rotation cannot be performed
            import logging
            logger = logging.getLogger(__name__)
            if strict:
                # In strict mode, raise error instead of silently falling back
                error_msg = (
                    f"CryptoRotation cannot generate signals in strict mode: "
                    f"universe={len(universe)}, ranked={len(ranked) if ranked else 0}, "
                    f"current_symbol={current_symbol}. Insufficient symbols for multi-asset rotation."
                )
                logger.error(error_msg)
                raise RuntimeError(error_msg)
            
            # In non-strict mode, log warning and fallback
            logger.warning(
                f"CryptoRotation fallback to single-symbol mode: "
                f"universe={len(universe)}, ranked={len(ranked) if ranked else 0}, "
                f"current_symbol={current_symbol}. This degrades strategy from multi-asset rotation to single-asset EMA."
            )
            
            # Degrade to single-symbol EMA-based logic
            data['ema'] = data['close'].ewm(span=self.lookback, adjust=False).mean()
            data['rel'] = (data['close'] / data['ema']) - 1.0
            data['strength'] = data['rel'].rolling(5).mean().fillna(0.0).clip(-1, 1)
            data['signal'] = 0
            data.loc[data['rel'] > 0.005, 'signal'] = 1
            data.loc[data['rel'] < -0.005, 'signal'] = -1
            data['rotation_rank'] = -1  # -1 indicates fallback mode
            data['rotation_mode'] = 'fallback'  # Flag for telemetry
            return data
        
        # Find current symbol's rank
        symbol_rank = -1
        symbol_score = float('-inf')
        for idx, (sym, score) in enumerate(ranked):
            if sym == current_symbol:
                symbol_rank = idx
                symbol_score = score
                break
        
        # Determine if we should signal based on divergence
        if len(ranked) < 2:
            data['signal'] = 0
            data['strength'] = 0.0
            data['rotation_rank'] = 0
            return data
        
        top_score = ranked[0][1] if ranked else 0.0
        bottom_score = ranked[-1][1] if ranked else 0.0
        divergence = abs(top_score - bottom_score)
        
        # Initialize signal columns
        data['rotation_rank'] = symbol_rank
        data['divergence'] = divergence
        data['signal'] = 0
        data['strength'] = 0.0
        data['rotation_mode'] = 'multi_asset'  # Flag for telemetry
        data['ranked_symbols_count'] = len(ranked)
        
        # Only signal if divergence is sufficient
        if divergence >= self.min_divergence:
            # Check if current symbol is in top N (BUY)
            if symbol_rank >= 0 and symbol_rank < self.top_n:
                data['signal'] = 1
                data['strength'] = min(max(symbol_score / (top_score + 1e-9), 0.0), 1.0) if top_score > 0 else 0.0
            # Check if current symbol is in bottom N (SELL)
            elif symbol_rank >= len(ranked) - self.bottom_n:
                data['signal'] = -1
                data['strength'] = min(max(abs(symbol_score) / (abs(bottom_score) + 1e-9), 0.0), 1.0) if bottom_score < 0 else 0.0
        else:
            # Insufficient divergence - neutral
            data['signal'] = 0
            data['strength'] = 0.0
        
        return data

    def generate_trades(self, df: pd.DataFrame) -> List[Dict]:
        """Generate trades from rotation signals with rebalancing logic.
        
        Trades are generated when:
        - Entering a position on BUY/SELL signal (symbol enters top/bottom)
        - Exiting when signal flips or when rebalance period suggests re-evaluation
        - Forcing exit at end of data
        
        Args:
            df: DataFrame with 'signal', 'timestamp', 'close' columns
            
        Returns:
            List of trade dictionaries
        """
        trades: List[Dict] = []
        if df.empty or 'signal' not in df.columns:
            return trades
        
        position = None
        last_rebalance_idx = -self.rebalance_periods  # Allow immediate first signal
        
        for idx in range(len(df)):
            row = df.iloc[idx]
            ts = row.get('timestamp')
            price = float(row.get('close', 0))
            sig = int(row.get('signal', 0))
            divergence = row.get('divergence', 0.0)
            
            # Rebalance check: close position if rebalance period elapsed
            if position is not None and (idx - last_rebalance_idx) >= self.rebalance_periods:
                # Check if we should maintain position or exit
                # Exit if signal changed or divergence dropped
                if (position['side'] == 'long' and sig <= 0) or (position['side'] == 'short' and sig >= 0):
                    exit_price = price
                    pnl = (exit_price - position['entry_price']) if position['side'] == 'long' else (position['entry_price'] - exit_price)
                    trade = {
                        "entry_price": position['entry_price'],
                        "exit_price": exit_price,
                        "side": position['side'],
                        "pnl": pnl,
                        "entry_time": position['entry_time'],
                        "exit_time": ts,
                        "exit_reason": "rebalance"
                    }
                    trades.append(trade)
                    position = None
                    last_rebalance_idx = idx
            
            # Entry conditions (only if no position or after rebalance exit)
            if position is None:
                if sig == 1:  # BUY signal - symbol in top N
                    position = {
                        "side": "long",
                        "entry_price": price,
                        "entry_time": ts,
                        "divergence_at_entry": divergence
                    }
                    last_rebalance_idx = idx
                elif sig == -1:  # SELL signal - symbol in bottom N
                    position = {
                        "side": "short",
                        "entry_price": price,
                        "entry_time": ts,
                        "divergence_at_entry": divergence
                    }
                    last_rebalance_idx = idx
                continue
            
            # Exit on opposite signal or loss of divergence
            should_exit = False
            exit_reason = None
            
            if position['side'] == 'long' and sig == -1:
                should_exit = True
                exit_reason = "opposite_signal"
            elif position['side'] == 'short' and sig == 1:
                should_exit = True
                exit_reason = "opposite_signal"
            elif divergence < self.min_divergence:
                should_exit = True
                exit_reason = "divergence_lost"
            
            if should_exit:
                exit_price = price
                pnl = (exit_price - position['entry_price']) if position['side'] == 'long' else (position['entry_price'] - exit_price)
                trade = {
                    "entry_price": position['entry_price'],
                    "exit_price": exit_price,
                    "side": position['side'],
                    "pnl": pnl,
                    "entry_time": position['entry_time'],
                    "exit_time": ts,
                    "exit_reason": exit_reason
                }
                trades.append(trade)
                position = None
        
        # Close any open position at last price
        if position is not None and not df.empty:
            last = df.iloc[-1]
            exit_price = float(last.get('close', 0))
            pnl = (exit_price - position['entry_price']) if position['side'] == 'long' else (position['entry_price'] - exit_price)
            trade = {
                "entry_price": position['entry_price'],
                "exit_price": exit_price,
                "side": position['side'],
                "pnl": pnl,
                "entry_time": position['entry_time'],
                "exit_time": last.get('timestamp'),
                "exit_reason": "forced_close"
            }
            trades.append(trade)
        
        return trades

    def generate_signal(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Generate current signal from latest candle data, compatible with recommendation service."""
        if df.empty:
            return {
                "signal": 0,
                "strength": 0.0,
                "confidence": 0.0,
                "reason": "No data available",
                "price": 0.0,
                "timestamp": None
            }
        
        # Try to infer timeframe from DataFrame metadata or use default
        timeframe = getattr(self, '_current_timeframe', '1h')
        
        # Try to infer current symbol from metadata or use first in universe
        current_symbol = getattr(self, '_current_symbol', None) or (self.universe[0] if self.universe else None)
        
        # Use non-strict mode by default for recommendation service (degradation allowed)
        strict_mode = getattr(self, '_strict_mode', False)
        
        # Generate signals with inferred parameters
        signals_df = self.generate_signals(df, timeframe=timeframe, current_symbol=current_symbol, strict=strict_mode)
        
        if signals_df.empty:
            return {
                "signal": 0,
                "strength": 0.0,
                "confidence": 0.0,
                "reason": "No signals generated",
                "price": float(df['close'].iloc[-1]) if not df.empty else 0.0,
                "timestamp": df['timestamp'].iloc[-1] if not df.empty and 'timestamp' in df.columns else None
            }
        
        # Get the latest signal
        latest_row = signals_df.iloc[-1]
        signal_value = int(latest_row.get('signal', 0))
        strength = float(latest_row.get('strength', 0.0))
        
        # Get current price
        current_price = float(df['close'].iloc[-1]) if not df.empty else 0.0
        
        # Calculate confidence based on signal consistency and strength
        recent_signals = signals_df['signal'].tail(5)
        if len(recent_signals) > 1:
            base_confidence = strength
            signal_consistency = (recent_signals == signal_value).sum() / len(recent_signals)
            consistency_boost = 1.0 + (signal_consistency * 0.5)
            active_boost = 1.5 if signal_value != 0 else 0.8
            confidence = min(base_confidence * consistency_boost * active_boost, 1.0)
        else:
            active_boost = 1.5 if signal_value != 0 else 0.8
            confidence = min(strength * active_boost, 1.0)
        
        # Ensure minimum confidence for active signals
        if signal_value != 0 and confidence < 0.1:
            confidence = 0.1
        
        # Generate reason incorporating rotation metadata
        rotation_mode = latest_row.get('rotation_mode', 'unknown')
        universe_count = latest_row.get('universe_symbols_count', 0)
        rotation_rank = latest_row.get('rotation_rank', -1)
        
        if rotation_mode == 'fallback':
            reason = f"CryptoRotation (fallback mode - only {universe_count} symbol(s)): EMA-based signal"
        elif rotation_mode == 'multi_asset' and rotation_rank >= 0:
            reason = f"CryptoRotation (rank {rotation_rank+1}/{universe_count}): Multi-asset rotation signal"
        else:
            reason = f"CryptoRotation: {self.ranking_method} ranking signal"
        
        return {
            "signal": signal_value,
            "strength": strength,
            "confidence": confidence,
            "reason": reason,
            "price": current_price,
            "timestamp": latest_row.get('timestamp', df['timestamp'].iloc[-1] if not df.empty and 'timestamp' in df.columns else None)
        }
    
    def calculate_exit_levels(self, df: pd.DataFrame, signal: int, entry_price: float) -> Dict[str, float]:
        # Use default fallback in base class via risk_targets pathway
        return self._default_exit_levels(df, signal, entry_price)



