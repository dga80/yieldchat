import React, { useState, useEffect, useCallback, useRef } from 'react'
import {
  Wifi,
  WifiOff,
  RefreshCw,
  CheckCircle2,
  AlertTriangle,
  Cloud,
  CloudOff,
  X
} from 'lucide-react'

const API_BASE = import.meta.env.VITE_API_URL || '/api'

export default function ConnectionBadge({ onStatusChange }) {
  const [status, setStatus] = useState('checking') // 'checking' | 'connected' | 'waking_up' | 'disconnected'
  const [latency, setLatency] = useState(null)
  const [lastCheck, setLastCheck] = useState(null)
  const [isRetrying, setIsRetrying] = useState(false)
  const [showModal, setShowModal] = useState(false)
  const slowTimerRef = useRef(null)

  const checkConnection = useCallback(async (isManual = false) => {
    if (isManual) setIsRetrying(true)

    // Si tarda más de 2.5s en responder, Render está arrancando del modo reposo (cold start)
    slowTimerRef.current = setTimeout(() => {
      setStatus(prev => prev !== 'connected' ? 'waking_up' : prev)
    }, 2500)

    const startTime = performance.now()
    try {
      const res = await fetch(`${API_BASE}/status`, { cache: 'no-store' })
      clearTimeout(slowTimerRef.current)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      const duration = Math.round(performance.now() - startTime)
      setLatency(duration)
      setStatus('connected')
      setLastCheck(new Date())
      if (onStatusChange) onStatusChange(data)
    } catch (err) {
      clearTimeout(slowTimerRef.current)
      console.warn('[YieldChat] Status check failed:', err)
      setStatus('disconnected')
      setLatency(null)
      setLastCheck(new Date())
    } finally {
      if (isManual) {
        setTimeout(() => setIsRetrying(false), 400)
      }
    }
  }, [onStatusChange])

  useEffect(() => {
    checkConnection()

    const interval = setInterval(() => {
      checkConnection()
    }, 15000)

    const handleResume = () => {
      if (document.visibilityState === 'visible') {
        checkConnection()
      }
    }

    window.addEventListener('online', () => checkConnection(true))
    window.addEventListener('offline', () => setStatus('disconnected'))
    window.addEventListener('focus', handleResume)
    document.addEventListener('visibilitychange', handleResume)

    return () => {
      clearInterval(interval)
      clearTimeout(slowTimerRef.current)
      window.removeEventListener('focus', handleResume)
      document.removeEventListener('visibilitychange', handleResume)
    }
  }, [checkConnection])

  const isRender = API_BASE.includes('onrender.com')

  return (
    <>
      {/* 1. Header Pill */}
      <button
        type="button"
        className={`yc-conn-pill yc-conn-pill-${status}`}
        onClick={() => setShowModal(true)}
        title="Ver estado de conexión con el servidor en la nube"
        aria-label="Estado de conexión"
      >
        <span className={`yc-conn-dot yc-dot-${status}`} />
        <span className="yc-conn-text-desktop">
          {status === 'connected' && `Online ${latency != null ? `(${latency}ms)` : ''}`}
          {status === 'waking_up' && 'Despertando servidor...'}
          {status === 'checking' && 'Comprobando...'}
          {status === 'disconnected' && 'Sin conexión'}
        </span>
        <span className="yc-conn-text-mobile">
          {status === 'connected' && `Online ${latency != null ? `${latency}ms` : ''}`}
          {status === 'waking_up' && 'Iniciando (~30s)'}
          {status === 'checking' && 'Verificando'}
          {status === 'disconnected' && 'Offline'}
        </span>
      </button>

      {/* 2. Top notification banner if Render is waking up */}
      {status === 'waking_up' && (
        <div className="yc-waking-banner">
          <div className="yc-waking-content">
            <RefreshCw size={14} className="yc-spin" />
            <span>
              <strong>Despertando el servidor en la nube:</strong> Render está iniciando el backend tras unos minutos de inactividad (~30s). En cuanto el indicador se ponga verde podrás chatear.
            </span>
          </div>
        </div>
      )}

      {/* 3. Disconnection banner */}
      {status === 'disconnected' && (
        <div className="yc-waking-banner yc-banner-error">
          <div className="yc-waking-content">
            <AlertTriangle size={14} />
            <span>
              <strong>Servidor no accesible:</strong> Comprueba tu conexión a internet o pulsa para reintentar.
            </span>
          </div>
          <button
            type="button"
            className="yc-retry-inline-btn"
            onClick={() => checkConnection(true)}
          >
            Reintentar
          </button>
        </div>
      )}

      {/* 4. Diagnostic Modal */}
      {showModal && (
        <div className="yc-modal-backdrop" onClick={() => setShowModal(false)}>
          <div className="yc-modal-card" onClick={e => e.stopPropagation()}>
            <div className="yc-modal-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <div className={`yc-modal-icon icon-${status}`}>
                  {status === 'connected' ? <CheckCircle2 size={20} /> : <CloudOff size={20} />}
                </div>
                <div>
                  <h3 className="yc-modal-title">Estado de Conexión</h3>
                  <p className="yc-modal-subtitle">YieldChat Cloud Architecture</p>
                </div>
              </div>
              <button
                type="button"
                className="yc-modal-close"
                onClick={() => setShowModal(false)}
                aria-label="Cerrar"
              >
                <X size={18} />
              </button>
            </div>

            <div className="yc-diag-rows">
              <div className="yc-diag-item">
                <span className="yc-diag-title">Backend en la Nube</span>
                <span className={`yc-status-badge tag-${status}`}>
                  {status === 'connected' && 'Activo y Respondiendo'}
                  {status === 'waking_up' && 'Iniciando contenedor (Render)'}
                  {status === 'checking' && 'Comprobando conexión...'}
                  {status === 'disconnected' && 'Sin respuesta'}
                </span>
              </div>

              {latency != null && (
                <div className="yc-diag-item">
                  <span className="yc-diag-title">Latencia de Red</span>
                  <span className="yc-diag-val">{latency} ms</span>
                </div>
              )}

              <div className="yc-diag-item col-span">
                <span className="yc-diag-title">URL del Servidor</span>
                <code className="yc-url-code">{API_BASE}</code>
                <span className="yc-diag-hint">
                  {isRender ? 'Alojado 24/7 en Render (No necesita el Mac encendido)' : 'Servidor local en desarrollo'}
                </span>
              </div>
            </div>

            <div style={{ margin: '16px 0 16px 0' }}>
              <button
                type="button"
                className="yc-retry-big-btn"
                onClick={() => checkConnection(true)}
                disabled={isRetrying}
              >
                <RefreshCw size={15} className={isRetrying ? 'yc-spin' : ''} />
                <span>{isRetrying ? 'Comprobando respuesta...' : 'Comprobar conexión ahora'}</span>
              </button>
              {lastCheck && (
                <p className="yc-last-check">
                  Última verificación: {lastCheck.toLocaleTimeString()}
                </p>
              )}
            </div>

            <div className="yc-info-box">
              <p>
                💡 <strong>¿Funciona con el Mac apagado?</strong>
              </p>
              <p style={{ marginTop: 4, fontSize: '12px', color: '#94a3b8', lineHeight: 1.5 }}>
                ¡Sí! YieldChat corre en los servidores de Render y GitHub Pages. Tu Mac puede estar completamente apagado. Además, el ping automático de GitHub Actions mantiene el servicio activo las 24 horas.
              </p>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 14 }}>
              <button
                type="button"
                className="yc-close-btn"
                onClick={() => setShowModal(false)}
              >
                Cerrar
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
