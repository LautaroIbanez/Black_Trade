# Technical Debt Cleanup: Static SL/TP Module

## Summary
- The legacy static percentage-based trade level calculator in `RecommendationService._calculate_trade_levels` has been deprecated and disabled by default.
- The system now derives SL/TP from strategy-specific logic and the `RiskManagementService` with ATR, support/resistance, and profile-aware rules.

## Feature Flag
- To guard against accidental activation, the static module is wrapped with a feature flag:
  - `FEATURE_STATIC_LEVELS` (default: `false`)
  - Set to `true` to temporarily re-enable for targeted tests or migration work.

Example (PowerShell):
```powershell
$env:FEATURE_STATIC_LEVELS='true'
```

## Rationale
- Static levels conflict with the adaptive risk framework (ATR, SR, profiles) and can reduce coherence across components.
- Removing it from the runtime path ensures a single source of truth for SL/TP: strategies + risk management service.

## Tests
- Tests that previously exercised `_calculate_trade_levels` now assert the guard raises by default.
- End-to-end behavior is unchanged because production paths use `risk_management_service.aggregate_risk_targets`.

## Next Steps
- If any external clients depend on static levels, migrate them to read `stop_loss`/`take_profit` from the recommendation output or use strategy-level `risk_targets`.


