import React, { useState, useEffect } from 'react'
import { getMetrics, getExecutionOrders, createOrder, getStrategiesConfig } from '../services/api'
import { useRecommendations } from '../hooks/useRecommendations'
import { useRiskData } from '../hooks/useRiskData'
import { useAuth } from '../context/AuthContext'
import { wsService } from '../services/websocket'
import OpportunityCard from './OpportunityCard'
import RiskOverview from './RiskOverview'
import ExecutionTracker from './ExecutionTracker'
import StrategyControls from './StrategyControls'
import NotificationSystem from './NotificationSystem'
import './TradingDashboard.css'
import RecommendationsList from './RecommendationsList'
import AlertsCenter from './AlertsCenter'
import LiveMetrics from './LiveMetrics'
import AuthGate from './AuthGate'
import RiskPanel from './RiskPanel'

function TradingDashboard() {
  const { token, retryProtectedCall } = useAuth()
  const { items: recommendations, loading: recLoading, error: recError, kycBlocked: recKycBlocked } = useRecommendations('balanced')
  const { data: riskDataResp, loading: riskLoading, error: riskError } = useRiskData()
  const [metrics, setMetrics] = useState(null)
  const [strategies, setStrategies] = useState([])
  const [wsStatus, setWsStatus] = useState('connecting')
  const [selectedOpportunity, setSelectedOpportunity] = useState(null)
  const [showOrderModal, setShowOrderModal] = useState(false)

  useEffect(() => {
    loadDashboardData()

    const unsubscribeConn = wsService.subscribe('connection', (data) => {
      setWsStatus(data?.status || 'disconnected')
    })

    return () => {
      unsubscribeConn()
    }
  }, [])

  const loadDashboardData = async () => {
    await Promise.all([
      loadMetrics(),
      loadStrategies(),
    ])
  }

  const loadMetrics = async () => {
    if (!token) return
    try {
      const data = await retryProtectedCall(() => getMetrics(token))
      setMetrics(data)
    } catch (error) {
      console.error('Error loading metrics:', error)
    }
  }

  const loadStrategies = async () => {
    try {
      const config = await getStrategiesConfig()
      const list = (config || []).map((c) => ({ name: c.name, enabled: !!c.enabled, metrics: null }))
      setStrategies(list)
    } catch (error) {
      console.error('Error loading strategies:', error)
    }
  }

  const handleExecuteOpportunity = (opportunity) => {
    setSelectedOpportunity(opportunity)
    setShowOrderModal(true)
  }

  const handleConfirmOrder = async (orderData) => {
    try {
      await createOrder(orderData, token)
      setShowOrderModal(false)
      setSelectedOpportunity(null)
      loadDashboardData()
    } catch (error) {
      alert('Error al ejecutar orden: ' + error.message)
    }
  }

  const handleViewDetails = (opportunity) => {
    console.log('View details:', opportunity)
  }

  const loading = recLoading || riskLoading
  const error = recError || riskError

  if (loading && !riskDataResp && recommendations.length === 0) {
    return <div className="trading-dashboard loading">Cargando dashboard...</div>
  }

  return (
    <div className="trading-dashboard">
      <NotificationSystem />
      <AlertsCenter />

      <div className={`connection-banner ${wsStatus === 'connected' ? 'ok' : 'warn'}`}>
        WS: {wsStatus}
      </div>
      {error && (
        <div className="alert-banner error">{error}</div>
      )}

      {riskDataResp?.metrics && riskDataResp.metrics.current_drawdown_pct > 18 && (
        <div className="alert-banner warning">
          ⚠️ Drawdown cercano al límite: {riskDataResp.metrics.current_drawdown_pct.toFixed(2)}%
        </div>
      )}

      <AuthGate>
      <div className="dashboard-grid">
        <div className="dashboard-column">
          <RiskOverview riskData={riskDataResp} />
          <RiskPanel />
          <LiveMetrics />
          
          <div className="opportunities-section">
            <h2>Recomendaciones Priorizadas</h2>
            {recLoading ? (
              <div className="no-opportunities">Cargando recomendaciones...</div>
            ) : recommendations.length === 0 ? (
              <div className="no-opportunities">
                No hay recomendaciones disponibles en este momento
              </div>
            ) : (
              recommendations.map((opp, idx) => (
                <OpportunityCard
                  key={idx}
                  opportunity={opp}
                  onExecute={handleExecuteOpportunity}
                  onViewDetails={handleViewDetails}
                />
              ))
            )}
          </div>
        </div>

        <div className="dashboard-column">
          <ExecutionTracker token={token} />
          <RecommendationsList />
          <StrategyControls 
            strategies={strategies} 
            token={token}
            onUpdate={loadStrategies}
          />
        </div>
      </div>
      </AuthGate>

      {/* Order Confirmation Modal */}
      {showOrderModal && selectedOpportunity && (
        <OrderModal
          opportunity={selectedOpportunity}
          onConfirm={handleConfirmOrder}
          onCancel={() => {
            setShowOrderModal(false)
            setSelectedOpportunity(null)
          }}
        />
      )}
    </div>
  )
}

// Simple Order Modal Component
function OrderModal({ opportunity, onConfirm, onCancel }) {
  const [quantity, setQuantity] = useState(0.1)
  const [orderType, setOrderType] = useState('limit')

  const handleSubmit = (e) => {
    e.preventDefault()
    onConfirm({
      symbol: opportunity.symbol,
      side: opportunity.action.toLowerCase(),
      order_type: orderType,
      quantity: quantity,
      price: opportunity.current_price,
      stop_loss: opportunity.stop_loss,
      take_profit: opportunity.take_profit,
      strategy_name: opportunity.primary_strategy || '',
    })
  }

  return (
    <div className="modal-overlay" onClick={onCancel}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <h2>Ejecutar Orden</h2>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Símbolo:</label>
            <input type="text" value={opportunity.symbol} disabled />
          </div>
          <div className="form-group">
            <label>Cantidad:</label>
            <input
              type="number"
              value={quantity}
              onChange={(e) => setQuantity(parseFloat(e.target.value))}
              step="0.0001"
              min="0.0001"
              required
            />
          </div>
          <div className="form-group">
            <label>Tipo de Orden:</label>
            <select value={orderType} onChange={(e) => setOrderType(e.target.value)}>
              <option value="limit">Limit</option>
              <option value="market">Market</option>
            </select>
          </div>
          <div className="modal-actions">
            <button type="button" onClick={onCancel}>Cancelar</button>
            <button type="submit">Confirmar y Ejecutar</button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default TradingDashboard

