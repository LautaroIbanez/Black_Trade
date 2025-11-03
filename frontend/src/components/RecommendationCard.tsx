import React, { useState } from 'react'
import { submitRecommendationFeedback } from '../services/api'

type ChecklistItem = { key: string; label: string; required?: boolean; checked?: boolean }

type Props = {
  item: any
  onSubmitted?: () => void
}

const RecommendationCard: React.FC<Props> = ({ item, onSubmitted }) => {
  const [checks, setChecks] = useState<Record<string, boolean>>(() => (item.pre_trade_checklist || []).reduce((acc: any, c: ChecklistItem) => ({ ...acc, [c.key]: !!c.checked }), {}))
  const [notes, setNotes] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const toggle = (key: string) => setChecks({ ...checks, [key]: !checks[key] })

  const submit = async (status: 'accepted' | 'rejected') => {
    setSubmitting(true)
    try {
      const checklist = { pre_trade: (item.pre_trade_checklist || []).map((c: ChecklistItem) => ({ ...c, checked: checks[c.key] })) }
      await submitRecommendationFeedback({ status, checklist, notes, payload: item })
      onSubmitted && onSubmitted()
    } catch (e: any) {
      alert(e.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="recommendation-card">
      <div className="rec-header">
        <div className={`rec-action ${String(item.action || '').toLowerCase()}`}>{item.action}</div>
        <div className="rec-meta">Confianza {Math.round((item.confidence || 0) * 100)}% • Riesgo {item.risk_level} • {item.timestamp}</div>
      </div>
      <div className="rec-justification">{item.justification}</div>
      <div className="sizing">Sugerido: ${Number(item.suggested_position_size_usd || 0).toFixed(2)} ({Math.round((item.suggested_position_size_pct || 0) * 100)}%)</div>
      <div className="checklist">
        <h4>Checklist</h4>
        <ul>
          {(item.pre_trade_checklist || []).map((ch: ChecklistItem) => (
            <li key={ch.key} className={ch.required ? 'required' : ''}>
              <label>
                <input type="checkbox" checked={!!checks[ch.key]} onChange={() => toggle(ch.key)} /> {ch.label}
              </label>
            </li>
          ))}
        </ul>
        <textarea placeholder="Notas (opcional)" value={notes} onChange={(e) => setNotes(e.target.value)} />
        <div className="actions">
          <button disabled={submitting} onClick={() => submit('accepted')}>Aceptar</button>
          <button disabled={submitting} onClick={() => submit('rejected')}>Rechazar</button>
        </div>
      </div>
    </div>
  )
}

export default RecommendationCard


