import React, { useState } from 'react'
import { submitRecommendationFeedback } from '../services/api'

function RecommendationChecklist({ item, onSubmitted }) {
  const [checks, setChecks] = useState(() => (item.pre_trade_checklist || []).reduce((acc, c) => ({ ...acc, [c.key]: !!c.checked }), {}))
  const [notes, setNotes] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const toggle = (key) => setChecks({ ...checks, [key]: !checks[key] })

  const submit = async (status) => {
    setSubmitting(true)
    try {
      const checklist = {
        pre_trade: item.pre_trade_checklist.map(c => ({ ...c, checked: checks[c.key] }))
      }
      await submitRecommendationFeedback({ status, checklist, notes, payload: item })
      if (onSubmitted) onSubmitted(status)
    } catch (e) {
      alert('Error enviando feedback: ' + e.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="recommendation-checklist">
      <h3>Checklist pre-trade</h3>
      <ul>
        {(item.pre_trade_checklist || []).map(ch => (
          <li key={ch.key} className={ch.required ? 'required' : ''}>
            <label>
              <input type="checkbox" checked={!!checks[ch.key]} onChange={() => toggle(ch.key)} /> {ch.label}
              {ch.required && <span className="req">*</span>}
            </label>
          </li>
        ))}
      </ul>
      <div className="notes">
        <textarea value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Notas (opcional)" />
      </div>
      <div className="actions">
        <button disabled={submitting} onClick={() => submit('accepted')}>Aceptar</button>
        <button disabled={submitting} onClick={() => submit('rejected')}>Rechazar</button>
      </div>
    </div>
  )
}

export default RecommendationChecklist


