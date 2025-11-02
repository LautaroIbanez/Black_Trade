import React from 'react'
import './OpportunityCard.css'

function OpportunityCard({ opportunity, onExecute, onViewDetails }) {
  const getConfidenceColor = (confidence) => {
    if (confidence >= 0.8) return 'high'
    if (confidence >= 0.6) return 'medium'
    return 'low'
  }

  const getActionLabel = () => {
    if (opportunity.status === 'executing') return 'Ejecutando...'
    if (opportunity.status === 'filled') return 'Ejecutada'
    if (opportunity.status === 'expired') return 'Expirada'
    return 'Ejecutar'
  }

  const isActionable = opportunity.status === 'available'

  return (
    <div className={`opportunity-card ${opportunity.status || 'available'}`}>
      <div className="opportunity-header">
        <div className="symbol-info">
          <span className="symbol">{opportunity.symbol}</span>
          <span className={`action ${opportunity.action?.toLowerCase()}`}>
            {opportunity.action}
          </span>
        </div>
        <div className={`confidence-badge ${getConfidenceColor(opportunity.confidence)}`}>
          {Math.round(opportunity.confidence * 100)}% confianza
        </div>
      </div>

      <div className="opportunity-price">
        <span className="current-price">${opportunity.current_price?.toLocaleString()}</span>
        {opportunity.risk_reward_ratio && (
          <span className="risk-reward">R:R {opportunity.risk_reward_ratio.toFixed(2)}:1</span>
        )}
      </div>

      <div className="opportunity-details">
        <div className="detail-row">
          <span className="label">Entry:</span>
          <span className="value">
            ${opportunity.entry_range?.min?.toLocaleString()} - ${opportunity.entry_range?.max?.toLocaleString()}
          </span>
        </div>
        <div className="detail-row">
          <span className="label">Stop Loss:</span>
          <span className="value">${opportunity.stop_loss?.toLocaleString()}</span>
        </div>
        <div className="detail-row">
          <span className="label">Take Profit:</span>
          <span className="value">${opportunity.take_profit?.toLocaleString()}</span>
        </div>
      </div>

      {opportunity.supporting_strategies && opportunity.supporting_strategies.length > 0 && (
        <div className="strategies">
          <span className="label">Estrategias:</span>
          <div className="strategy-tags">
            {opportunity.supporting_strategies.slice(0, 3).map((strategy, idx) => (
              <span key={idx} className="strategy-tag">{strategy}</span>
            ))}
          </div>
        </div>
      )}

      <div className="opportunity-actions">
        <button
          className="btn-primary"
          onClick={() => onExecute(opportunity)}
          disabled={!isActionable}
        >
          {getActionLabel()}
        </button>
        <button
          className="btn-secondary"
          onClick={() => onViewDetails(opportunity)}
        >
          Ver Detalles
        </button>
      </div>

      {opportunity.status === 'executing' && (
        <div className="execution-status">
          <div className="progress-bar">
            <div className="progress-fill"></div>
          </div>
          <span className="status-text">Enviando al exchange...</span>
        </div>
      )}
    </div>
  )
}

export default OpportunityCard

