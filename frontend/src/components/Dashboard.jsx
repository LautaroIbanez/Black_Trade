import React, { useState, useEffect } from 'react'
import { getRecommendation, refreshData } from '../services/api'
import './Dashboard.css'

function Dashboard() {
  const [recommendation, setRecommendation] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

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
        <h2>BTC/USDT Trading Recommendation</h2>
        <button onClick={handleRefresh} className="refresh-btn" disabled={loading}>
          {loading ? 'Refreshing...' : 'Refresh'}
        </button>
      </div>

      {recommendation && (
        <>
          <div className="price-display">
            <span className="price-label">Current Price</span>
            <span className="price-value">${recommendation.current_price.toFixed(2)}</span>
          </div>

          <div className="recommendation-card">
            <div className="recommendation-header">
              <h3>Recommendation</h3>
              <span className={`confidence-badge ${recommendation.confidence > 0.7 ? 'high' : recommendation.confidence > 0.4 ? 'medium' : 'low'}`}>
                {Math.round(recommendation.confidence * 100)}% Confidence
              </span>
            </div>
            
            <div className="action-section">
              <div className={`action-badge ${recommendation.action.toLowerCase()}`}>
                {recommendation.action}
              </div>
              <p className="action-description">
                {recommendation.action === 'LONG' && 'Suggested entry for buying position'}
                {recommendation.action === 'SHORT' && 'Suggested entry for selling position'}
                {recommendation.action === 'FLAT' && 'No clear direction, stay neutral'}
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
          </div>

          <div className="risk-info">
            <p>⚠️ This is not financial advice. Always do your own research and trade responsibly.</p>
          </div>
        </>
      )}
    </div>
  )
}

export default Dashboard


