import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react'
import { getToken, getUserId, getUsername, clearSession, refreshAccessToken } from '../services/auth'
import { checkKYCStatus } from '../services/api'

interface AuthState {
  isAuthenticated: boolean
  token: string | null
  userId: string | null
  username: string | null
  isKYCVerified: boolean
  loading: boolean
}

interface AuthContextType extends AuthState {
  logout: () => void
  retryProtectedCall: <T>(fn: () => Promise<T>, retries?: number) => Promise<T>
  refreshAuthState: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return context
}

interface AuthProviderProps {
  children: ReactNode
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [authState, setAuthState] = useState<AuthState>({
    isAuthenticated: false,
    token: null,
    userId: null,
    username: null,
    isKYCVerified: false,
    loading: true,
  })

  const refreshAuthState = useCallback(async () => {
    const token = getToken()
    const userId = getUserId()
    const username = getUsername()
    
    if (!token || !userId) {
      setAuthState({
        isAuthenticated: false,
        token: null,
        userId: null,
        username: null,
        isKYCVerified: false,
        loading: false,
      })
      return
    }

    let isKYCVerified = false
    try {
      const status = await checkKYCStatus(userId)
      isKYCVerified = status.verified
    } catch {}

    setAuthState({
      isAuthenticated: true,
      token,
      userId,
      username,
      isKYCVerified,
      loading: false,
    })
  }, [])

  useEffect(() => {
    refreshAuthState()
  }, [refreshAuthState])

  const logout = useCallback(() => {
    clearSession()
    setAuthState({
      isAuthenticated: false,
      token: null,
      userId: null,
      username: null,
      isKYCVerified: false,
      loading: false,
    })
  }, [])

  const retryProtectedCall = useCallback(async <T,>(fn: () => Promise<T>, retries = 1): Promise<T> => {
    try {
      return await fn()
    } catch (error: any) {
      if (error.status === 401 && retries > 0) {
        const refreshed = await refreshAccessToken()
        if (refreshed) {
          await refreshAuthState()
          return retryProtectedCall(fn, retries - 1)
        }
      }
      throw error
    }
  }, [refreshAuthState])

  return (
    <AuthContext.Provider value={{ ...authState, logout, retryProtectedCall, refreshAuthState }}>
      {children}
    </AuthContext.Provider>
  )
}

