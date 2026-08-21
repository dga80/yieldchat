import React from 'react'
import { Plus, Trash2, Brain, Sparkles, Youtube, Layers } from 'lucide-react'

export default function Sidebar({
  sessions,
  activeSessionId,
  onSelectSession,
  onNewChat,
  onDeleteSession,
  onOpenMemory,
  status
}) {
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

        <div className="model-badge">
          <div className="pulse-dot" />
          <span>{status?.active_gemini_model || 'Gemini Flash'}</span>
        </div>
      </div>
    </aside>
  )
}
