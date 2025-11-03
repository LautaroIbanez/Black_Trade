import React, { useState, useEffect } from 'react'
import { loginUser, registerUser, checkKYCStatus, verifyKYC } from '../services/api'
import { setSession, getUserId, getUsername, getToken } from '../services/auth'

type Props = { children: React.ReactNode }

function AuthGate({ children }: Props) {
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [country, setCountry] = useState('AR')
  const [loading, setLoading] = useState(false)
  const [needsKYC, setNeedsKYC] = useState(false)
  const [userId, setUserId] = useState<string | null>(null)
  const [kycDocs, setKycDocs] = useState({ document_type: 'passport', document_number: '' })
  const token = typeof window !== 'undefined' ? getToken() : null

  useEffect(() => {
    const check = async () => {
      const uid = getUserId()
      if (uid) {
        setUserId(uid)
        try {
          const status = await checkKYCStatus(uid)
          if (!status.verified) {
            setNeedsKYC(true)
          }
        } catch {}
      }
    }
    if (token) check()
  }, [token])

  const onLogin = async () => {
    setLoading(true)
    try {
      const res = await loginUser({ username, role: 'viewer' })
      setSession(res.access_token, res.user_id, res.role, res.refresh_token, username)
      setUserId(res.user_id)
      try {
        const kycStatus = await checkKYCStatus(res.user_id)
        if (!kycStatus.verified) {
          setNeedsKYC(true)
        }
      } catch {}
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
      setUserId(res.user_id)
      alert('Registro exitoso. Verifique KYC para acceder a datos protegidos.')
      setNeedsKYC(true)
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
      setNeedsKYC(false)
    } catch (e: any) {
      alert(e.message || 'Error verificando KYC')
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

  if (needsKYC) {
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


