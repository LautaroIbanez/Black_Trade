import React, { useEffect, useState } from 'react'
import { getLiveRecommendations } from '../services/api'
import RecommendationChecklist from './RecommendationChecklist'

function RecommendationsList({ profile = 'balanced' }) {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const load = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await getLiveRecommendations(profile)
      setItems(res.items || [])
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    const interval = setInterval(load, 30000)
    return () => clearInterval(interval)
  }, [profile])

  if (loading) return <div>Cargando recomendaciones...</div>
  if (error) return <div className="alert-banner error">{error}</div>

  return (
    <div className="recommendations-list">
      <h2>Oportunidades Prioritarias</h2>
      {items.length === 0 ? (
        <div>No hay recomendaciones disponibles</div>
      ) : (
        items.map((item, idx) => (
          <div key={idx} className="recommendation-card">
            <div className="rec-header">
              <div className={`rec-action ${item.action.toLowerCase()}`}>{item.action}</div>
              <div className="rec-meta">Confianza {Math.round(item.confidence * 100)}% • Riesgo {item.risk_level} • {item.timestamp}</div>
            </div>
            <div className="rec-justification">{item.justification}</div>
            <RecommendationChecklist item={item} onSubmitted={load} />
          </div>
        ))
      )}
    </div>
  )
}

export default RecommendationsList


