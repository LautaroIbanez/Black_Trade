import React, { useState, useEffect } from 'react'
import { getStrategies } from '../services/api'
import './Strategies.css'

function Strategies() {
  const [strategiesData, setStrategiesData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [selectedTimeframe, setSelectedTimeframe] = useState(null)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await getStrategies()
      setStrategiesData(data)
      if (!selectedTimeframe && data.timeframes) {
        setSelectedTimeframe(Object.keys(data.timeframes)[0])
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  if (error) {
    return (
      <div className="error-container">
        <p className="error-message">{error}</p>
        <button onClick={loadData} className="retry-btn">
          Retry
        </button>
      </div>
    )
  }

  if (!strategiesData || !selectedTimeframe) {
    return <div className="loading">Loading strategies...</div>
  }

  const strategies = strategiesData.timeframes[selectedTimeframe] || []

  return (
    <div className="strategies">
      <h2>Strategy Performance</h2>

      <div className="timeframe-selector">
        {Object.keys(strategiesData.timeframes).map(tf => (
          <button
            key={tf}
            className={selectedTimeframe === tf ? 'active' : ''}
            onClick={() => setSelectedTimeframe(tf)}
          >
            {tf.toUpperCase()}
          </button>
        ))}
      </div>

      <div className="strategies-table-container">
        <table className="strategies-table">
          <thead>
            <tr>
              <th>Strategy</th>
              <th>Score</th>
              <th>Win Rate</th>
              <th>Total Trades</th>
              <th>Net PnL</th>
              <th>Max Drawdown</th>
              <th>Profit Factor</th>
              <th>Expectancy</th>
            </tr>
          </thead>
          <tbody>
            {strategies.map((strategy, index) => (
              <tr key={index} className={index === 0 ? 'top-strategy' : ''}>
                <td className="strategy-name">
                  {strategy.strategy_name}
                  {index === 0 && <span className="badge-top">TOP</span>}
                </td>
                <td className="score-cell">
                  <div className="score-bar">
                    <div 
                      className="score-fill" 
                      style={{ width: `${Math.min(strategy.score * 100, 100)}%` }}
                    />
                    <span>{strategy.score.toFixed(3)}</span>
                  </div>
                </td>
                <td>{(strategy.win_rate * 100).toFixed(1)}%</td>
                <td>{strategy.total_trades}</td>
                <td className={strategy.net_pnl >= 0 ? 'positive' : 'negative'}>
                  {strategy.net_pnl >= 0 ? '+' : ''}{strategy.net_pnl.toFixed(2)}
                </td>
                <td>{strategy.max_drawdown.toFixed(2)}</td>
                <td>{strategy.profit_factor.toFixed(2)}</td>
                <td>{strategy.expectancy.toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {strategiesData.summary && (
        <div className="summary">
          <h3>Summary</h3>
          <div className="summary-grid">
            {Object.entries(strategiesData.summary).map(([tf, data]) => (
              <div key={tf} className="summary-card">
                <span className="summary-label">{tf.toUpperCase()}</span>
                <span className="summary-value">{data.top_strategy}</span>
                <span className="summary-score">Score: {data.top_score.toFixed(3)}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default Strategies


