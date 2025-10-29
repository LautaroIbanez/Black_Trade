import React, { useState, useEffect } from 'react'
import './MonitoringDashboard.css'

function MonitoringDashboard() {
  const [metrics, setMetrics] = useState(null)
  const [alerts, setAlerts] = useState([])
  const [health, setHealth] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const fetchMonitoringData = async () => {
    setLoading(true)
    setError(null)
    try {
      const [metricsResponse, alertsResponse, healthResponse] = await Promise.all([
        fetch('/api/monitoring/metrics'),
        fetch('/api/monitoring/alerts'),
        fetch('/api/monitoring/health')
      ])

      if (!metricsResponse.ok || !alertsResponse.ok || !healthResponse.ok) {
        throw new Error('Failed to fetch monitoring data')
      }

      const metricsData = await metricsResponse.json()
      const alertsData = await alertsResponse.json()
      const healthData = await healthResponse.json()

      setMetrics(metricsData.latest_metrics)
      setAlerts(alertsData)
      setHealth(healthData)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchMonitoringData()
    // Refresh every 30 seconds
    const interval = setInterval(fetchMonitoringData, 30000)
    return () => clearInterval(interval)
  }, [])

  const getHealthStatusColor = (status) => {
    switch (status) {
      case 'healthy': return '#22c55e'
      case 'warning': return '#eab308'
      case 'degraded': return '#f97316'
      case 'critical': return '#ef4444'
      default: return '#6b7280'
    }
  }

  const getSeverityColor = (severity) => {
    switch (severity) {
      case 'high': return '#ef4444'
      case 'medium': return '#eab308'
      case 'low': return '#22c55e'
      default: return '#6b7280'
    }
  }

  if (error) {
    return (
      <div className="monitoring-dashboard">
        <div className="error-container">
          <p className="error-message">{error}</p>
          <button onClick={fetchMonitoringData} className="retry-btn">
            Retry
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="monitoring-dashboard">
      <div className="monitoring-header">
        <h2>System Monitoring</h2>
        <button 
          onClick={fetchMonitoringData} 
          className="refresh-btn" 
          disabled={loading}
        >
          {loading ? 'Refreshing...' : 'Refresh'}
        </button>
      </div>

      {/* System Health Overview */}
      {health && (
        <div className="health-overview">
          <div className="health-card">
            <div className="health-status">
              <span 
                className="health-indicator"
                style={{ backgroundColor: getHealthStatusColor(health.status) }}
              ></span>
              <span className="health-label">System Status</span>
              <span className="health-value">{health.status.toUpperCase()}</span>
            </div>
            <div className="health-score">
              <span className="score-label">Health Score</span>
              <span className="score-value">{health.health_score}/100</span>
            </div>
          </div>
        </div>
      )}

      {/* Metrics Grid */}
      {metrics && (
        <div className="metrics-grid">
          <div className="metric-card">
            <h3>Recalibration Status</h3>
            <div className="metric-stats">
              <div className="stat-item">
                <span className="stat-label">Total Profiles</span>
                <span className="stat-value">{metrics.total_profiles}</span>
              </div>
              <div className="stat-item">
                <span className="stat-label">Successful</span>
                <span className="stat-value success">{metrics.successful_recalibrations}</span>
              </div>
              <div className="stat-item">
                <span className="stat-label">Failed</span>
                <span className="stat-value error">{metrics.failed_recalibrations}</span>
              </div>
              <div className="stat-item">
                <span className="stat-label">Success Rate</span>
                <span className="stat-value">
                  {metrics.total_profiles > 0 
                    ? `${((metrics.successful_recalibrations / metrics.total_profiles) * 100).toFixed(1)}%`
                    : '0%'
                  }
                </span>
              </div>
            </div>
          </div>

          <div className="metric-card">
            <h3>Anomaly Detection</h3>
            <div className="metric-stats">
              <div className="stat-item">
                <span className="stat-label">Total Anomalies</span>
                <span className="stat-value">{metrics.total_anomalies}</span>
              </div>
              <div className="stat-item">
                <span className="stat-label">High Severity</span>
                <span className="stat-value error">{metrics.high_severity_alerts}</span>
              </div>
            </div>
          </div>

          <div className="metric-card">
            <h3>Profile Actions</h3>
            <div className="profile-actions">
              {Object.entries(metrics.profile_actions).map(([profile, action]) => (
                <div key={profile} className="profile-action">
                  <span className="profile-name">{profile}</span>
                  <span className={`action-badge ${action.toLowerCase()}`}>{action}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="metric-card">
            <h3>Strategy Usage</h3>
            <div className="strategy-usage">
              {Object.entries(metrics.strategy_usage).map(([strategy, count]) => (
                <div key={strategy} className="strategy-item">
                  <span className="strategy-name">{strategy}</span>
                  <span className="strategy-count">{count}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Alerts Section */}
      <div className="alerts-section">
        <h3>Recent Alerts</h3>
        {alerts.length === 0 ? (
          <div className="no-alerts">
            <p>No recent alerts</p>
          </div>
        ) : (
          <div className="alerts-list">
            {alerts.slice(0, 10).map((alert, index) => (
              <div key={index} className="alert-item">
                <div className="alert-header">
                  <span 
                    className="alert-severity"
                    style={{ backgroundColor: getSeverityColor(alert.severity) }}
                  >
                    {alert.severity.toUpperCase()}
                  </span>
                  <span className="alert-type">{alert.type}</span>
                  <span className="alert-time">
                    {new Date(alert.timestamp).toLocaleString()}
                  </span>
                </div>
                <div className="alert-description">
                  {alert.description}
                </div>
                {alert.profile && (
                  <div className="alert-profile">
                    Profile: {alert.profile}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default MonitoringDashboard
