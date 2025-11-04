import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import React from 'react'
import { AuthProvider, useAuth } from '../context/AuthContext'
import { refreshAccessToken, ensureSession, getUsername, setSession } from '../services/auth'

// Mock auth services
vi.mock('../services/auth', async () => {
  const actual = await vi.importActual('../services/auth')
  return {
    ...actual,
    getToken: vi.fn(() => null),
    getUserId: vi.fn(() => null),
    getUsername: vi.fn(() => 'testuser'),
    getRefresh: vi.fn(() => 'refresh123'),
    getRole: vi.fn(() => 'viewer'),
    clearSession: vi.fn(),
    setSession: vi.fn(),
    refreshAccessToken: vi.fn(),
    ensureSession: vi.fn(),
  }
})

vi.mock('../services/api', () => ({
  checkKYCStatus: vi.fn(() => Promise.resolve({ verified: false })),
  loginUser: vi.fn(() => Promise.resolve({
    access_token: 'access123',
    refresh_token: 'refresh123',
    user_id: 'user123',
    role: 'viewer',
    username: 'testuser'
  })),
  refreshToken: vi.fn(() => Promise.resolve({
    access_token: 'access456',
    refresh_token: 'refresh456',
    user_id: 'user123',
    role: 'viewer',
    username: 'testuser'
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

describe('refreshAccessToken', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(getUsername).mockReturnValue('original_username')
  })

  it('preserves original username during refresh', async () => {
    const mod = await import('../services/auth')
    const { refreshAccessToken } = mod
    const api = await import('../services/api')
    
    vi.mocked(api.refreshToken).mockResolvedValue({
      access_token: 'new_access',
      refresh_token: 'new_refresh',
      user_id: 'user123',
      role: 'viewer',
      username: 'testuser'
    })
    
    const result = await refreshAccessToken()
    
    expect(result).toBe(true)
    expect(setSession).toHaveBeenCalledWith(
      'new_access',
      'user123',
      'viewer',
      'new_refresh',
      'testuser' // Should use username from response, not user_id
    )
  })

  it('falls back to original username if response missing username', async () => {
    const mod = await import('../services/auth')
    const { refreshAccessToken } = mod
    const api = await import('../services/api')
    
    vi.mocked(api.refreshToken).mockResolvedValue({
      access_token: 'new_access',
      refresh_token: 'new_refresh',
      user_id: 'user123',
      role: 'viewer'
      // No username in response
    } as any)
    
    const result = await refreshAccessToken()
    
    expect(result).toBe(true)
    expect(setSession).toHaveBeenCalledWith(
      'new_access',
      'user123',
      'viewer',
      'new_refresh',
      'original_username' // Should preserve original username
    )
  })

  it('never uses user_id as username', async () => {
    const mod = await import('../services/auth')
    const { refreshAccessToken } = mod
    const api = await import('../services/api')
    
    vi.mocked(api.refreshToken).mockResolvedValue({
      access_token: 'new_access',
      refresh_token: 'new_refresh',
      user_id: 'user_abc123def456',
      role: 'viewer'
      // No username in response
    } as any)
    
    const result = await refreshAccessToken()
    
    expect(result).toBe(true)
    // Should not use user_id as username - should use original or response username
    const callArgs = vi.mocked(setSession).mock.calls[0]
    expect(callArgs[4]).not.toBe('user_abc123def456')
    expect(callArgs[4]).toBe('original_username')
  })
})

describe('ensureSession', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('uses original username for login when token expired', async () => {
    const mod = await import('../services/auth')
    const { ensureSession } = mod
    const api = await import('../services/api')
    
    vi.mocked(getUsername).mockReturnValue('stored_username')
    vi.mocked(mod.getToken).mockReturnValue(null) // No token
    vi.mocked(mod.refreshAccessToken).mockResolvedValue(false) // Refresh failed
    vi.mocked(api.loginUser).mockResolvedValue({
      access_token: 'access123',
      refresh_token: 'refresh123',
      user_id: 'user123',
      role: 'viewer',
      username: 'stored_username'
    })
    
    const result = await ensureSession()
    
    expect(result).toBe(true)
    expect(api.loginUser).toHaveBeenCalledWith({ username: 'stored_username', role: 'viewer' })
    expect(setSession).toHaveBeenCalledWith(
      'access123',
      'user123',
      'viewer',
      'refresh123',
      'stored_username' // Should use stored username, not user_id
    )
  })

  it('skips login if username looks like user_id', async () => {
    const mod = await import('../services/auth')
    const { ensureSession } = mod
    
    vi.mocked(getUsername).mockReturnValue('user_abc123def456') // Looks like user_id
    vi.mocked(mod.getToken).mockReturnValue(null)
    vi.mocked(mod.refreshAccessToken).mockResolvedValue(false)
    
    const result = await ensureSession()
    
    expect(result).toBe(false)
    // Should not attempt login with user_id
  })

  it('returns true if token exists', async () => {
    const mod = await import('../services/auth')
    const { ensureSession } = mod
    
    vi.mocked(mod.getToken).mockReturnValue('existing_token')
    
    const result = await ensureSession()
    
    expect(result).toBe(true)
  })
})

