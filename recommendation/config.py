"""Recommendation configuration for active timeframes and consensus calibration."""
import os

# Default active timeframes used when TIMEFRAMES env var is not provided
TIMEFRAMES_ACTIVE = [
    '15m', '1h', '2h', '4h', '12h', '1d', '1w'
]

# Consensus calibration parameters for mixed scenarios (BUY/SELL/HOLD combinations)
# These parameters control how consensus is calculated when opposing signals coexist.

# Maximum consensus value in mixed scenarios with opposing signals
# When BUY and SELL signals coexist (e.g., 2 BUY / 1 SELL / 1 HOLD), this cap ensures
# consensus stays closer to the weighted average rather than inflating artificially.
# Rationale: Opposing signals indicate market uncertainty, so consensus should reflect
# moderation rather than false conviction. Lower values = more conservative consensus.
# Default: 0.60 (60% max consensus when mixed signals present)
MIXED_CONSENSUS_CAP = float(os.getenv('MIXED_CONSENSUS_CAP', '0.60'))

# Neutral count factor: additional penalty when multiple HOLD signals are present
# This factor scales down consensus further when hold_count exceeds a threshold.
# Formula: if hold_count > neutral_threshold, apply penalty = (neutral_count_factor ** excess_neutrals)
# Rationale: Many HOLD signals indicate broader market indecision beyond simple opposition.
# Lower values = stronger penalty. Default: 0.95 (5% penalty per excess neutral above threshold)
NEUTRAL_COUNT_FACTOR = float(os.getenv('NEUTRAL_COUNT_FACTOR', '0.95'))

# Threshold for applying neutral count penalty (number of HOLD signals)
# When hold_count exceeds this, the neutral_count_factor penalty applies.
# Default: 2 (if more than 2 HOLD signals, apply additional scaling)
NEUTRAL_COUNT_THRESHOLD = int(os.getenv('NEUTRAL_COUNT_THRESHOLD', '2'))

# Neutral floor: minimum weight factor for neutrals when mixed (legacy parameter, kept for compatibility)
# Used to prevent consensus saturation in mixed scenarios. See RecommendationService.__init__
NEUTRAL_FLOOR = float(os.getenv('NEUTRAL_FLOOR', '0.3'))

# Maximum deviation from simple majority in mixed scenarios (legacy parameter, kept for compatibility)
# See RecommendationService.__init__ for usage.
MAX_CONSENSUS_DELTA = float(os.getenv('MAX_CONSENSUS_DELTA', '0.1'))


