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
  const response = await fetch(`${API_BASE_URL}/api/risk/status`, {
    headers: token ? { 'Authorization': `Bearer ${token}` } : {}
  })
  return handleResponse(response)
}

export async function getMetrics(token) {
  const response = await fetch(`${API_BASE_URL}/api/metrics`, {
    headers: token ? { 'Authorization': `Bearer ${token}` } : {}
  })
  return handleResponse(response)
}

export async function getExecutionOrders(status, token) {
  const url = new URL(`${API_BASE_URL}/api/execution/orders`)
  if (status) url.searchParams.set('status', status)
  const response = await fetch(url, {
    headers: token ? { 'Authorization': `Bearer ${token}` } : {}
  })
  return handleResponse(response)
}

export async function createOrder(orderData, token) {
  const response = await fetch(`${API_BASE_URL}/api/execution/orders`, {
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
  const response = await fetch(`${API_BASE_URL}/api/execution/orders/${orderId}/cancel`, {
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
  const response = await fetch(`${API_BASE_URL}/api/risk/limits`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { 'Authorization': `Bearer ${token}` } : {})
    },
    body: JSON.stringify(limits)
  })
  return handleResponse(response)
}

export async function enableStrategy(strategyName, token) {
  const response = await fetch(`${API_BASE_URL}/strategies/${strategyName}/enable`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { 'Authorization': `Bearer ${token}` } : {})
    }
  })
  return handleResponse(response)
}

export async function disableStrategy(strategyName, token) {
  const response = await fetch(`${API_BASE_URL}/strategies/${strategyName}/disable`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { 'Authorization': `Bearer ${token}` } : {})
    }
  })
  return handleResponse(response)
}

export async function getStrategyOptimalParameters(strategyName, token) {
  const response = await fetch(`${API_BASE_URL}/strategies/${strategyName}/optimal-parameters`, {
    headers: token ? { 'Authorization': `Bearer ${token}` } : {}
  })
  return handleResponse(response)
}

export async function getStrategyResults(strategyName, limit = 10, splitType = null, token) {
  const url = new URL(`${API_BASE_URL}/strategies/${strategyName}/results`)
  url.searchParams.set('limit', limit)
  if (splitType) url.searchParams.set('split_type', splitType)
  const response = await fetch(url, {
    headers: token ? { 'Authorization': `Bearer ${token}` } : {}
  })
  return handleResponse(response)
}

export async function getStrategyMetrics(strategyName, token) {
  const response = await fetch(`${API_BASE_URL}/strategies/${strategyName}/metrics`, {
    headers: token ? { 'Authorization': `Bearer ${token}` } : {}
  })
  return handleResponse(response)
}

export async function getStrategyPerformance(strategyName, token) {
  const response = await fetch(`${API_BASE_URL}/strategies/${strategyName}/performance`, {
    headers: token ? { 'Authorization': `Bearer ${token}` } : {}
  })
  return handleResponse(response)
}

export async function getStrategiesConfig() {
  const response = await fetch(`${API_BASE_URL}/strategies/config`)
  return handleResponse(response)
}




