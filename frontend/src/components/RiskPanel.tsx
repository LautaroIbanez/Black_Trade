import React, { useEffect, useState } from 'react'
import { wsService } from '../services/websocket'

function RiskPanel() {
  const [limits, setLimits] = useState<any | null>(null)
  const [lastChange, setLastChange] = useState<string | null>(null)

  useEffect(() => {
    const unsub = wsService.subscribe('risk_limits_changed', (payload: any) => {
      setLimits(payload?.limits)
      setLastChange(new Date().toLocaleString())
    })
    return () => unsub()
  }, [])

  if (!limits) return null

  return (
    <div className="risk-panel">
      <h4>Límites de Riesgo (vía WS)</h4>
      <div className="limits">
        <div>Max Exposición: {limits.max_exposure_pct}%</div>
        <div>Max Posición: {limits.max_position_pct}%</div>
        <div>Max Drawdown: {limits.max_drawdown_pct}%</div>
        <div>VaR 1d 95: {limits.var_limit_1d_95}</div>
      </div>
      <div className="ts">Actualizado: {lastChange}</div>
    </div>
  )
}

export default RiskPanel


