import React, { useState, useEffect } from 'react'
import { getRecommendation, getRiskStatus, getMetrics, getExecutionOrders, createOrder } from '../services/api'
import { wsService } from '../services/websocket'
import OpportunityCard from './OpportunityCard'
import RiskOverview from './RiskOverview'
import ExecutionTracker from './ExecutionTracker'
import StrategyControls from './StrategyControls'
import NotificationSystem from './NotificationSystem'
import './TradingDashboard.css'

function TradingDashboard({ token }) {
  const [opportunities, setOpportunities] = useState([])
  const [riskData, setRiskData] = useState(null)
  const [metrics, setMetrics] = useState(null)
  const [strategies, setStrategies] = useState([])
  const [loading, setLoading] = useState(true)
  const [selectedOpportunity, setSelectedOpportunity] = useState(null)
  const [showOrderModal, setShowOrderModal] = useState(false)

  useEffect(() => {
    loadDashboardData()

    // Subscribe to WebSocket updates
    const unsubscribeOrder = wsService.subscribe('order_update', (data) => {
      // Refresh orders when update received
      loadExecutionData()
    })

    const unsubscribeRisk = wsService.subscribe('risk_update', (data) => {
      loadRiskData()
    })

    // Auto-refresh every 30 seconds
    const interval = setInterval(loadDashboardData, 30000)

    return () => {
      unsubscribeOrder()
      unsubscribeRisk()
      clearInterval(interval)
    }
  }, [])

  const loadDashboardData = async () => {
    try {
      await Promise.all([
        loadOpportunities(),
        loadRiskData(),
        loadMetrics(),
        loadStrategies(),
        loadExecutionData(),
      ])
    } catch (error) {
      console.error('Error loading dashboard:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadOpportunities = async () => {
    try {
      const data = await getRecommendation('balanced')
      if (data && data.action !== 'HOLD') {
        setOpportunities([{
          ...data,
          symbol: 'BTCUSDT', // Would come from actual data
          status: 'available',
        }])
      } else {
        setOpportunities([])
      }
    } catch (error) {
      console.error('Error loading opportunities:', error)
    }
  }

  const loadRiskData = async () => {
    try {
      const data = await getRiskStatus(token)
      setRiskData(data)
    } catch (error) {
      console.error('Error loading risk data:', error)
    }
  }

  const loadMetrics = async () => {
    try {
      const data = await getMetrics(token)
      setMetrics(data)
    } catch (error) {
      console.error('Error loading metrics:', error)
    }
  }

  const loadStrategies = async () => {
    try {
      // This would fetch actual strategy data
      setStrategies([
        { name: 'EMA_RSI', enabled: true, metrics: { pnl: 500, win_rate: 0.65, trades: 45 } },
        { name: 'Momentum', enabled: true, metrics: { pnl: 300, win_rate: 0.58, trades: 32 } },
        { name: 'Breakout', enabled: false, metrics: { pnl: -50, win_rate: 0.45, trades: 28 } },
      ])
    } catch (error) {
      console.error('Error loading strategies:', error)
    }
  }

  const loadExecutionData = async () => {
    // ExecutionTracker handles its own loading
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
    // Open detail modal or navigate
    console.log('View details:', opportunity)
  }

  if (loading) {
    return <div className="trading-dashboard loading">Cargando dashboard...</div>
  }

  return (
    <div className="trading-dashboard">
      <NotificationSystem />

      {/* Alert Banner */}
      {riskData?.metrics && riskData.metrics.current_drawdown_pct > 18 && (
        <div className="alert-banner warning">
          ⚠️ Drawdown cercano al límite: {riskData.metrics.current_drawdown_pct.toFixed(2)}%
        </div>
      )}

      <div className="dashboard-grid">
        {/* Left Column */}
        <div className="dashboard-column">
          <RiskOverview riskData={riskData} />
          
          <div className="opportunities-section">
            <h2>Oportunidades Priorizadas</h2>
            {opportunities.length === 0 ? (
              <div className="no-opportunities">
                No hay oportunidades disponibles en este momento
              </div>
            ) : (
              opportunities.map((opp, idx) => (
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

        {/* Right Column */}
        <div className="dashboard-column">
          <ExecutionTracker token={token} />
          <StrategyControls 
            strategies={strategies} 
            token={token}
            onUpdate={loadStrategies}
          />
        </div>
      </div>

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

