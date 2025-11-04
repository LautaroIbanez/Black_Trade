# API Normalization and Transparency

This document describes the new normalized and transparency fields added to the recommendation API response.

## Overview

The recommendation system now provides enhanced transparency through normalized scoring, risk management metrics, and entry guidance. All values are properly normalized to ensure consistency and comparability.

## New Response Fields

### Risk Management Fields

#### `risk_reward_ratio` (float)
- **Description**: Risk-to-reward ratio for the trade
- **Range**: 0.0 to ∞ (typically 0.5 to 3.0)
- **Calculation**: `(take_profit - current_price) / (current_price - stop_loss)` for BUY
- **Example**: `1.5` means potential reward is 1.5x the risk

#### `suggested_position_size` (float)
- **Description**: Suggested position size multiplier
- **Range**: 0.1 to 3.0
- **Calculation**: Based on confidence level and risk profile
- **Example**: `1.2` means use 1.2x base position size

#### `risk_percentage` (float)
- **Description**: Risk percentage of the trade
- **Range**: 0.0 to 100.0
- **Calculation**: `((current_price - stop_loss) / current_price) * 100` for BUY
- **Example**: `2.5` means 2.5% risk per trade

### Normalization Fields

#### `normalized_weights_sum` (float)
- **Description**: Sum of all strategy weights (should equal 1.0)
- **Range**: 0.0 to 1.0
- **Purpose**: Validates that weights are properly normalized
- **Example**: `1.000` confirms proper normalization

### Entry Guidance

#### `entry_label` (string)
- **Description**: Descriptive guidance for entry timing
- **Values**: Contextual messages based on price position
- **Examples**:
  - `"Esperar pullback - Precio por debajo del rango de entrada"`
  - `"Entrada favorable - Precio en la parte baja del rango"`
  - `"Entrada inmediata - Precio en la parte alta del rango"`

## Normalization Details

### Signal Consensus Normalization
- **Before**: Could exceed 1.0 due to active signal boost
- **After**: Capped at 1.0 for consistent 0-1 range
- **Formula**: `min(raw_consensus * 2.0, 1.0)`

### Strategy Weights Normalization
- **Before**: Raw weights (confidence × score)
- **After**: Normalized to sum to 1.0
- **Formula**: `weight_i = (confidence_i × score_i) / Σ(confidence_j × score_j)`

### Confidence Floors
- **BUY/SELL**: Minimum 15% confidence
- **With 2+ strategies**: Minimum 30% confidence
- **High-ranked strategies**: Minimum 25% confidence
- **HOLD with high-ranked signals**: Minimum 10% confidence

## API Response Example

```json
{
  "action": "BUY",
  "confidence": 0.75,
  "entry_range": {
    "min": 49500.0,
    "max": 50500.0
  },
  "stop_loss": 48000.0,
  "take_profit": 52000.0,
  "current_price": 50000.0,
  "primary_strategy": "EMA_RSI_Strategy",
  "supporting_strategies": ["MACD_Crossover_Strategy"],
  "strategy_details": [
    {
      "strategy_name": "EMA_RSI_Strategy",
      "signal": 1,
      "strength": 0.8,
      "confidence": 0.7,
      "score": 0.9,
      "weight": 0.630,
      "timeframe": "1h"
    }
  ],
  "signal_consensus": 0.85,
  "risk_level": "MEDIUM",
  "contribution_breakdown": [...],
  "risk_reward_ratio": 1.0,
  "suggested_position_size": 1.2,
  "entry_label": "Entrada favorable - Precio en la parte baja del rango",
  "risk_percentage": 4.0,
  "normalized_weights_sum": 1.000
}
```

## Validation Rules

### Weight Normalization
- All strategy weights must sum to 1.0
- Individual weights must be between 0.0 and 1.0
- Weights are proportional to confidence × score

### Signal Consensus
- Must be between 0.0 and 1.0
- Represents agreement level among strategies
- Higher values indicate stronger consensus

### Risk Metrics
- Risk/reward ratio must be positive
- Position size must be between 0.1 and 3.0
- Risk percentage must be between 0.0 and 100.0

## Testing

Run the normalization tests to validate proper behavior:

```bash
python -m pytest backend/tests/test_normalization.py -v
```

## Migration Notes

### Frontend Updates
- New fields are optional and have default values
- Existing code will continue to work
- New transparency fields can be displayed optionally

### Backend Compatibility
- All new fields have default values
- Existing API clients will receive the new fields
- No breaking changes to existing functionality

## Best Practices

### Using Risk Metrics
1. **Risk/Reward Ratio**: Prefer ratios ≥ 1.0 for favorable trades
2. **Position Size**: Adjust based on account size and risk tolerance
3. **Risk Percentage**: Keep individual trade risk ≤ 2% of account
4. **Entry Labels**: Follow guidance for optimal entry timing

### Monitoring Normalization
1. **Weights Sum**: Should always equal 1.000
2. **Signal Consensus**: Higher values indicate stronger signals
3. **Confidence Floors**: Ensure minimum confidence thresholds are met
4. **Entry Labels**: Provide clear guidance for trade execution

This normalization and transparency enhancement provides users with complete visibility into recommendation generation while ensuring consistent, comparable metrics across all trading scenarios.






