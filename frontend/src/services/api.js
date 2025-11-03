const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

import { authHeader } from './auth'

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
    headers: token ? { 'Authorization': `Bearer ${token}` } : authHeader()
  })
  return handleResponse(response)
}

export async function getMetrics(token) {
  const response = await fetch(`${API_BASE_URL}/api/metrics`, {
    headers: token ? { 'Authorization': `Bearer ${token}` } : authHeader()
  })
  return handleResponse(response)
}

export async function getExecutionOrders(status, token) {
  const url = new URL(`${API_BASE_URL}/api/execution/orders`)
  if (status) url.searchParams.set('status', status)
  const response = await fetch(url, {
    headers: token ? { 'Authorization': `Bearer ${token}` } : authHeader()
  })
  return handleResponse(response)
}

export async function createOrder(orderData, token) {
  const response = await fetch(`${API_BASE_URL}/api/execution/orders`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { 'Authorization': `Bearer ${token}` } : authHeader())
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
      ...(token ? { 'Authorization': `Bearer ${token}` } : authHeader())
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
      ...(token ? { 'Authorization': `Bearer ${token}` } : authHeader())
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
    headers: token ? { 'Authorization': `Bearer ${token}` } : authHeader()
  })
  return handleResponse(response)
}

export async function getStrategyResults(strategyName, limit = 10, splitType = null, token) {
  const url = new URL(`${API_BASE_URL}/strategies/${strategyName}/results`)
  url.searchParams.set('limit', limit)
  if (splitType) url.searchParams.set('split_type', splitType)
  const response = await fetch(url, {
    headers: token ? { 'Authorization': `Bearer ${token}` } : authHeader()
  })
  return handleResponse(response)
}

export async function getStrategyMetrics(strategyName, token) {
  const response = await fetch(`${API_BASE_URL}/strategies/${strategyName}/metrics`, {
    headers: token ? { 'Authorization': `Bearer ${token}` } : authHeader()
  })
  return handleResponse(response)
}

export async function getStrategyPerformance(strategyName, token) {
  const response = await fetch(`${API_BASE_URL}/strategies/${strategyName}/performance`, {
    headers: token ? { 'Authorization': `Bearer ${token}` } : authHeader()
  })
  return handleResponse(response)
}

export async function getStrategiesConfig() {
  const response = await fetch(`${API_BASE_URL}/strategies/config`, { headers: authHeader() })
  return handleResponse(response)
}

// Human-oriented recommendations
export async function getLiveRecommendations(profile = 'balanced') {
  const response = await fetch(`${API_BASE_URL}/api/recommendations/live?profile=${profile}`, { headers: authHeader() })
  return handleResponse(response)
}

export async function submitRecommendationFeedback({ status, recommendation_id, checklist, notes, user_id, payload }) {
  const response = await fetch(`${API_BASE_URL}/api/recommendations/feedback`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeader() },
    body: JSON.stringify({ status, recommendation_id, checklist, notes, user_id, payload })
  })
  return handleResponse(response)
}

export async function listRecommendationHistory(limit = 20) {
  const response = await fetch(`${API_BASE_URL}/api/recommendations/history?limit=${limit}`, { headers: authHeader() })
  return handleResponse(response)
}

// Auth endpoints
export async function registerUser({ username, email, country, role }) {
  const response = await fetch(`${API_BASE_URL}/api/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, email, country, role })
  })
  return handleResponse(response)
}

export async function loginUser({ username, role }) {
  const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, role })
  })
  return handleResponse(response)
}




