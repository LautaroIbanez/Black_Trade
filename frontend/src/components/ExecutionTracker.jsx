import React, { useState, useEffect } from 'react'
import { getExecutionOrders, cancelOrder } from '../services/api'
import './ExecutionTracker.css'

function ExecutionTracker({ token, refreshInterval = 5000 }) {
  const [orders, setOrders] = useState([])
  const [loading, setLoading] = useState(true)

  const fetchOrders = async () => {
    try {
      const data = await getExecutionOrders(null, token)
      setOrders(data.orders || [])
    } catch (error) {
      console.error('Error fetching orders:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchOrders()
    const interval = setInterval(fetchOrders, refreshInterval)
    return () => clearInterval(interval)
  }, [token, refreshInterval])

  const handleCancel = async (orderId) => {
    if (!confirm('¿Está seguro de que desea cancelar esta orden?')) {
      return
    }

    try {
      await cancelOrder(orderId, 'Manual cancellation', token)
      fetchOrders()
    } catch (error) {
      alert('Error al cancelar orden: ' + error.message)
    }
  }

  const getStatusIcon = (status) => {
    switch (status) {
      case 'pending':
        return '⏳'
      case 'submitted':
        return '📤'
      case 'partially_filled':
        return '⏸️'
      case 'filled':
        return '✅'
      case 'cancelled':
        return '❌'
      case 'rejected':
        return '⚠️'
      default:
        return '❓'
    }
  }

  const getStatusColor = (status) => {
    switch (status) {
      case 'pending':
      case 'submitted':
        return 'blue'
      case 'partially_filled':
        return 'orange'
      case 'filled':
        return 'green'
      case 'cancelled':
      case 'rejected':
        return 'red'
      default:
        return 'gray'
    }
  }

  if (loading) {
    return <div className="execution-tracker">Cargando órdenes...</div>
  }

  return (
    <div className="execution-tracker">
      <div className="tracker-header">
        <h3>Estado de Ejecución</h3>
        <button onClick={fetchOrders} className="refresh-btn">🔄</button>
      </div>

      <div className="orders-list">
        {orders.length === 0 ? (
          <div className="no-orders">No hay órdenes activas</div>
        ) : (
          orders.map((order) => (
            <div key={order.order_id} className="order-item">
              <div className="order-header">
                <div className="order-id">#{order.order_id?.slice(-8)}</div>
                <div className={`order-status ${getStatusColor(order.state?.status)}`}>
                  {getStatusIcon(order.state?.status)} {order.state?.status || 'unknown'}
                </div>
              </div>

              <div className="order-details">
                <div className="order-info">
                  <span className="order-symbol">{order.state?.order?.symbol}</span>
                  <span className={`order-side ${order.state?.order?.side}`}>
                    {order.state?.order?.side?.toUpperCase()}
                  </span>
                  <span className="order-quantity">
                    {order.state?.order?.quantity} {order.state?.order?.symbol?.replace('USDT', '')}
                  </span>
                </div>

                {order.state?.order?.price && (
                  <div className="order-price">
                    @ ${order.state?.order?.price.toLocaleString()}
                  </div>
                )}

                {order.state?.filled_quantity > 0 && (
                  <div className="order-fill">
                    Llenado: {order.state?.filled_quantity} / {order.state?.order?.quantity}
                    {order.state?.average_fill_price && (
                      <span> @ ${order.state?.average_fill_price.toLocaleString()}</span>
                    )}
                  </div>
                )}
              </div>

              {(order.state?.status === 'pending' || order.state?.status === 'submitted') && (
                <div className="order-actions">
                  <button 
                    onClick={() => handleCancel(order.order_id)}
                    className="cancel-btn"
                  >
                    Cancelar
                  </button>
                </div>
              )}

              {order.state?.submitted_at && (
                <div className="order-timestamp">
                  Enviado: {new Date(order.state.submitted_at).toLocaleString()}
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  )
}

export default ExecutionTracker

