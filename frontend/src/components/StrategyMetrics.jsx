import React, { useState, useEffect } from 'react'
import { getStrategyMetrics, getStrategyPerformance } from '../services/api'
import './StrategyMetrics.css'

function StrategyMetrics({ strategyName, token }) {
  const [metrics, setMetrics] = useState(null)
  const [performance, setPerformance] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadMetrics()
  }, [strategyName])

  const loadMetrics = async () => {
    try {
      setLoading(true)
      const [metricsData, performanceData] = await Promise.all([
        getStrategyMetrics(strategyName, token),
        getStrategyPerformance(strategyName, token),
      ])
      setMetrics(metricsData)
      setPerformance(performanceData)
    } catch (error) {
      console.error('Error loading strategy metrics:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return <div className="strategy-metrics">Cargando métricas...</div>
  }

  if (!metrics) {
    return <div className="strategy-metrics">No hay métricas disponibles</div>
  }

  return (
    <div className="strategy-metrics">
      <h4>{strategyName} - Métricas Walk-Forward</h4>

      {metrics.latest_optimal_parameters && (
        <div className="optimal-parameters">
          <h5>Parámetros Óptimos</h5>
          <div className="parameters-list">
            {Object.entries(metrics.latest_optimal_parameters.parameters || {}).map(([key, value]) => (
              <div key={key} className="parameter-item">
                <span className="param-key">{key}:</span>
                <span className="param-value">{String(value)}</span>
              </div>
            ))}
          </div>
          {metrics.latest_optimal_parameters.validation_metrics && (
            <div className="validation-metrics">
              <div className="metric-item">
                <span className="metric-label">Sharpe Ratio:</span>
                <span className="metric-value">
                  {metrics.latest_optimal_parameters.validation_metrics.sharpe_ratio?.toFixed(2) || 'N/A'}
                </span>
              </div>
              <div className="metric-item">
                <span className="metric-label">Win Rate:</span>
                <span className="metric-value">
                  {(metrics.latest_optimal_parameters.validation_metrics.win_rate * 100)?.toFixed(1) || 'N/A'}%
                </span>
              </div>
            </div>
          )}
        </div>
      )}

      {performance && (
        <div className="performance-comparison">
          <h5>Performance IS vs OOS</h5>
          <div className="comparison-grid">
            <div className="comparison-col">
              <div className="comparison-header">In-Sample</div>
              <div className="comparison-metric">
                Sharpe: {performance.in_sample.avg_sharpe?.toFixed(2) || 'N/A'}
              </div>
              <div className="comparison-metric">
                Win Rate: {(performance.in_sample.avg_win_rate * 100)?.toFixed(1) || 'N/A'}%
              </div>
              <div className="comparison-metric">
                Results: {performance.in_sample.results_count || 0}
              </div>
            </div>
            <div className="comparison-col">
              <div className="comparison-header">Out-of-Sample</div>
              <div className="comparison-metric">
                Sharpe: {performance.out_of_sample.avg_sharpe?.toFixed(2) || 'N/A'}
              </div>
              <div className="comparison-metric">
                Win Rate: {(performance.out_of_sample.avg_win_rate * 100)?.toFixed(1) || 'N/A'}%
              </div>
              <div className="comparison-metric">
                Results: {performance.out_of_sample.results_count || 0}
              </div>
            </div>
            <div className="comparison-col">
              <div className="comparison-header">Consistencia</div>
              {performance.consistency.is_oos_sharpe_ratio && (
                <div className="comparison-metric">
                  IS/OOS Ratio: {performance.consistency.is_oos_sharpe_ratio.toFixed(2)}
                  {performance.consistency.is_oos_sharpe_ratio > 0.7 && (
                    <span className="consistency-good">✓</span>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {metrics.summary_metrics && Object.keys(metrics.summary_metrics).length > 0 && (
        <div className="summary-metrics">
          <h5>Métricas Promedio</h5>
          <div className="metrics-grid">
            {metrics.summary_metrics.avg_sharpe_ratio !== undefined && (
              <div className="summary-metric">
                <span className="metric-label">Avg Sharpe:</span>
                <span className="metric-value">{metrics.summary_metrics.avg_sharpe_ratio.toFixed(2)}</span>
              </div>
            )}
            {metrics.summary_metrics.avg_win_rate !== undefined && (
              <div className="summary-metric">
                <span className="metric-label">Avg Win Rate:</span>
                <span className="metric-value">{(metrics.summary_metrics.avg_win_rate * 100).toFixed(1)}%</span>
              </div>
            )}
            {metrics.summary_metrics.avg_profit_factor !== undefined && (
              <div className="summary-metric">
                <span className="metric-label">Avg Profit Factor:</span>
                <span className="metric-value">{metrics.summary_metrics.avg_profit_factor.toFixed(2)}</span>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

export default StrategyMetrics


