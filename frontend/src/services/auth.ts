// Simple token persistence and helpers

const TOKEN_KEY = 'bt_auth_token'
const USER_ID_KEY = 'bt_user_id'
const ROLE_KEY = 'bt_user_role'

export function setSession(token: string, userId?: string, role?: string) {
  try {
    localStorage.setItem(TOKEN_KEY, token)
    if (userId) localStorage.setItem(USER_ID_KEY, userId)
    if (role) localStorage.setItem(ROLE_KEY, role)
  } catch {}
}

export function clearSession() {
  try {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_ID_KEY)
    localStorage.removeItem(ROLE_KEY)
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

export function authHeader(): Record<string, string> {
  const t = getToken()
  return t ? { 'Authorization': `Bearer ${t}` } : {}
}

// Optional: naive refresh placeholder (no backend refresh endpoint provided)
export async function ensureSession(): Promise<boolean> {
  return !!getToken()
}


