import React, { useState } from 'react'
import { X, Trash2, Plus, Brain, CloudUpload, RefreshCw, CheckCircle2 } from 'lucide-react'

export default function MemoryModal({ isOpen, onClose, insights, onAddInsight, onDeleteInsight, onSyncGitHub, syncing, syncStatus }) {
  const [categoria, setCategoria] = useState('CANAL')
  const [regla, setRegla] = useState('')

  const isSynced = syncStatus?.is_synced && !syncStatus?.has_pending_changes
  const hasPending = syncStatus?.has_pending_changes

  if (!isOpen) return null

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!regla.trim()) return
    onAddInsight({ categoria, regla: regla.trim() })
    setRegla('')
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Brain size={18} style={{ color: 'var(--gold)' }} />
            <h3 style={{ fontSize: '15px', fontWeight: 600 }}>Memoria a Largo Plazo del Agente</h3>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <button
              onClick={onSyncGitHub}
              disabled={syncing}
              style={{
                background: '#121824',
                border: `1px solid ${hasPending ? 'rgba(234, 179, 8, 0.4)' : isSynced ? 'rgba(34, 197, 94, 0.25)' : '#1E293B'}`,
                color: isSynced ? 'var(--green)' : hasPending ? 'var(--gold)' : '#38BDF8',
                borderRadius: 'var(--radius-sm)',
                padding: '5px 10px',
                fontSize: '11.5px',
                fontWeight: 600,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: 6
              }}
              title="Guardar y subir memoria a GitHub"
            >
              {syncing ? (
                <RefreshCw size={12} className="spin-icon" />
              ) : isSynced ? (
                <CheckCircle2 size={13} style={{ color: 'var(--green)' }} />
              ) : (
                <CloudUpload size={13} />
              )}
              <span>{syncing ? 'Sincronizando...' : isSynced ? 'GitHub al día' : 'Subir a GitHub'}</span>
            </button>
            <button
              onClick={onClose}
              style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}
            >
              <X size={18} />
            </button>
          </div>
        </div>

        <div className="modal-body">
          <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: 8 }}>
            Estas reglas y preferencias se inyectan automáticamente en todas tus conversaciones. El agente las recuerda permanentemente.
          </p>

          {/* Add New Insight Form */}
          <form onSubmit={handleSubmit} className="memory-add-form">
            <select
              value={categoria}
              onChange={e => setCategoria(e.target.value)}
              className="memory-select"
            >
              <option value="CANAL">CANAL</option>
              <option value="FORMATO_GUION">GUION</option>
              <option value="MINIATURAS">MINIATURAS</option>
              <option value="EDICION">EDICION</option>
              <option value="PREFERENCIA">PREFERENCIA</option>
            </select>
            <input
              type="text"
              placeholder="Escribe una regla o aprendizaje..."
              value={regla}
              onChange={e => setRegla(e.target.value)}
              className="memory-input"
            />
            <button
              type="submit"
              className="memory-submit-btn"
            >
              <Plus size={14} /> Añadir
            </button>
          </form>

          {/* List of Insights */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {insights.length === 0 ? (
              <p style={{ color: 'var(--text-dim)', fontSize: '13px', textAlign: 'center', padding: '20px 0' }}>
                No hay reglas guardadas todavía.
              </p>
            ) : (
              insights.map(item => (
                <div key={item.id} className="insight-card">
                  <div style={{ flex: 1 }}>
                    <span className="insight-category">{item.categoria}</span>
                    <div className="insight-text">{item.regla}</div>
                  </div>
                  <button
                    onClick={() => onDeleteInsight(item.id)}
                    style={{ background: 'none', border: 'none', color: 'var(--text-dim)', cursor: 'pointer' }}
                    title="Eliminar regla"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
