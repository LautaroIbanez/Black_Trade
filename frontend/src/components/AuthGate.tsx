import React, { useState } from 'react'
import { loginUser, registerUser } from '../services/api'
import { setSession, getUserId } from '../services/auth'

type Props = { children: React.ReactNode }

function AuthGate({ children }: Props) {
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [country, setCountry] = useState('AR')
  const [loading, setLoading] = useState(false)
  const token = typeof window !== 'undefined' ? localStorage.getItem('bt_auth_token') : null

  const onLogin = async () => {
    setLoading(true)
    try {
      const res = await loginUser({ username, role: 'viewer' })
      setSession(res.access_token, res.user_id, res.role, res.refresh_token, username)
    } catch (e: any) {
      alert(e.message)
    } finally {
      setLoading(false)
    }
  }

  const onRegister = async () => {
    setLoading(true)
    try {
      const res = await registerUser({ username, email, country, role: 'viewer' })
      setSession(res.access_token, res.user_id, res.role, res.refresh_token, username)
      alert('Registro exitoso. Proceda a verificar KYC si es necesario.')
    } catch (e: any) {
      alert(e.message)
    } finally {
      setLoading(false)
    }
  }

  if (!token) {
    return (
      <div className="auth-gate">
        <h3>Inicie sesión para ver datos protegidos</h3>
        <div className="row">
          <input placeholder="Usuario" value={username} onChange={e => setUsername(e.target.value)} />
          <button onClick={onLogin} disabled={loading || !username}>Login</button>
        </div>
        <div className="row">
          <input placeholder="Email" value={email} onChange={e => setEmail(e.target.value)} />
          <input placeholder="País" value={country} onChange={e => setCountry(e.target.value)} />
          <button onClick={onRegister} disabled={loading || !username || !email}>Registrar</button>
        </div>
      </div>
    )
  }

  return <>{children}</>
}

export default AuthGate


