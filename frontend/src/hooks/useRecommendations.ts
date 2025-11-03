import { useEffect, useState } from 'react'
import { getLiveRecommendations } from '../services/api'
import { ensureSession } from '../services/auth'

export function useRecommendations(profile: string = 'balanced') {
  const [items, setItems] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = async () => {
    setLoading(true)
    setError(null)
    try {
      const ok = await ensureSession()
      if (!ok) throw new Error('No autenticado')
      const res = await getLiveRecommendations(profile)
      setItems(res.items || [])
    } catch (e: any) {
      setError(e?.message || 'Error cargando recomendaciones')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    const iv = setInterval(load, 30000)
    return () => clearInterval(iv)
  }, [profile])

  return { items, loading, error, reload: load }
}


