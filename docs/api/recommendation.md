# Recommendation API Documentation

This document describes the real-time recommendation API endpoints and their responses.

## Table of Contents

1. [Overview](#overview)
2. [Endpoints](#endpoints)
3. [Response Formats](#response-formats)
4. [Strategy Details](#strategy-details)
5. [Error Handling](#error-handling)
6. [Examples](#examples)

## Overview

The recommendation API provides real-time trading recommendations based on multiple strategy signals. It analyzes current market data across different timeframes and generates actionable trading advice with detailed strategy analysis.

> Warning: La suite de QA de extremo a extremo está en progreso y algunas estrategias se encuentran en fase de calibración fina. Ver resultados reales en `docs/qa/status.md` (actualizado automáticamente tras correr `.venv\\Scripts\\pytest -q`). Los campos y umbrales documentados son estables, pero los valores de confianza/pesos pueden variar entre versiones menores hasta concluir la calibración.

### Key Features

- **Real-time Signal Analysis**: Uses current market data to generate signals
- **Multi-Strategy Consensus**: Combines signals from multiple strategies
- **Weighted Scoring**: Considers historical performance and signal confidence
- **Risk Assessment**: Provides risk levels based on signal strength and consensus
- **Detailed Strategy Breakdown**: Shows individual strategy contributions

## Endpoints

### GET /recommendation

Get current trading recommendation based on real-time signals.

**URL**: `http://localhost:8000/recommendation`

**Method**: `GET`

**Headers**:
```
Content-Type: application/json
```

**Response**: `RecommendationResponse`

## Response Formats

### RecommendationResponse

```json
{
  "action": "BUY|SELL|HOLD",
  "confidence": 0.85,
  "entry_range": {
    "min": 45000.0,
    "max": 45100.0
  },
  "stop_loss": 44100.0,
  "take_profit": 46920.0,
  "current_price": 45050.0,
  "primary_strategy": "EMA_RSI",
  "supporting_strategies": ["Momentum", "Breakout"],
  "strategy_details": [
    {
      "strategy_name": "EMA_RSI",
      "signal": 1,
      "strength": 1.0,
      "confidence": 0.9,
      "reason": "EMA Crossover BUY: Fast EMA (45020.50) > Slow EMA (44800.30), RSI (65.2) > 30",
      "score": 0.8,
      "timeframe": "1h",
      "weight": 0.72
    },
    {
      "strategy_name": "Momentum",
      "signal": 1,
      "strength": 0.8,
      "confidence": 0.7,
      "reason": "Momentum BUY: MACD (125.4) > Signal (98.2), RSI (62.1) > 50",
      "score": 0.6,
      "timeframe": "4h",
      "weight": 0.42
    }
  ],
  "signal_consensus": 0.75,
  "risk_level": "MEDIUM",
  "risk_reward_ratio": 1.25,
  "entry_label": "Entrada favorable - Precio en la parte baja del rango",
  "risk_percentage": 2.0,
  "normalized_weights_sum": 1.0,
  "position_size_usd": 1200.0,
  "position_size_pct": 0.12
}
```

### Field Descriptions

#### Core Recommendation Fields

| Field | Type | Description |
|-------|------|-------------|
| `action` | string | Primary trading action: "BUY", "SELL", or "HOLD" |
| `confidence` | float | Overall confidence level (0.0 to 1.0) |
| `entry_range` | object | Suggested entry price range |
| `stop_loss` | float | Recommended stop loss price |
| `take_profit` | float | Recommended take profit price |
| `current_price` | float | Current market price |

#### Strategy Analysis Fields

| Field | Type | Description |
|-------|------|-------------|
| `primary_strategy` | string | Main strategy driving the recommendation |
| `supporting_strategies` | array | List of strategies supporting the primary signal |
| `strategy_details` | array | Detailed analysis of all strategies |
| `signal_consensus` | float | Percentage of strategies agreeing (0.0 to 1.0) |
| `risk_level` | string | Risk assessment: "LOW", "MEDIUM", or "HIGH" |
| `risk_reward_ratio` | float | Risk to reward ratio of proposed levels |
| `entry_label` | string | Human-readable entry guidance |
| `risk_percentage` | float | Percent of price at risk to stop loss |
| `normalized_weights_sum` | float | Sum of normalized weights (should be 1.0) |
| `position_size_usd` | float | Suggested notional exposure in USD (or quote currency) |
| `position_size_pct` | float | Fraction of capital allocated (0.0 to ~1.0) |

#### Strategy Detail Fields

| Field | Type | Description |
|-------|------|-------------|
| `strategy_name` | string | Name of the strategy |
| `signal` | integer | Signal value: -1 (sell), 0 (hold), 1 (buy) |
| `strength` | float | Signal strength (0.0 to 1.0) |
| `confidence` | float | Strategy confidence in the signal (0.0 to 1.0) |
| `reason` | string | Human-readable explanation of the signal |
| `score` | float | Historical performance score (0.0 to 1.0) |
| `timeframe` | string | Timeframe used for analysis |
| `weight` | float | Combined weight (confidence × score) |

## Strategy Details

### Signal Generation

Each strategy generates signals based on:

1. **Technical Indicators**: RSI, MACD, EMA, Bollinger Bands, etc.
2. **Price Action**: Breakouts, reversals, trend following
3. **Market Conditions**: Volatility, momentum, mean reversion

### Signal Strength Calculation

Signal strength is calculated as:
- **1.0**: Strong buy/sell signal
- **0.5**: Moderate signal
- **0.0**: No signal (hold)

### Confidence Calculation

Confidence is based on:
- **Signal Consistency**: How consistent recent signals are
- **Indicator Alignment**: Multiple indicators agreeing
- **Market Conditions**: Favorable trading conditions

### Weight Calculation

Strategy weight combines:
- **Confidence**: How sure the strategy is
- **Historical Score**: Past performance rating
- **Formula**: `weight = confidence × score`

## Error Handling

### Common Error Responses

#### 404 Not Found
```json
{
  "detail": "No results available. Please call /refresh first."
}
```

#### 500 Internal Server Error
```json
{
  "detail": "Error generating recommendation: [error message]"
}
```

### Error Scenarios

1. **No Data Available**: Call `/refresh` first to load market data
2. **Strategy Errors**: Individual strategy failures don't stop the process
3. **Data Loading Issues**: Missing or corrupted market data
4. **Service Unavailable**: Backend services not running

## Examples

### Example 1: Strong Buy Signal

**Request**:
```bash
curl -X GET "http://localhost:8000/recommendation"
```

**Response**:
```json
{
  "action": "BUY",
  "confidence": 0.92,
  "entry_range": {
    "min": 45000.0,
    "max": 45100.0
  },
  "stop_loss": 44100.0,
  "take_profit": 46920.0,
  "current_price": 45050.0,
  "primary_strategy": "EMA_RSI",
  "supporting_strategies": ["Momentum", "Breakout", "Ichimoku_ADX"],
  "strategy_details": [
    {
      "strategy_name": "EMA_RSI",
      "signal": 1,
      "strength": 1.0,
      "confidence": 0.95,
      "reason": "EMA Crossover BUY: Fast EMA (45020.50) > Slow EMA (44800.30), RSI (65.2) > 30",
      "score": 0.85,
      "timeframe": "1h",
      "weight": 0.81
    },
    {
      "strategy_name": "Momentum",
      "signal": 1,
      "strength": 0.9,
      "confidence": 0.88,
      "reason": "Momentum BUY: MACD (125.4) > Signal (98.2), RSI (62.1) > 50",
      "score": 0.78,
      "timeframe": "4h",
      "weight": 0.69
    }
  ],
  "signal_consensus": 0.85,
  "risk_level": "HIGH"
}
```

### Example 2: Hold Signal

**Response**:
```json
{
  "action": "HOLD",
  "confidence": 0.35,
  "entry_range": {
    "min": 45000.0,
    "max": 45100.0
  },
  "stop_loss": 44100.0,
  "take_profit": 46920.0,
  "current_price": 45050.0,
  "primary_strategy": "None",
  "supporting_strategies": [],
  "strategy_details": [
    {
      "strategy_name": "EMA_RSI",
      "signal": 0,
      "strength": 0.0,
      "confidence": 0.0,
      "reason": "Waiting: Fast EMA (45020.50) vs Slow EMA (45015.30), RSI (52.1)",
      "score": 0.85,
      "timeframe": "1h",
      "weight": 0.0
    }
  ],
  "signal_consensus": 0.6,
  "risk_level": "LOW"
}
```

### Example 3: Mixed Signals

**Response**:
```json
{
  "action": "BUY",
  "confidence": 0.65,
  "entry_range": {
    "min": 45000.0,
    "max": 45100.0
  },
  "stop_loss": 44100.0,
  "take_profit": 46920.0,
  "current_price": 45050.0,
  "primary_strategy": "EMA_RSI",
  "supporting_strategies": ["Momentum"],
  "strategy_details": [
    {
      "strategy_name": "EMA_RSI",
      "signal": 1,
      "strength": 0.8,
      "confidence": 0.7,
      "reason": "EMA Crossover BUY: Fast EMA (45020.50) > Slow EMA (44800.30), RSI (65.2) > 30",
      "score": 0.85,
      "timeframe": "1h",
      "weight": 0.60
    },
    {
      "strategy_name": "Momentum",
      "signal": 1,
      "strength": 0.6,
      "confidence": 0.5,
      "reason": "Momentum BUY: MACD (125.4) > Signal (98.2), RSI (62.1) > 50",
      "score": 0.78,
      "timeframe": "4h",
      "weight": 0.39
    },
    {
      "strategy_name": "Breakout",
      "signal": -1,
      "strength": 0.4,
      "confidence": 0.3,
      "reason": "Breakout SELL: Price (45050.0) < Lower Band (45100.0), ATR: 150.0",
      "score": 0.72,
      "timeframe": "1h",
      "weight": 0.22
    }
  ],
  "signal_consensus": 0.6,
  "risk_level": "MEDIUM"
}
```

## Usage Guidelines

### Interpreting Recommendations

1. **High Confidence + High Consensus**: Strong signal, consider taking action
2. **Medium Confidence + Medium Consensus**: Moderate signal, use with caution
3. **Low Confidence or Low Consensus**: Weak signal, consider waiting

### Risk Management

- **HIGH Risk**: Strong signals with multiple supporting strategies
- **MEDIUM Risk**: Moderate signals with some supporting strategies
- **LOW Risk**: Weak signals or mixed consensus

### Strategy Weights

- **Weight > 0.7**: Very reliable strategy signal
- **Weight 0.4-0.7**: Moderately reliable strategy signal
- **Weight < 0.4**: Less reliable strategy signal

## Integration Examples

### Python Integration

```python
import requests

def get_recommendation():
    response = requests.get("http://localhost:8000/recommendation")
    if response.status_code == 200:
        data = response.json()
        return {
            "action": data["action"],
            "confidence": data["confidence"],
            "risk_level": data["risk_level"],
            "primary_strategy": data["primary_strategy"]
        }
    else:
        return {"error": response.json()["detail"]}

# Usage
recommendation = get_recommendation()
print(f"Action: {recommendation['action']}")
print(f"Confidence: {recommendation['confidence']:.2%}")
print(f"Risk: {recommendation['risk_level']}")
```

### JavaScript Integration

```javascript
async function getRecommendation() {
    try {
        const response = await fetch('http://localhost:8000/recommendation');
        const data = await response.json();
        
        return {
            action: data.action,
            confidence: data.confidence,
            riskLevel: data.risk_level,
            primaryStrategy: data.primary_strategy
        };
    } catch (error) {
        console.error('Error fetching recommendation:', error);
        return { error: error.message };
    }
}

// Usage
getRecommendation().then(recommendation => {
    console.log(`Action: ${recommendation.action}`);
    console.log(`Confidence: ${(recommendation.confidence * 100).toFixed(1)}%`);
    console.log(`Risk: ${recommendation.riskLevel}`);
});
```

## Conclusion

The recommendation API provides comprehensive real-time trading analysis with detailed strategy breakdowns. Use the confidence levels, risk assessments, and strategy weights to make informed trading decisions while managing risk appropriately.

### Current Limitations

- Aggregate confidence may exceed the weakest active signal in highly unbalanced cases; normalization updates are in progress to cap by active mean and minimum.
- Some strategies are under calibration; thresholds may change between minor versions until QA is complete (see `docs/qa/status.md`).
