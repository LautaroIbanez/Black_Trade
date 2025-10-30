import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import React from 'react'
import Dashboard from '../components/Dashboard'

vi.mock('../services/api', () => ({
  getRecommendation: vi.fn(async () => ({
    action: 'HOLD',
    confidence: 0.35,
    entry_range: { min: 100, max: 101 },
    stop_loss: 99,
    take_profit: 102,
    current_price: 100.5,
    primary_strategy: 'None',
    supporting_strategies: [],
    strategy_details: [],
    signal_consensus: 0.5,
    risk_level: 'LOW',
    risk_reward_ratio: 0.0,
    entry_label: '',
    risk_percentage: 0.0,
    normalized_weights_sum: 1.0,
    position_size_usd: 0.0,
    position_size_pct: 0.0
  })),
  refreshData: vi.fn(async () => ({}))
}))

describe('Dashboard refresh flow', () => {
  it('renders without crashing and shows position size fields', async () => {
    render(<Dashboard />)
    // Wait for refresh to complete
    const btn = await screen.findByRole('button', { name: /Refresh/i })
    expect(btn).toBeInTheDocument()
    // Ensure position size placeholder renders
    const position = await screen.findByText(/Position Size/i)
    expect(position).toBeInTheDocument()
  })

  it('renders placeholders when optional fields are missing', async () => {
    const api = await import('../services/api')
    api.getRecommendation.mockResolvedValueOnce({
      action: 'HOLD',
      confidence: null,
      entry_range: null,
      stop_loss: null,
      take_profit: null,
      current_price: null,
      primary_strategy: '',
      supporting_strategies: [],
      strategy_details: [],
      signal_consensus: 0.0,
      risk_level: 'LOW',
      risk_reward_ratio: null,
      entry_label: '',
      risk_percentage: null,
      normalized_weights_sum: null,
      position_size_usd: null,
      position_size_pct: null
    })
    render(<Dashboard />)
    const priceLabel = await screen.findByText(/Current Price/i)
    expect(priceLabel).toBeInTheDocument()
    // N/A placeholders should be present at least in some transparency fields
    const na = await screen.findAllByText('N/A')
    expect(na.length).toBeGreaterThan(0)
  })
})


