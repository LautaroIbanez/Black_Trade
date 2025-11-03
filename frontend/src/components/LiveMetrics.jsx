import React, { useEffect, useState } from 'react'
import { getMetrics } from '../services/api'

function LiveMetrics() {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  const load = async () => {
    try {
      setError(null)
      const res = await getMetrics()
      setData(res)
    } catch (e) {
      setError(e.message)
    }
  }

  useEffect(() => {
    load()
    const iv = setInterval(load, 30000)
    return () => clearInterval(iv)
  }, [])

  if (error) return <div className="alert-banner error">{error}</div>
  if (!data) return <div>Cargando métricas...</div>

  const freshness = data.timestamp
  const latency = data.latency?.p95_ms
  const ordersPerMin = data.throughput?.orders_per_minute

  return (
    <div className="live-metrics">
      <div className="metric-box">
        <div className="label">Frescura señales</div>
        <div className="value">{freshness}</div>
      </div>
      <div className="metric-box">
        <div className="label">Latencia p95</div>
        <div className={`value ${latency > 2000 ? 'warn' : 'ok'}`}>{Math.round(latency)} ms</div>
      </div>
      <div className="metric-box">
        <div className="label">Órdenes/min</div>
        <div className="value">{Math.round(ordersPerMin || 0)}</div>
      </div>
    </div>
  )
}

export default LiveMetrics


