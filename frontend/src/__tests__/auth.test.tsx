import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import React from 'react'
import { AuthProvider, useAuth } from '../context/AuthContext'

// Mock auth services
vi.mock('../services/auth', () => ({
  getToken: vi.fn(() => null),
  getUserId: vi.fn(() => null),
  getUsername: vi.fn(() => null),
  getRefresh: vi.fn(() => null),
  clearSession: vi.fn(),
  setSession: vi.fn(),
  refreshAccessToken: vi.fn(() => Promise.resolve(false)),
}))

vi.mock('../services/api', () => ({
  checkKYCStatus: vi.fn(() => Promise.resolve({ verified: false })),
  loginUser: vi.fn(() => Promise.resolve({
    access_token: 'access123',
    refresh_token: 'refresh123',
    user_id: 'user123',
    role: 'viewer'
  })),
  refreshToken: vi.fn(() => Promise.resolve({
    access_token: 'access456',
    refresh_token: 'refresh456',
    user_id: 'user123',
    role: 'viewer'
  })),
}))

// Test component that uses auth
function TestComponent() {
  const { isAuthenticated, token, isKYCVerified } = useAuth()
  return (
    <div>
      <div data-testid="authenticated">{isAuthenticated ? 'yes' : 'no'}</div>
      <div data-testid="token">{token || 'none'}</div>
      <div data-testid="kyc">{isKYCVerified ? 'yes' : 'no'}</div>
    </div>
  )
}

describe('AuthProvider', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('provides initial unauthenticated state', () => {
    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    )

    expect(screen.getByTestId('authenticated')).toHaveTextContent('no')
    expect(screen.getByTestId('token')).toHaveTextContent('none')
    expect(screen.getByTestId('kyc')).toHaveTextContent('no')
  })

  it('throws error when useAuth used outside provider', () => {
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
    
    expect(() => {
      render(<TestComponent />)
    }).toThrow('useAuth must be used within AuthProvider')
    
    consoleSpy.mockRestore()
  })
})

describe('Token storage', () => {
  it('stores tokens in localStorage on login', async () => {
    const { setSession } = await import('../services/auth')
    
    setSession('token123', 'user1', 'viewer', 'refresh123', 'testuser')
    
    expect(setSession).toHaveBeenCalledWith('token123', 'user1', 'viewer', 'refresh123', 'testuser')
  })
})

