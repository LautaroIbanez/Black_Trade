import { useEffect, useState } from 'react'
import { getRiskStatus } from '../services/api'
import { ensureSession } from '../services/auth'

export function useRiskData() {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = async () => {
    setLoading(true)
    setError(null)
    try {
      const ok = await ensureSession()
      if (!ok) throw new Error('No autenticado')
      const res = await getRiskStatus(null as any)
      setData(res)
    } catch (e: any) {
      setError(e?.message || 'Error cargando riesgo')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    const iv = setInterval(load, 30000)
    return () => clearInterval(iv)
  }, [])

  return { data, loading, error, reload: load }
}


