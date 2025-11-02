import React, { useState, useEffect } from 'react'
import { wsService } from '../services/websocket'
import './NotificationSystem.css'

function NotificationSystem() {
  const [notifications, setNotifications] = useState([])

  useEffect(() => {
    const unsubscribeOrder = wsService.subscribe('order_update', (data) => {
      addNotification({
        type: 'info',
        title: 'Actualización de Orden',
        message: `Orden ${data.order_id} - ${data.status}`,
        timestamp: new Date(),
      })
    })

    const unsubscribeAlert = wsService.subscribe('alert', (data) => {
      addNotification({
        type: data.severity === 'critical' ? 'error' : 'warning',
        title: data.title,
        message: data.message,
        timestamp: new Date(),
      })
    })

    const unsubscribeFill = wsService.subscribe('order_filled', (data) => {
      addNotification({
        type: 'success',
        title: 'Orden Ejecutada',
        message: `Orden ${data.order_id} ejecutada @ $${data.price}`,
        timestamp: new Date(),
      })
    })

    return () => {
      unsubscribeOrder()
      unsubscribeAlert()
      unsubscribeFill()
    }
  }, [])

  const addNotification = (notification) => {
    const id = Date.now() + Math.random()
    const newNotification = { ...notification, id }
    
    setNotifications(prev => [...prev, newNotification])

    // Auto-remove after 5 seconds
    setTimeout(() => {
      removeNotification(newNotification.id)
    }, 5000)
  }

  const removeNotification = (id) => {
    setNotifications(prev => prev.filter(n => n.id !== id))
  }

  return (
    <div className="notification-container">
      {notifications.map(notification => (
        <div
          key={notification.id}
          className={`notification notification-${notification.type}`}
          onClick={() => removeNotification(notification.id)}
        >
          <div className="notification-icon">
            {notification.type === 'success' && '✅'}
            {notification.type === 'error' && '🚨'}
            {notification.type === 'warning' && '⚠️'}
            {notification.type === 'info' && 'ℹ️'}
          </div>
          <div className="notification-content">
            <div className="notification-title">{notification.title}</div>
            <div className="notification-message">{notification.message}</div>
          </div>
          <button className="notification-close" onClick={() => removeNotification(notification.id)}>
            ×
          </button>
        </div>
      ))}
    </div>
  )
}

export default NotificationSystem

