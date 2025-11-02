const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

async function handleResponse(response) {
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Network error' }))
    throw new Error(error.detail || 'Request failed')
  }
  return response.json()
}

export async function refreshData() {
  const response = await fetch(`${API_BASE_URL}/refresh`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    }
  })
  return handleResponse(response)
}

export async function getRecommendation(profile = 'balanced') {
  const response = await fetch(`${API_BASE_URL}/recommendation?profile=${profile}`)
  return handleResponse(response)
}

export async function getStrategies() {
  const response = await fetch(`${API_BASE_URL}/strategies`)
  return handleResponse(response)
}

export async function getRiskStatus(token) {
  const response = await fetch(`${API_BASE_URL}/risk/status`, {
    headers: token ? { 'Authorization': `Bearer ${token}` } : {}
  })
  return handleResponse(response)
}

export async function getMetrics(token) {
  const response = await fetch(`${API_BASE_URL}/metrics`, {
    headers: token ? { 'Authorization': `Bearer ${token}` } : {}
  })
  return handleResponse(response)
}

export async function getExecutionOrders(status, token) {
  const url = new URL(`${API_BASE_URL}/execution/orders`)
  if (status) url.searchParams.set('status', status)
  const response = await fetch(url, {
    headers: token ? { 'Authorization': `Bearer ${token}` } : {}
  })
  return handleResponse(response)
}

export async function createOrder(orderData, token) {
  const response = await fetch(`${API_BASE_URL}/execution/orders`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { 'Authorization': `Bearer ${token}` } : {})
    },
    body: JSON.stringify(orderData)
  })
  return handleResponse(response)
}

export async function cancelOrder(orderId, reason, token) {
  const response = await fetch(`${API_BASE_URL}/execution/orders/${orderId}/cancel`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { 'Authorization': `Bearer ${token}` } : {})
    },
    body: JSON.stringify({ reason })
  })
  return handleResponse(response)
}

export async function updateRiskLimits(limits, token) {
  const response = await fetch(`${API_BASE_URL}/risk/limits`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { 'Authorization': `Bearer ${token}` } : {})
    },
    body: JSON.stringify(limits)
  })
  return handleResponse(response)
}

export async function toggleStrategy(strategyName, enabled, token) {
  // This would need to be implemented in the backend
  const response = await fetch(`${API_BASE_URL}/strategies/${strategyName}/toggle`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { 'Authorization': `Bearer ${token}` } : {})
    },
    body: JSON.stringify({ enabled })
  })
  return handleResponse(response)
}




