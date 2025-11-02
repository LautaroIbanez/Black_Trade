import React from 'react'
import './RiskOverview.css'

function RiskOverview({ riskData }) {
  const getRiskLevel = (value, limit) => {
    const percentage = (value / limit) * 100
    if (percentage >= 90) return 'critical'
    if (percentage >= 70) return 'warning'
    return 'safe'
  }

  const formatPercentage = (value) => {
    return `${value.toFixed(2)}%`
  }

  const formatCurrency = (value) => {
    return `$${Math.abs(value).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
  }

  const drawdownLevel = riskData?.metrics?.current_drawdown_pct && riskData?.risk_limits?.max_drawdown_pct
    ? getRiskLevel(riskData.metrics.current_drawdown_pct, riskData.risk_limits.max_drawdown_pct)
    : 'safe'

  const exposureLevel = riskData?.metrics?.exposure_pct && riskData?.risk_limits?.max_exposure_pct
    ? getRiskLevel(riskData.metrics.exposure_pct, riskData.risk_limits.max_exposure_pct)
    : 'safe'

  return (
    <div className="risk-overview">
      <h3 className="risk-title">Riesgo Actual</h3>
      
      <div className="risk-metrics">
        <div className="risk-metric">
          <div className="metric-header">
            <span className="metric-label">Drawdown</span>
            <span className={`metric-status ${drawdownLevel}`}>
              {riskData?.metrics?.current_drawdown_pct !== undefined 
                ? formatPercentage(riskData.metrics.current_drawdown_pct)
                : 'N/A'}
            </span>
          </div>
          <div className="progress-container">
            <div 
              className={`progress-bar ${drawdownLevel}`}
              style={{ 
                width: riskData?.metrics?.current_drawdown_pct && riskData?.risk_limits?.max_drawdown_pct
                  ? `${Math.min((riskData.metrics.current_drawdown_pct / riskData.risk_limits.max_drawdown_pct) * 100, 100)}%`
                  : '0%'
              }}
            ></div>
          </div>
          <div className="metric-limit">
            Límite: {riskData?.risk_limits?.max_drawdown_pct 
              ? formatPercentage(riskData.risk_limits.max_drawdown_pct)
              : 'N/A'}
          </div>
        </div>

        <div className="risk-metric">
          <div className="metric-header">
            <span className="metric-label">Exposición</span>
            <span className={`metric-status ${exposureLevel}`}>
              {riskData?.metrics?.exposure_pct !== undefined
                ? formatPercentage(riskData.metrics.exposure_pct)
                : 'N/A'}
            </span>
          </div>
          <div className="progress-container">
            <div 
              className={`progress-bar ${exposureLevel}`}
              style={{ 
                width: riskData?.metrics?.exposure_pct && riskData?.risk_limits?.max_exposure_pct
                  ? `${Math.min((riskData.metrics.exposure_pct / riskData.risk_limits.max_exposure_pct) * 100, 100)}%`
                  : '0%'
              }}
            ></div>
          </div>
          <div className="metric-limit">
            Límite: {riskData?.risk_limits?.max_exposure_pct
              ? formatPercentage(riskData.risk_limits.max_exposure_pct)
              : 'N/A'}
          </div>
        </div>

        <div className="risk-metric">
          <div className="metric-header">
            <span className="metric-label">Daily P&L</span>
            <span className={`metric-value ${riskData?.metrics?.daily_pnl >= 0 ? 'positive' : 'negative'}`}>
              {riskData?.metrics?.daily_pnl !== undefined
                ? formatCurrency(riskData.metrics.daily_pnl)
                : 'N/A'}
            </span>
          </div>
          {riskData?.risk_limits?.daily_loss_limit_pct && (
            <div className="metric-limit">
              Límite: {formatPercentage(riskData.risk_limits.daily_loss_limit_pct)}
            </div>
          )}
        </div>

        {riskData?.metrics?.var_1d_95 !== undefined && (
          <div className="risk-metric">
            <div className="metric-header">
              <span className="metric-label">VaR (1d 95%)</span>
              <span className="metric-value">
                {formatCurrency(riskData.metrics.var_1d_95)}
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default RiskOverview

