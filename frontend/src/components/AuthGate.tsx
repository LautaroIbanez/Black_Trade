import React, { useState, useEffect } from 'react'
import { loginUser, registerUser, checkKYCStatus, verifyKYC } from '../services/api'
import { setSession, getUserId, getUsername } from '../services/auth'
import { useAuth } from '../context/AuthContext'

type Props = { children: React.ReactNode }

function AuthGate({ children }: Props) {
  const { isAuthenticated, isKYCVerified, userId, refreshAuthState } = useAuth()
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [country, setCountry] = useState('AR')
  const [loading, setLoading] = useState(false)
  const [kycDocs, setKycDocs] = useState({ document_type: 'passport', document_number: '' })

  const onLogin = async () => {
    setLoading(true)
    try {
      const res = await loginUser({ username, role: 'viewer' })
      setSession(res.access_token, res.user_id, res.role, res.refresh_token, username)
      await refreshAuthState()
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
      alert('Registro exitoso. Verifique KYC para acceder a datos protegidos.')
      await refreshAuthState()
    } catch (e: any) {
      alert(e.message)
    } finally {
      setLoading(false)
    }
  }

  const onVerifyKYC = async () => {
    if (!userId) return
    setLoading(true)
    try {
      await verifyKYC({ user_id: userId, ...kycDocs })
      alert('KYC verificado exitosamente')
      await refreshAuthState()
    } catch (e: any) {
      alert(e.message || 'Error verificando KYC')
    } finally {
      setLoading(false)
    }
  }

  if (!isAuthenticated) {
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

  if (!isKYCVerified) {
    return (
      <div className="auth-gate">
        <h3>Verificación KYC requerida</h3>
        <p>Complete su verificación para acceder a recomendaciones y métricas de riesgo.</p>
        <div className="row">
          <select value={kycDocs.document_type} onChange={e => setKycDocs({ ...kycDocs, document_type: e.target.value })}>
            <option value="passport">Passport</option>
            <option value="id">ID</option>
            <option value="driver_license">Driver License</option>
          </select>
          <input placeholder="Documento" value={kycDocs.document_number} onChange={e => setKycDocs({ ...kycDocs, document_number: e.target.value })} />
          <button onClick={onVerifyKYC} disabled={loading || !kycDocs.document_number}>Verificar</button>
        </div>
      </div>
    )
  }

  return <>{children}</>
}

export default AuthGate


