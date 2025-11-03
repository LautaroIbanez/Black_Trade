import { useEffect, useState } from 'react'
import { getLiveRecommendations } from '../services/api'
import { ensureSession, refreshAccessToken, getUserId } from '../services/auth'

export function useRecommendations(profile: string = 'balanced') {
  const [items, setItems] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [kycBlocked, setKycBlocked] = useState(false)

  const load = async () => {
    setLoading(true)
    setError(null)
    try {
      const ok = await ensureSession()
      if (!ok) throw new Error('No autenticado')
      const res = await getLiveRecommendations(profile)
      setItems(res.items || [])
      setKycBlocked(false)
    } catch (e: any) {
      if (e.status === 403 || e.message?.includes('KYC verification required')) {
        setKycBlocked(true)
        setError('Verificación KYC requerida')
      } else if (e.status === 401) {
        const refreshed = await refreshAccessToken()
        if (refreshed) {
          load()
          return
        }
        setError(e?.message || 'Error de autenticación')
      } else {
        setError(e?.message || 'Error cargando recomendaciones')
      }
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    const iv = setInterval(load, 30000)
    return () => clearInterval(iv)
  }, [profile])

  return { items, loading, error, kycBlocked, reload: load }
}


