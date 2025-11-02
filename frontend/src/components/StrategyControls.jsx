import React, { useState } from 'react'
import { toggleStrategy } from '../services/api'
import './StrategyControls.css'

function StrategyControls({ strategies, token, onUpdate }) {
  const [loading, setLoading] = useState({})

  const handleToggle = async (strategyName, currentEnabled) => {
    const newEnabled = !currentEnabled
    
    if (!confirm(`¿Está seguro de que desea ${newEnabled ? 'activar' : 'pausar'} la estrategia ${strategyName}?`)) {
      return
    }

    setLoading({ ...loading, [strategyName]: true })

    try {
      await toggleStrategy(strategyName, newEnabled, token)
      if (onUpdate) {
        onUpdate()
      }
    } catch (error) {
      alert('Error al actualizar estrategia: ' + error.message)
    } finally {
      setLoading({ ...loading, [strategyName]: false })
    }
  }

  const getPerformanceColor = (pnl) => {
    if (pnl > 0) return 'positive'
    if (pnl < 0) return 'negative'
    return 'neutral'
  }

  return (
    <div className="strategy-controls">
      <div className="controls-header">
        <h3>Estrategias</h3>
        <button onClick={onUpdate} className="refresh-btn">🔄</button>
      </div>

      <div className="strategies-list">
        {strategies.map((strategy) => (
          <div key={strategy.name} className="strategy-item">
            <div className="strategy-info">
              <div className="strategy-name-row">
                <span className="strategy-name">{strategy.name}</span>
                <div className={`strategy-toggle ${strategy.enabled ? 'enabled' : 'disabled'}`}>
                  <button
                    className={`toggle-btn ${strategy.enabled ? 'on' : 'off'}`}
                    onClick={() => handleToggle(strategy.name, strategy.enabled)}
                    disabled={loading[strategy.name]}
                  >
                    {loading[strategy.name] ? '...' : strategy.enabled ? 'ON' : 'OFF'}
                  </button>
                </div>
              </div>

              {strategy.metrics && (
                <div className="strategy-metrics">
                  {strategy.metrics.pnl !== undefined && (
                    <div className={`metric ${getPerformanceColor(strategy.metrics.pnl)}`}>
                      <span className="metric-label">P&L:</span>
                      <span className="metric-value">
                        ${strategy.metrics.pnl.toLocaleString()}
                      </span>
                    </div>
                  )}
                  {strategy.metrics.win_rate !== undefined && (
                    <div className="metric">
                      <span className="metric-label">Win Rate:</span>
                      <span className="metric-value">
                        {(strategy.metrics.win_rate * 100).toFixed(1)}%
                      </span>
                    </div>
                  )}
                  {strategy.metrics.trades !== undefined && (
                    <div className="metric">
                      <span className="metric-label">Trades:</span>
                      <span className="metric-value">{strategy.metrics.trades}</span>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default StrategyControls

