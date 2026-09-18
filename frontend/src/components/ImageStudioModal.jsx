import React, { useState, useEffect } from 'react'
import {
  X,
  Sparkles,
  Download,
  Image as ImageIcon,
  Folder,
  Maximize2,
  Trash2,
  Copy,
  ExternalLink,
  Layers,
  Check,
  RefreshCw,
  Wand2
} from 'lucide-react'
import toast from 'react-hot-toast'

const API_BASE = import.meta.env.VITE_API_URL || '/api'

const PROMPT_TEMPLATES = [
  { label: 'Nebulosa Cósmica', text: 'Una persona en silueta meditando bajo una nebulosa cósmica púrpura y dorada, cielo estrellado profundo, atmósfera zen' },
  { label: 'Catedral en la Niebla', text: 'Catedral antigua gótica en la niebla matutina, arquitectura serena de piedra, rayos de luz suave filtrándose, paz estática' },
  { label: 'Mecánica & Reloj', text: 'Primer plano macro de engranajes antiguos de madera y bronce entrelazados en perfecta armonía, iluminación cinematográfica' },
  { label: 'Rincón de Lectura', text: 'Taza de té caliente humeante junto a libros antiguos en una ventana de madera con lluvia suave, estilo Studio Ghibli' }
]

export default function ImageStudioModal({
  isOpen,
  onClose,
  folders = [],
  activeFolderId = null,
  activeSessionId = null
}) {
  const [selectedFolderId, setSelectedFolderId] = useState(activeFolderId || '')
  const [prompt, setPrompt] = useState('')
  const [aspectRatio, setAspectRatio] = useState('16:9')
  const [model, setModel] = useState('google-banana')
  const [loading, setLoading] = useState(false)
  const [gallery, setGallery] = useState([])
  const [loadingGallery, setLoadingGallery] = useState(false)
  const [visualContext, setVisualContext] = useState(null)
  const [lightboxImg, setLightboxImg] = useState(null)
  const [copiedId, setCopiedId] = useState(null)

  // Sincronizar carpeta activa cuando cambie
  useEffect(() => {
    if (activeFolderId) {
      setSelectedFolderId(activeFolderId)
    }
  }, [activeFolderId])

  // Cargar galería y contexto visual cuando cambie la carpeta seleccionada o al abrir modal
  useEffect(() => {
    if (!isOpen) return
    loadVisualContext(selectedFolderId)
    loadGallery(selectedFolderId)
  }, [isOpen, selectedFolderId])

  const loadVisualContext = async (folderId) => {
    try {
      const url = folderId
        ? `${API_BASE}/images/context?folder_id=${encodeURIComponent(folderId)}`
        : `${API_BASE}/images/context`
      const res = await fetch(url)
      if (res.ok) {
        const data = await res.json()
        setVisualContext(data)
      }
    } catch (e) {
      console.warn('Error loading visual context', e)
    }
  }

  const loadGallery = async (folderId) => {
    setLoadingGallery(true)
    try {
      const url = folderId
        ? `${API_BASE}/images/gallery?folder_id=${encodeURIComponent(folderId)}`
        : `${API_BASE}/images/gallery`
      const res = await fetch(url)
      if (res.ok) {
        const data = await res.json()
        setGallery(data)
      }
    } catch (e) {
      console.error('Error loading gallery', e)
    } finally {
      setLoadingGallery(false)
    }
  }

  const handleGenerate = async (e) => {
    e?.preventDefault()
    if (!prompt.trim()) {
      toast.error('Introduce una descripción para generar la imagen')
      return
    }

    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/images/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: prompt.trim(),
          folder_id: selectedFolderId || null,
          session_id: activeSessionId || null,
          aspect_ratio: aspectRatio,
          model: model
        })
      })

      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()

      if (data.status === 'success') {
        toast.success('¡Imagen generada con éxito!', { icon: '🎨' })
        setGallery(prev => [data, ...prev.filter(item => item.id !== data.id)])
      } else {
        toast.error('No se pudo generar la imagen')
      }
    } catch (e) {
      console.error('Error generating image', e)
      toast.error('Error de conexión al generar la imagen')
    } finally {
      setLoading(false)
    }
  }

  const handleDeleteImage = async (imgId) => {
    if (!window.confirm('¿Deseas eliminar esta imagen de la galería?')) return
    try {
      const res = await fetch(`${API_BASE}/images/${imgId}`, { method: 'DELETE' })
      if (res.ok) {
        setGallery(prev => prev.filter(img => img.id !== imgId))
        toast.success('Imagen eliminada')
      }
    } catch (e) {
      toast.error('Error al eliminar imagen')
    }
  }

  const handleDownload = async (img) => {
    const rawUrl = img.image_url || img.external_url
    const src = rawUrl?.startsWith('/api')
      ? `${API_BASE.replace(/\/api$/, '')}${rawUrl}`
      : rawUrl

    try {
      const response = await fetch(src)
      const blob = await response.blob()
      const blobUrl = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = blobUrl
      link.download = img.filename || `yieldchat_${Date.now()}.jpg`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(blobUrl)
      toast.success('Imagen descargada en HD')
    } catch (e) {
      toast.error('Error al descargar la imagen')
    }
  }

  const handleCopyPrompt = (text, id) => {
    navigator.clipboard.writeText(text)
    setCopiedId(id)
    toast.success('Prompt copiado')
    setTimeout(() => setCopiedId(null), 2000)
  }

  if (!isOpen) return null

  const activeFolder = folders.find(f => f.id === selectedFolderId)
  const channelName = activeFolder ? activeFolder.name : (visualContext?.channel_name || 'General')
  const visualRules = visualContext?.visual_rules || []

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content image-studio-modal" onClick={e => e.stopPropagation()}>
        {/* Header del Estudio */}
        <div className="modal-header image-studio-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div className="image-studio-brand-icon">
              <Sparkles size={18} />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <h3 style={{ fontSize: '15.5px', fontWeight: 700, color: 'var(--text-main)' }}>
                  Estudio de Imágenes & Miniaturas
                </h3>
                <span className="banana-engine-badge">
                  Google Banana / Flux
                </span>
              </div>
              <div style={{ fontSize: '11px', color: 'var(--text-dim)' }}>
                Generador visual de alta fidelidad con memoria de estilo por canal
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            {/* Selector de Carpeta/Canal */}
            <div className="image-studio-folder-picker">
              <Folder size={14} style={{ color: activeFolder?.color || 'var(--gold)' }} />
              <select
                value={selectedFolderId}
                onChange={e => setSelectedFolderId(e.target.value)}
                className="studio-folder-select"
              >
                <option value="">Todas las carpetas</option>
                {folders.map(f => (
                  <option key={f.id} value={f.id}>
                    {f.name}
                  </option>
                ))}
              </select>
            </div>

            <button
              onClick={onClose}
              className="modal-close-icon-btn"
              title="Cerrar Estudio"
            >
              <X size={18} />
            </button>
          </div>
        </div>

        {/* Cuerpo del Estudio */}
        <div className="image-studio-body">
          {/* Columna Izquierda: Formulario de Creación */}
          <div className="image-studio-creator-column">
            {/* Banner de Memoria Visual Activa del Canal */}
            <div className="channel-visual-memory-card">
              <div className="channel-memory-header">
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <Wand2 size={13} style={{ color: 'var(--gold)' }} />
                  <span style={{ fontSize: '11.5px', fontWeight: 600, color: 'var(--gold)' }}>
                    Memoria Visual de: {channelName}
                  </span>
                </div>
                <span style={{ fontSize: '10px', color: 'var(--text-dim)' }}>
                  Inyección automática de estilo
                </span>
              </div>
              {visualRules.length > 0 ? (
                <div className="channel-memory-tags">
                  {visualRules.slice(0, 3).map((rule, idx) => (
                    <span key={idx} className="channel-memory-tag" title={rule}>
                      {rule.length > 55 ? `${rule.slice(0, 55)}...` : rule}
                    </span>
                  ))}
                </div>
              ) : (
                <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                  Este canal utiliza optimización cinematográfica estándar. Añade reglas visuales a este canal para anclar estilos como Ghibli o Seinen.
                </div>
              )}
            </div>

            <form onSubmit={handleGenerate} className="studio-creation-form">
              {/* Textarea del Prompt */}
              <div className="studio-field-group">
                <label className="studio-field-label">
                  <span>Descripción de la escena o miniatura:</span>
                </label>
                <textarea
                  className="studio-prompt-input"
                  rows={4}
                  placeholder="Ej: Silueta de un viajero contemplando un agujero negro supermasivo en calma, partículas doradas, estética anime Studio Ghibli..."
                  value={prompt}
                  onChange={e => setPrompt(e.target.value)}
                  disabled={loading}
                />
              </div>

              {/* Plantillas / Atajos rápidos */}
              <div className="studio-templates-row">
                <span style={{ fontSize: '10.5px', color: 'var(--text-dim)' }}>Atajos:</span>
                {PROMPT_TEMPLATES.map((tmpl, idx) => (
                  <button
                    key={idx}
                    type="button"
                    className="studio-template-chip"
                    onClick={() => setPrompt(tmpl.text)}
                    disabled={loading}
                  >
                    {tmpl.label}
                  </button>
                ))}
              </div>

              {/* Controles de Ratio & Modelo */}
              <div className="studio-controls-grid">
                <div>
                  <label className="studio-field-label">
                    <span>Aspect Ratio (Formato):</span>
                  </label>
                  <div className="ratio-selector-group">
                    <button
                      type="button"
                      className={`ratio-btn ${aspectRatio === '16:9' ? 'active' : ''}`}
                      onClick={() => setAspectRatio('16:9')}
                    >
                      <span className="ratio-icon-box ratio-16-9" />
                      <span>16:9 (Vídeo / Miniatura)</span>
                    </button>
                    <button
                      type="button"
                      className={`ratio-btn ${aspectRatio === '9:16' ? 'active' : ''}`}
                      onClick={() => setAspectRatio('9:16')}
                    >
                      <span className="ratio-icon-box ratio-9-16" />
                      <span>9:16 (Shorts / Reels)</span>
                    </button>
                    <button
                      type="button"
                      className={`ratio-btn ${aspectRatio === '1:1' ? 'active' : ''}`}
                      onClick={() => setAspectRatio('1:1')}
                    >
                      <span className="ratio-icon-box ratio-1-1" />
                      <span>1:1 (Avatar / Cuadrada)</span>
                    </button>
                  </div>
                </div>
              </div>

              {/* Botón de Generación */}
              <button
                type="submit"
                className="studio-generate-btn"
                disabled={loading || !prompt.trim()}
              >
                {loading ? (
                  <>
                    <RefreshCw size={15} className="spin-icon" />
                    <span>Generando con Google Banana / Flux...</span>
                  </>
                ) : (
                  <>
                    <Sparkles size={16} />
                    <span>Generar Imagen con Memoria</span>
                  </>
                )}
              </button>
            </form>
          </div>

          {/* Columna Derecha: Galería de Creaciones del Canal */}
          <div className="image-studio-gallery-column">
            <div className="gallery-header-row">
              <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
                <Layers size={14} style={{ color: 'var(--gold)' }} />
                <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-main)' }}>
                  Creaciones de {channelName}
                </span>
                <span className="gallery-counter-badge">{gallery.length}</span>
              </div>
              {selectedFolderId && (
                <button
                  type="button"
                  className="gallery-view-all-btn"
                  onClick={() => setSelectedFolderId('')}
                >
                  Ver todas
                </button>
              )}
            </div>

            <div className="gallery-scroll-area">
              {loadingGallery ? (
                <div className="gallery-empty-state">
                  <RefreshCw size={20} className="spin-icon" style={{ color: 'var(--gold)' }} />
                  <span>Cargando galería del canal...</span>
                </div>
              ) : gallery.length === 0 ? (
                <div className="gallery-empty-state">
                  <ImageIcon size={32} style={{ color: 'var(--text-muted)', opacity: 0.5 }} />
                  <span style={{ fontWeight: 600, color: 'var(--text-main)', marginTop: 8 }}>
                    Aún no hay imágenes en {channelName}
                  </span>
                  <span style={{ fontSize: '11px', color: 'var(--text-dim)', maxWidth: '240px' }}>
                    Escribe una descripción en el panel de la izquierda para crear la primera miniatura o ilustración.
                  </span>
                </div>
              ) : (
                <div className="studio-gallery-grid">
                  {gallery.map(img => {
                    const rawUrl = img.image_url || img.external_url
                    const resolvedSrc = rawUrl?.startsWith('/api')
                      ? `${API_BASE.replace(/\/api$/, '')}${rawUrl}`
                      : rawUrl

                    return (
                      <div key={img.id} className="studio-gallery-card">
                        <div
                          className={`gallery-card-thumb-wrap ${img.aspect_ratio === '9:16' ? 'ratio-9-16-thumb' : img.aspect_ratio === '1:1' ? 'ratio-1-1-thumb' : 'ratio-16-9-thumb'}`}
                          onClick={() => setLightboxImg(resolvedSrc)}
                        >
                          <img
                            src={resolvedSrc}
                            alt={img.prompt}
                            loading="lazy"
                            className="gallery-card-img"
                          />
                          <div className="gallery-card-overlay">
                            <button
                              type="button"
                              className="gallery-overlay-btn"
                              title="Ver en tamaño completo"
                              onClick={(e) => {
                                e.stopPropagation()
                                setLightboxImg(resolvedSrc)
                              }}
                            >
                              <Maximize2 size={13} />
                            </button>
                            <button
                              type="button"
                              className="gallery-overlay-btn"
                              title="Descargar en alta calidad"
                              onClick={(e) => {
                                e.stopPropagation()
                                handleDownload(img)
                              }}
                            >
                              <Download size={13} />
                            </button>
                            <button
                              type="button"
                              className="gallery-overlay-btn"
                              title="Copiar prompt"
                              onClick={(e) => {
                                e.stopPropagation()
                                handleCopyPrompt(img.prompt, img.id)
                              }}
                            >
                              {copiedId === img.id ? <Check size={13} style={{ color: 'var(--green)' }} /> : <Copy size={13} />}
                            </button>
                            <button
                              type="button"
                              className="gallery-overlay-btn delete"
                              title="Eliminar de la galería"
                              onClick={(e) => {
                                e.stopPropagation()
                                handleDeleteImage(img.id)
                              }}
                            >
                              <Trash2 size={13} />
                            </button>
                          </div>
                        </div>

                        <div className="gallery-card-meta">
                          <div className="gallery-card-meta-top">
                            <span className="gallery-card-ratio-badge">{img.aspect_ratio || '16:9'}</span>
                            <span className="gallery-card-date">
                              {img.created_at ? new Date(img.created_at).toLocaleDateString() : ''}
                            </span>
                          </div>
                          <div className="gallery-card-prompt" title={img.prompt}>
                            {img.prompt}
                          </div>
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Lightbox / Visor Ampliado */}
      {lightboxImg && (
        <div className="lightbox-overlay" onClick={() => setLightboxImg(null)}>
          <div className="lightbox-content" onClick={e => e.stopPropagation()}>
            <button
              className="lightbox-close-btn"
              onClick={() => setLightboxImg(null)}
              title="Cerrar vista previa"
            >
              <X size={20} />
            </button>
            <img src={lightboxImg} alt="Vista previa completa" className="lightbox-image" />
            <div className="lightbox-footer">
              <a
                href={lightboxImg}
                target="_blank"
                rel="noopener noreferrer"
                className="lightbox-action-btn"
              >
                <ExternalLink size={14} />
                <span>Abrir original</span>
              </a>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
