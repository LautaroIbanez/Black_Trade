import React, { useState, useEffect, useCallback } from 'react'
import { getRecommendation, refreshData } from '../services/api'
import SignalChart from './SignalChart'
import TradeSummary from './TradeSummary'
import './Dashboard.css'

function Dashboard() {
  const [recommendation, setRecommendation] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [chartData, setChartData] = useState(null)
  const [selectedTimeframe, setSelectedTimeframe] = useState('1h')
  const [chartLoading, setChartLoading] = useState(false)
  const [tradingProfile, setTradingProfile] = useState('balanced')
  const [showBreakdown, setShowBreakdown] = useState(false)

  const handleRefresh = async () => {
    setLoading(true)
    setError(null)
    try {
      await refreshData()
      const data = await getRecommendation(tradingProfile)
      setRecommendation(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleProfileChange = async (profile) => {
    setTradingProfile(profile)
    setLoading(true)
    setError(null)
    try {
      const data = await getRecommendation(profile)
      setRecommendation(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  // Memorized callbacks to prevent unnecessary re-renders
  const handleChartDataLoad = useCallback((data) => {
    setChartData(data)
    setChartLoading(false)
  }, [])

  const handleChartError = useCallback((error) => {
    console.error('Chart error:', error)
    setChartLoading(false)
  }, [])

  const handleTimeframeChange = useCallback((timeframe) => {
    setSelectedTimeframe(timeframe)
    setChartLoading(true)
  }, [])

  useEffect(() => {
    handleRefresh()
  }, [])

  if (error) {
    return (
      <div className="error-container">
        <p className="error-message">{error}</p>
        <button onClick={handleRefresh} className="refresh-btn">
          Retry
        </button>
      </div>
    )
  }

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <h2>BTC/USDT Trading Dashboard</h2>
        <button onClick={handleRefresh} className="refresh-btn" disabled={loading}>
          {loading ? 'Refreshing...' : 'Refresh'}
        </button>
      </div>

      {/* Trading Profile Selector */}
      <div className="profile-selector">
        <h3>Trading Profile</h3>
        <div className="profile-buttons">
          {[
            { id: 'day_trading', label: 'Day Trading', description: 'Focus on 1h-4h signals' },
            { id: 'swing', label: 'Swing Trading', description: 'Focus on 4h-1d signals' },
            { id: 'balanced', label: 'Balanced', description: 'Equal weight all timeframes' },
            { id: 'long_term', label: 'Long Term', description: 'Focus on 1d-1w signals' }
          ].map(profile => (
            <button
              key={profile.id}
              className={`profile-btn ${tradingProfile === profile.id ? 'active' : ''}`}
              onClick={() => handleProfileChange(profile.id)}
              disabled={loading}
              title={profile.description}
            >
              {profile.label}
            </button>
          ))}
        </div>
        <p className="profile-description">
          {tradingProfile === 'day_trading' && 'Optimized for intraday trading with emphasis on short-term signals'}
          {tradingProfile === 'swing' && 'Balanced approach for swing trades with medium-term focus'}
          {tradingProfile === 'balanced' && 'Equal consideration of all timeframes for general trading'}
          {tradingProfile === 'long_term' && 'Long-term perspective with emphasis on higher timeframes'}
        </p>
      </div>

      {/* Timeframe Selector */}
      <div className="timeframe-selector">
        <h3>Select Timeframe</h3>
        <div className="timeframe-buttons">
          {['1h', '4h', '1d', '1w'].map(timeframe => (
            <button
              key={timeframe}
              className={`timeframe-btn ${selectedTimeframe === timeframe ? 'active' : ''}`}
              onClick={() => handleTimeframeChange(timeframe)}
              disabled={chartLoading}
            >
              {timeframe}
            </button>
          ))}
        </div>
      </div>

      {/* Chart Section */}
      <div className="chart-section">
        <SignalChart
          symbol="BTCUSDT"
          timeframe={selectedTimeframe}
          limit={200}
          showSignals={true}
          showRecommendation={true}
          onDataLoad={handleChartDataLoad}
          onError={handleChartError}
          className="dashboard-chart"
        />
      </div>

      {/* Trade Summary Section */}
      {recommendation && (
        <TradeSummary 
          recommendation={recommendation}
          className="dashboard-trade-summary"
        />
      )}

      {/* Recommendation Section */}
      {recommendation && (
        <div className="recommendation-section">
          <div className="price-display">
            <span className="price-label">Current Price</span>
            <span className="price-value">${recommendation.current_price.toFixed(2)}</span>
          </div>

          <div className="recommendation-card">
            <div className="recommendation-header">
              <h3>Current Recommendation</h3>
              <span className={`confidence-badge ${recommendation.confidence > 0.7 ? 'high' : recommendation.confidence > 0.4 ? 'medium' : 'low'}`}>
                {Math.round(recommendation.confidence * 100)}% Confidence
              </span>
            </div>
            
            <div className="action-section">
              <div className={`action-badge ${recommendation.action.toLowerCase()}`}>
                {recommendation.action}
              </div>
              <p className="action-description">
                {recommendation.action === 'BUY' && 'Suggested entry for buying position'}
                {recommendation.action === 'SELL' && 'Suggested entry for selling position'}
                {recommendation.action === 'HOLD' && 'No clear direction, stay neutral'}
              </p>
            </div>

            <div className="levels-grid">
              <div className="level-card">
                <span className="level-label">Entry Range</span>
                <span className="level-value">${recommendation.entry_range.min.toFixed(2)} - ${recommendation.entry_range.max.toFixed(2)}</span>
              </div>
              <div className="level-card">
                <span className="level-label">Stop Loss</span>
                <span className="level-value stop-loss">${recommendation.stop_loss.toFixed(2)}</span>
              </div>
              <div className="level-card">
                <span className="level-label">Take Profit</span>
                <span className="level-value take-profit">${recommendation.take_profit.toFixed(2)}</span>
              </div>
            </div>

            {recommendation.primary_strategy && (
              <div className="strategy-info">
                <span className="strategy-label">Primary Strategy:</span>
                <span className="strategy-name">{recommendation.primary_strategy}</span>
              </div>
            )}

            {recommendation.risk_level && (
              <div className="risk-level">
                <span className="risk-label">Risk Level:</span>
                <span className={`risk-badge risk-${recommendation.risk_level.toLowerCase()}`}>
                  {recommendation.risk_level}
                </span>
              </div>
            )}

            {/* Multi-timeframe Consensus Summary */}
            {recommendation.strategy_details && recommendation.strategy_details.length > 0 && (() => {
              // Group strategies by timeframe
              const timeframeGroups = {};
              recommendation.strategy_details.forEach(strategy => {
                const tf = strategy.timeframe;
                if (!timeframeGroups[tf]) {
                  timeframeGroups[tf] = [];
                }
                timeframeGroups[tf].push(strategy);
              });

              return (
                <div className="consensus-summary">
                  <div className="consensus-header">
                    <h4>Multi-Timeframe Consensus</h4>
                    <span className="consensus-tooltip" title="This recommendation combines signals from multiple timeframes and strategies, weighted by their historical performance and current strength.">
                      ℹ️
                    </span>
                  </div>
                  
                  <div className="timeframe-participants">
                    {Object.entries(timeframeGroups).map(([timeframe, strategies]) => (
                      <div key={timeframe} className="timeframe-group">
                        <div className="timeframe-label">
                          {timeframe}
                          <span className="strategy-count">({strategies.length} strategies)</span>
                        </div>
                        <div className="strategy-list">
                          {strategies.slice(0, 3).map((strategy, idx) => (
                            <span 
                              key={idx} 
                              className={`strategy-tag ${strategy.signal === 1 ? 'buy' : strategy.signal === -1 ? 'sell' : 'hold'}`}
                              title={`${strategy.strategy_name}: ${strategy.signal === 1 ? 'BUY' : strategy.signal === -1 ? 'SELL' : 'HOLD'} (${Math.round(strategy.confidence * 100)}% confidence, ${Math.round(strategy.score * 100)}% historical score)`}
                            >
                              {strategy.strategy_name}
                            </span>
                          ))}
                          {strategies.length > 3 && (
                            <span className="strategy-more">+{strategies.length - 3} more</span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>

                  <div className="consensus-explanation">
                    <small>
                      💡 Recommendation based on weighted consensus across {Object.keys(timeframeGroups).length} timeframes
                    </small>
                  </div>
                </div>
              );
            })()}

            {/* Contribution Breakdown Panel */}
            {recommendation.contribution_breakdown && recommendation.contribution_breakdown.length > 0 && (
              <div className="contribution-breakdown">
                <div className="breakdown-header">
                  <h4>Detailed Contribution Analysis</h4>
                  <button 
                    className="breakdown-toggle"
                    onClick={() => setShowBreakdown(!showBreakdown)}
                  >
                    {showBreakdown ? 'Hide Details' : 'Show Details'}
                  </button>
                </div>
                
                {showBreakdown && (
                  <div className="breakdown-content">
                    <div className="breakdown-description">
                      <p>This panel shows how each strategy contributed to the final recommendation, including entry range, stop loss, and take profit calculations.</p>
                    </div>
                    
                    <div className="breakdown-list">
                      {recommendation.contribution_breakdown.map((contribution, index) => (
                        <div key={index} className="contribution-item">
                          <div className="contribution-header">
                            <div className="strategy-info">
                              <span className="strategy-name">{contribution.strategy_name}</span>
                              <span className="timeframe-badge">{contribution.timeframe}</span>
                              <span className={`signal-badge ${contribution.signal === 1 ? 'buy' : contribution.signal === -1 ? 'sell' : 'hold'}`}>
                                {contribution.signal === 1 ? 'BUY' : contribution.signal === -1 ? 'SELL' : 'HOLD'}
                              </span>
                            </div>
                            <div className="weight-info">
                              <span className="weight-percentage">{contribution.weight.toFixed(1)}%</span>
                              <span className="weight-label">Weight</span>
                            </div>
                          </div>
                          
                          <div className="contribution-metrics">
                            <div className="metric-group">
                              <span className="metric-label">Confidence:</span>
                              <span className="metric-value">{(contribution.confidence * 100).toFixed(1)}%</span>
                            </div>
                            <div className="metric-group">
                              <span className="metric-label">Strength:</span>
                              <span className="metric-value">{(contribution.strength * 100).toFixed(1)}%</span>
                            </div>
                            <div className="metric-group">
                              <span className="metric-label">Historical Score:</span>
                              <span className="metric-value">{(contribution.score * 100).toFixed(1)}%</span>
                            </div>
                          </div>
                          
                          <div className="contribution-levels">
                            <div className="level-group">
                              <span className="level-label">Entry Range:</span>
                              <span className="level-value">
                                ${contribution.entry_contribution.min.toFixed(2)} - ${contribution.entry_contribution.max.toFixed(2)}
                              </span>
                            </div>
                            <div className="level-group">
                              <span className="level-label">Stop Loss:</span>
                              <span className="level-value">${contribution.sl_contribution.toFixed(2)}</span>
                            </div>
                            <div className="level-group">
                              <span className="level-label">Take Profit:</span>
                              <span className="level-value">${contribution.tp_contribution.toFixed(2)}</span>
                            </div>
                          </div>
                          
                          <div className="contribution-reason">
                            <span className="reason-label">Reason:</span>
                            <span className="reason-text">{contribution.reason}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          <div className="risk-info">
            <p>⚠️ This is not financial advice. Always do your own research and trade responsibly.</p>
          </div>
        </div>
      )}
    </div>
  )
}

export default Dashboard


