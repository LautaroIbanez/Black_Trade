import React, { useState, useEffect } from 'react';
import './TradeSummary.css';

// Types
interface TradeManagement {
  entry_price: number;
  stop_loss: number;
  take_profit: number;
  current_price: number;
  unrealized_pnl: number;
  risk_reward_ratio: number;
  max_risk_pct: number;
  potential_reward_pct: number;
  strategy_name: string;
  signal_strength: number;
  confidence: number;
  timeframe: string;
  status: 'OPEN' | 'HIT_SL' | 'HIT_TP' | 'MANUAL_CLOSE';
  entry_time: string;
  last_updated: string;
}

interface RecommendationData {
  action: string;
  confidence: number;
  entry_range: { min: number; max: number };
  stop_loss: number;
  take_profit: number;
  current_price: number;
  primary_strategy: string;
  risk_level: string;
  trade_management?: TradeManagement;
}

interface TradeSummaryProps {
  recommendation?: RecommendationData;
  className?: string;
}

const TradeSummary: React.FC<TradeSummaryProps> = ({ recommendation, className = '' }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  if (!recommendation || !recommendation.trade_management) {
    return (
      <div className={`trade-summary trade-summary--no-trade ${className}`}>
        <div className="trade-summary__header">
          <h3>Active Trades</h3>
          <span className="trade-summary__status trade-summary__status--none">No Active Trades</span>
        </div>
        <p className="trade-summary__message">
          No active trades. Monitor recommendations for new entry opportunities.
        </p>
      </div>
    );
  }

  const trade = recommendation.trade_management;
  const isLong = trade.entry_price < trade.current_price;
  const pnlColor = trade.unrealized_pnl >= 0 ? 'positive' : 'negative';
  const statusColor = trade.status === 'OPEN' ? 'open' : 'closed';

  // Calculate distance to stop loss and take profit
  const distanceToSL = isLong 
    ? ((trade.current_price - trade.stop_loss) / trade.current_price * 100)
    : ((trade.stop_loss - trade.current_price) / trade.current_price * 100);
  
  const distanceToTP = isLong
    ? ((trade.take_profit - trade.current_price) / trade.current_price * 100)
    : ((trade.current_price - trade.take_profit) / trade.current_price * 100);

  return (
    <div className={`trade-summary ${className}`}>
      <div className="trade-summary__header">
        <h3>Active Trade</h3>
        <div className="trade-summary__controls">
          <span className={`trade-summary__status trade-summary__status--${statusColor}`}>
            {trade.status}
          </span>
          <button 
            className="trade-summary__toggle"
            onClick={() => setIsExpanded(!isExpanded)}
            aria-label={isExpanded ? 'Collapse details' : 'Expand details'}
          >
            {isExpanded ? '−' : '+'}
          </button>
        </div>
      </div>

      <div className="trade-summary__overview">
        <div className="trade-summary__row">
          <div className="trade-summary__item">
            <span className="trade-summary__label">Strategy:</span>
            <span className="trade-summary__value">{trade.strategy_name}</span>
          </div>
          <div className="trade-summary__item">
            <span className="trade-summary__label">Timeframe:</span>
            <span className="trade-summary__value">{trade.timeframe}</span>
          </div>
        </div>

        <div className="trade-summary__row">
          <div className="trade-summary__item">
            <span className="trade-summary__label">Entry Price:</span>
            <span className="trade-summary__value">${trade.entry_price.toFixed(2)}</span>
          </div>
          <div className="trade-summary__item">
            <span className="trade-summary__label">Current Price:</span>
            <span className="trade-summary__value">${trade.current_price.toFixed(2)}</span>
          </div>
        </div>

        <div className="trade-summary__row">
          <div className="trade-summary__item">
            <span className="trade-summary__label">Unrealized P&L:</span>
            <span className={`trade-summary__value trade-summary__pnl--${pnlColor}`}>
              ${trade.unrealized_pnl.toFixed(2)}
            </span>
          </div>
          <div className="trade-summary__item">
            <span className="trade-summary__label">Confidence:</span>
            <span className="trade-summary__value">{(trade.confidence * 100).toFixed(1)}%</span>
          </div>
        </div>
      </div>

      {isExpanded && (
        <div className="trade-summary__details">
          <div className="trade-summary__section">
            <h4>Exit Levels</h4>
            <div className="trade-summary__exit-levels">
              <div className="trade-summary__level">
                <span className="trade-summary__level-label">Stop Loss:</span>
                <span className="trade-summary__level-value">${trade.stop_loss.toFixed(2)}</span>
                <span className="trade-summary__level-distance">
                  {distanceToSL.toFixed(1)}% away
                </span>
              </div>
              <div className="trade-summary__level">
                <span className="trade-summary__level-label">Take Profit:</span>
                <span className="trade-summary__level-value">${trade.take_profit.toFixed(2)}</span>
                <span className="trade-summary__level-distance">
                  {distanceToTP.toFixed(1)}% away
                </span>
              </div>
            </div>
          </div>

          <div className="trade-summary__section">
            <h4>Risk Management</h4>
            <div className="trade-summary__risk-metrics">
              <div className="trade-summary__metric">
                <span className="trade-summary__metric-label">Risk/Reward Ratio:</span>
                <span className="trade-summary__metric-value">{trade.risk_reward_ratio.toFixed(2)}</span>
              </div>
              <div className="trade-summary__metric">
                <span className="trade-summary__metric-label">Max Risk:</span>
                <span className="trade-summary__metric-value">{trade.max_risk_pct.toFixed(1)}%</span>
              </div>
              <div className="trade-summary__metric">
                <span className="trade-summary__metric-label">Potential Reward:</span>
                <span className="trade-summary__metric-value">{trade.potential_reward_pct.toFixed(1)}%</span>
              </div>
            </div>
          </div>

          <div className="trade-summary__section">
            <h4>Trade Details</h4>
            <div className="trade-summary__trade-info">
              <div className="trade-summary__info-item">
                <span className="trade-summary__info-label">Entry Time:</span>
                <span className="trade-summary__info-value">
                  {new Date(trade.entry_time).toLocaleString()}
                </span>
              </div>
              <div className="trade-summary__info-item">
                <span className="trade-summary__info-label">Last Updated:</span>
                <span className="trade-summary__info-value">
                  {new Date(trade.last_updated).toLocaleString()}
                </span>
              </div>
              <div className="trade-summary__info-item">
                <span className="trade-summary__info-label">Signal Strength:</span>
                <span className="trade-summary__info-value">{(trade.signal_strength * 100).toFixed(1)}%</span>
              </div>
            </div>
          </div>

          <div className="trade-summary__section">
            <h4>Price Levels Visualization</h4>
            <div className="trade-summary__price-chart">
              <div className="trade-summary__price-bar">
                <div className="trade-summary__price-level trade-summary__price-level--sl">
                  <span className="trade-summary__price-label">SL</span>
                  <span className="trade-summary__price-value">${trade.stop_loss.toFixed(2)}</span>
                </div>
                <div className="trade-summary__price-level trade-summary__price-level--entry">
                  <span className="trade-summary__price-label">Entry</span>
                  <span className="trade-summary__price-value">${trade.entry_price.toFixed(2)}</span>
                </div>
                <div className="trade-summary__price-level trade-summary__price-level--current">
                  <span className="trade-summary__price-label">Current</span>
                  <span className="trade-summary__price-value">${trade.current_price.toFixed(2)}</span>
                </div>
                <div className="trade-summary__price-level trade-summary__price-level--tp">
                  <span className="trade-summary__price-label">TP</span>
                  <span className="trade-summary__price-value">${trade.take_profit.toFixed(2)}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default TradeSummary;
