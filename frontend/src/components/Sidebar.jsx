import React from 'react'
import { Plus, Trash2, Brain, Sparkles, CloudUpload, RefreshCw, CheckCircle2, AlertCircle } from 'lucide-react'

export default function Sidebar({
  sessions,
  activeSessionId,
  onSelectSession,
  onNewChat,
  onDeleteSession,
  onOpenMemory,
  onSyncGitHub,
  syncing,
  syncStatus,
  status
}) {
  const isSynced = syncStatus?.is_synced && !syncStatus?.has_pending_changes
  const hasPending = syncStatus?.has_pending_changes

  return (
    <aside className="sidebar">
      {/* Header / Brand */}
      <div className="sidebar-header">
        <div className="app-brand">
          <div className="brand-icon">
            <Sparkles size={16} />
          </div>
          <span>YieldChat</span>
        </div>
        <span className="brand-tag">AGENTE IA</span>
      </div>

      {/* New Chat Action */}
      <button className="new-chat-btn" onClick={onNewChat}>
        <Plus size={16} />
        <span>Nueva Conversación</span>
      </button>

      {/* Sessions List */}
      <div className="session-list">
        {sessions.map(s => {
          const isActive = s.id === activeSessionId
          return (
            <div
              key={s.id}
              className={`session-item ${isActive ? 'active' : ''}`}
              onClick={() => onSelectSession(s.id)}
            >
              <span className="session-title" title={s.title}>
                {s.title}
              </span>
              <button
                className="delete-session-btn"
                onClick={(e) => {
                  e.stopPropagation()
                  onDeleteSession(s.id)
                }}
                title="Eliminar conversación"
              >
                <Trash2 size={13} />
              </button>
            </div>
          )
        })}
      </div>

      {/* Footer / Long-term Memory & Status */}
      <div className="sidebar-footer">
        <button className="memory-btn" onClick={onOpenMemory}>
          <Brain size={15} style={{ color: 'var(--gold)' }} />
          <span>Memoria del Agente</span>
        </button>

        <button 
          className={`memory-btn sync-btn ${hasPending ? 'has-pending' : ''}`} 
          onClick={onSyncGitHub} 
          disabled={syncing}
          title={
            syncing 
              ? 'Sincronizando con GitHub...' 
              : hasPending 
                ? 'Hay cambios locales sin subir. Clic para sincronizar ahora (o espera el auto-sync cada 5 min).' 
                : 'La memoria y los chats están 100% actualizados en GitHub.'
          }
          style={{ 
            opacity: syncing ? 0.8 : 1,
            borderColor: hasPending ? 'rgba(234, 179, 8, 0.4)' : isSynced ? 'rgba(34, 197, 94, 0.25)' : 'var(--border)'
          }}
        >
          {syncing ? (
            <RefreshCw size={14} className="spin-icon" style={{ color: '#38BDF8' }} />
          ) : isSynced ? (
            <CheckCircle2 size={14} style={{ color: 'var(--green)' }} />
          ) : hasPending ? (
            <CloudUpload size={14} style={{ color: 'var(--gold)' }} />
          ) : (
            <CloudUpload size={14} style={{ color: '#38BDF8' }} />
          )}

          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', flex: 1 }}>
            <span style={{ fontSize: '12px', color: isSynced ? 'var(--green)' : hasPending ? 'var(--gold)' : 'var(--text-main)' }}>
              {syncing 
                ? 'Sincronizando...' 
                : isSynced 
                  ? 'GitHub al día' 
                  : 'Subir a GitHub'}
            </span>
            <span style={{ fontSize: '9.5px', color: 'var(--text-dim)', fontWeight: 400 }}>
              {syncing ? 'Subiendo cambios...' : hasPending ? 'Cambios pendientes' : 'Auto-sync (5 min)'}
            </span>
          </div>
        </button>

        <div className="model-badge">
          <div className="pulse-dot" />
          <span>{status?.active_gemini_model || 'Gemini Flash'}</span>
        </div>
      </div>
    </aside>
  )
}
