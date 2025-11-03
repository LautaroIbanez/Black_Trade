// Simple token persistence and helpers

const TOKEN_KEY = 'bt_auth_token'
const REFRESH_KEY = 'bt_refresh_token'
const USER_ID_KEY = 'bt_user_id'
const ROLE_KEY = 'bt_user_role'
const USERNAME_KEY = 'bt_username'

export function setSession(token: string, userId?: string, role?: string, refreshToken?: string, username?: string) {
  try {
    localStorage.setItem(TOKEN_KEY, token)
    if (userId) localStorage.setItem(USER_ID_KEY, userId)
    if (role) localStorage.setItem(ROLE_KEY, role)
    if (refreshToken) localStorage.setItem(REFRESH_KEY, refreshToken)
    if (username) localStorage.setItem(USERNAME_KEY, username)
  } catch {}
}

export function clearSession() {
  try {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(REFRESH_KEY)
    localStorage.removeItem(USER_ID_KEY)
    localStorage.removeItem(ROLE_KEY)
    localStorage.removeItem(USERNAME_KEY)
  } catch {}
}

export function getToken(): string | null {
  try { return localStorage.getItem(TOKEN_KEY) } catch { return null }
}

export function getUserId(): string | null {
  try { return localStorage.getItem(USER_ID_KEY) } catch { return null }
}

export function getRole(): string | null {
  try { return localStorage.getItem(ROLE_KEY) } catch { return null }
}

export function getUsername(): string | null {
  try { return localStorage.getItem(USERNAME_KEY) } catch { return null }
}

export function getRefresh(): string | null {
  try { return localStorage.getItem(REFRESH_KEY) } catch { return null }
}

export function authHeader(): Record<string, string> {
  const t = getToken()
  return t ? { 'Authorization': `Bearer ${t}` } : {}
}

// Optional: naive refresh placeholder (no backend refresh endpoint provided)
export async function ensureSession(): Promise<boolean> {
  if (getToken()) return true
  // Attempt naive renewal via login using stored username/role (since backend lacks /refresh endpoint)
  try {
    const username = getUsername()
    const role = getRole() || 'viewer'
    if (!username) return false
    const mod = await import('./api')
    const res = await mod.loginUser({ username, role })
    if (res?.access_token) {
      setSession(res.access_token, res.user_id, res.role, res.refresh_token, username)
      return true
    }
  } catch {}
  return false
}


