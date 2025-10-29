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

export async function getRecommendation() {
  const response = await fetch(`${API_BASE_URL}/recommendation`)
  return handleResponse(response)
}

export async function getStrategies() {
  const response = await fetch(`${API_BASE_URL}/strategies`)
  return handleResponse(response)
}




