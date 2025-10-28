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

  const handleRefresh = async () => {
    setLoading(true)
    setError(null)
    try {
      await refreshData()
      const data = await getRecommendation()
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


