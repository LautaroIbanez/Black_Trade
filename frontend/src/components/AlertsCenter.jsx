import React, { useEffect, useState } from 'react'
import { wsService } from '../services/websocket'

function AlertsCenter() {
  const [alerts, setAlerts] = useState([])

  useEffect(() => {
    const unsub = wsService.subscribe('alert', (payload) => {
      setAlerts((prev) => [{ ...payload, id: Date.now() }, ...prev].slice(0, 5))
    })
    return () => unsub()
  }, [])

  if (alerts.length === 0) return null

  return (
    <div className="alerts-center">
      {alerts.map(a => (
        <div key={a.id} className={`alert-banner ${a.severity || 'warning'}`}>
          <strong>{a.title}</strong>: {a.message}
        </div>
      ))}
    </div>
  )
}

export default AlertsCenter


