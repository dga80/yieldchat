import React, { useState, useEffect } from 'react'
import {
  Plus,
  Trash2,
  Brain,
  Sparkles,
  CloudUpload,
  RefreshCw,
  CheckCircle2,
  X,
  Folder,
  FolderPlus,
  FolderOpen,
  ChevronDown,
  ChevronRight,
  MoreVertical,
  Edit2,
  FolderInput,
  Search,
  Check,
  Clock,
  Calendar
} from 'lucide-react'
import { groupSessionsByDate, formatSessionDate } from '../utils/dateUtils'

const FOLDER_COLORS = [
  '#F59E0B', // Gold / Amber
  '#38BDF8', // Sky Blue
  '#10B981', // Emerald
  '#A855F7', // Purple
  '#EC4899', // Pink
  '#F97316', // Orange
  '#64748B'  // Slate
]

export default function Sidebar({
  sessions = [],
  folders = [],
  activeSessionId,
  onSelectSession,
  onNewChat,
  onDeleteSession,
  onCreateFolder,
  onUpdateFolder,
  onDeleteFolder,
  onMoveSessionToFolder,
  onOpenMemory,
  onSyncGitHub,
  syncing,
  syncStatus,
  status,
  isOpen,
  onClose,
  isLoadingSessions = false,
  sessionsError = false,
  onRetryLoadSessions
}) {
  const [viewMode, setViewMode] = useState(() => {
    try {
      return localStorage.getItem('yieldchat_sidebar_view') || 'date'
    } catch {
      return 'date'
    }
  })
  const [collapsedDateGroups, setCollapsedDateGroups] = useState(() => {
    try {
      const saved = localStorage.getItem('yieldchat_collapsed_date_groups')
      return saved ? JSON.parse(saved) : {}
    } catch {
      return {}
    }
  })
  const [collapsedFolders, setCollapsedFolders] = useState(() => {
    try {
      const saved = localStorage.getItem('yieldchat_collapsed_folders')
      return saved ? JSON.parse(saved) : {}
    } catch {
      return {}
    }
  })
  const [isCreatingFolder, setIsCreatingFolder] = useState(false)
  const [newFolderName, setNewFolderName] = useState('')
  const [newFolderColor, setNewFolderColor] = useState(FOLDER_COLORS[0])
  const [editingFolderId, setEditingFolderId] = useState(null)
  const [editingFolderName, setEditingFolderName] = useState('')
  const [activeMoveMenuSessionId, setActiveMoveMenuSessionId] = useState(null)
  const [activeFolderMenuId, setActiveFolderMenuId] = useState(null)
  const [searchQuery, setSearchQuery] = useState('')

  const isSynced = syncStatus?.is_synced && !syncStatus?.has_pending_changes
  const hasPending = syncStatus?.has_pending_changes

  // Cerrar menús flotantes al hacer clic fuera
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (!e.target.closest('.dropdown-wrapper') && !e.target.closest('.floating-menu')) {
        setActiveMoveMenuSessionId(null)
        setActiveFolderMenuId(null)
      }
    }
    window.addEventListener('click', handleClickOutside)
    return () => window.removeEventListener('click', handleClickOutside)
  }, [])

  // Asegurar que la carpeta que contiene la sesión activa esté siempre desplegada
  useEffect(() => {
    if (activeSessionId && folders.length > 0 && sessions.length > 0) {
      const activeSession = sessions.find(s => s.id === activeSessionId)
      if (activeSession?.folder_id && collapsedFolders[activeSession.folder_id]) {
        setCollapsedFolders(prev => {
          const next = { ...prev, [activeSession.folder_id]: false }
          try {
            localStorage.setItem('yieldchat_collapsed_folders', JSON.stringify(next))
          } catch (e) {}
          return next
        })
      }
    }
  }, [activeSessionId, sessions, folders])

  const handleSetViewMode = (mode) => {
    setViewMode(mode)
    try {
      localStorage.setItem('yieldchat_sidebar_view', mode)
    } catch (e) {
      console.error('Error saving sidebar view mode', e)
    }
  }

  const toggleDateGroupCollapse = (category) => {
    setCollapsedDateGroups(prev => {
      const next = { ...prev, [category]: !prev[category] }
      try {
        localStorage.setItem('yieldchat_collapsed_date_groups', JSON.stringify(next))
      } catch (e) {
        console.error('Error saving collapsed date groups', e)
      }
      return next
    })
  }

  const toggleFolderCollapse = (folderId) => {
    setCollapsedFolders(prev => {
      const next = { ...prev, [folderId]: !prev[folderId] }
      try {
        localStorage.setItem('yieldchat_collapsed_folders', JSON.stringify(next))
      } catch (e) {
        console.error('Error saving collapsed folders', e)
      }
      return next
    })
  }

  const handleStartCreateFolder = () => {
    setIsCreatingFolder(true)
    setNewFolderName('')
    setNewFolderColor(FOLDER_COLORS[0])
  }

  const handleSaveNewFolder = async (e) => {
    e?.preventDefault()
    if (!newFolderName.trim()) return
    await onCreateFolder(newFolderName.trim(), newFolderColor)
    setIsCreatingFolder(false)
    setNewFolderName('')
  }

  const handleStartEditFolder = (folder, e) => {
    e.stopPropagation()
    setEditingFolderId(folder.id)
    setEditingFolderName(folder.name)
    setActiveFolderMenuId(null)
  }

  const handleSaveEditFolder = async (folderId, currentColor) => {
    if (editingFolderName.trim()) {
      await onUpdateFolder(folderId, editingFolderName.trim(), currentColor)
    }
    setEditingFolderId(null)
  }

  // Filtrado por búsqueda
  const filteredSessions = searchQuery.trim()
    ? sessions.filter(s => s.title.toLowerCase().includes(searchQuery.toLowerCase()))
    : sessions

  // Agrupación cronológica por fechas (clasificación automática)
  const dateGroups = groupSessionsByDate(filteredSessions)

  // Agrupación por carpetas
  const uncategorizedSessions = filteredSessions.filter(
    s => !s.folder_id || !folders.some(f => f.id === s.folder_id)
  )

  return (
    <>
      <div 
        className={`sidebar-overlay ${isOpen ? 'open' : ''}`} 
        onClick={onClose}
        aria-hidden="true"
      />
      <aside className={`sidebar ${isOpen ? 'open' : 'closed'}`}>
        {/* Header / Brand */}
        <div className="sidebar-header">
          <div className="app-brand">
            <div className="brand-icon">
              <Sparkles size={16} />
            </div>
            <span>YieldChat</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span className="brand-tag">AGENTE IA</span>
            <button className="mobile-close-btn" onClick={onClose} title="Cerrar menú">
              <X size={18} />
            </button>
          </div>
        </div>

        {/* Action Buttons: New Chat & New Folder */}
        <div className="sidebar-actions-row">
          <button className="new-chat-btn" onClick={() => onNewChat()}>
            <Plus size={15} />
            <span>Nuevo Chat</span>
          </button>
          <button 
            className="new-folder-btn" 
            onClick={handleStartCreateFolder} 
            title="Crear nueva carpeta o tema"
          >
            <FolderPlus size={16} />
          </button>
        </div>

        {/* Inline Folder Creation Form */}
        {isCreatingFolder && (
          <form className="folder-create-form" onSubmit={handleSaveNewFolder}>
            <div className="folder-create-header">
              <span className="folder-create-title">Nueva Carpeta / Tema</span>
              <button 
                type="button" 
                className="folder-create-close" 
                onClick={() => setIsCreatingFolder(false)}
              >
                <X size={13} />
              </button>
            </div>
            <input
              type="text"
              className="folder-name-input"
              placeholder="Ej. Guiones, Miniaturas..."
              value={newFolderName}
              onChange={e => setNewFolderName(e.target.value)}
              autoFocus
            />
            <div className="folder-color-picker">
              {FOLDER_COLORS.map(c => (
                <button
                  key={c}
                  type="button"
                  className={`color-dot ${newFolderColor === c ? 'selected' : ''}`}
                  style={{ backgroundColor: c }}
                  onClick={() => setNewFolderColor(c)}
                />
              ))}
            </div>
            <div className="folder-create-actions">
              <button 
                type="button" 
                className="btn-folder-cancel" 
                onClick={() => setIsCreatingFolder(false)}
              >
                Cancelar
              </button>
              <button 
                type="submit" 
                className="btn-folder-save" 
                disabled={!newFolderName.trim()}
              >
                Crear
              </button>
            </div>
          </form>
        )}

        {/* Quick Search */}
        {sessions.length > 4 && (
          <div className="sidebar-search-box">
            <Search size={13} className="search-icon" />
            <input
              type="text"
              placeholder="Buscar conversaciones..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              className="sidebar-search-input"
            />
            {searchQuery && (
              <button 
                className="clear-search-btn" 
                onClick={() => setSearchQuery('')}
                title="Limpiar búsqueda"
              >
                <X size={12} />
              </button>
            )}
          </div>
        )}

        {/* Selector de Modo de Vista: Por Fecha (por defecto) vs Carpetas */}
        <div className="sidebar-view-selector">
          <button 
            type="button"
            className={`view-mode-btn ${viewMode === 'date' ? 'active' : ''}`}
            onClick={() => handleSetViewMode('date')}
            title="Ver conversaciones clasificadas por fecha reciente"
          >
            <Clock size={12} />
            <span>Por Fecha</span>
          </button>
          <button 
            type="button"
            className={`view-mode-btn ${viewMode === 'folder' ? 'active' : ''}`}
            onClick={() => handleSetViewMode('folder')}
            title="Ver conversaciones organizadas por carpetas"
          >
            <Folder size={12} />
            <span>Carpetas {folders.length > 0 ? `(${folders.length})` : ''}</span>
          </button>
        </div>

        {/* Sessions & Folders Tree */}
        <div className="session-list custom-scrollbar">
          {isLoadingSessions && sessions.length === 0 ? (
            <div className="sidebar-status-card">
              <RefreshCw size={18} className="spin-icon" style={{ color: 'var(--gold)' }} />
              <span style={{ fontSize: '13px', color: 'var(--text-main)', fontWeight: 600 }}>Cargando conversaciones...</span>
              <span style={{ fontSize: '11px', color: 'var(--text-dim)', textAlign: 'center' }}>
                Conectando con el servidor en la nube...
              </span>
            </div>
          ) : sessionsError && sessions.length === 0 ? (
            <div className="sidebar-status-card error">
              <span style={{ fontSize: '13px', color: '#F87171', fontWeight: 600 }}>Servidor no disponible</span>
              <span style={{ fontSize: '11px', color: 'var(--text-dim)', textAlign: 'center' }}>
                El servidor en la nube podría estar iniciando o suspendido.
              </span>
              <button 
                type="button" 
                className="sidebar-retry-btn"
                onClick={onRetryLoadSessions}
              >
                <RefreshCw size={12} /> Reintentar ahora
              </button>
            </div>
          ) : viewMode === 'date' ? (
            /* 1. Vista Clasificada por Fecha (Cronológica) */
            dateGroups.length === 0 ? (
              <div className="sidebar-empty-search">
                {searchQuery ? `No se encontraron conversaciones con "${searchQuery}"` : 'No hay conversaciones aún.'}
              </div>
            ) : (
              dateGroups.map(group => {
                const isCollapsed = Boolean(collapsedDateGroups[group.category])
                return (
                  <div key={group.category} className="date-group">
                    <div 
                      className="date-group-header"
                      onClick={() => toggleDateGroupCollapse(group.category)}
                    >
                      <div className="date-group-header-left">
                        <span className="folder-chevron">
                          {isCollapsed ? <ChevronRight size={13} /> : <ChevronDown size={13} />}
                        </span>
                        <Calendar size={13} className="date-group-icon" />
                        <span className="date-group-title">{group.category}</span>
                        <span className="folder-count">{group.sessions.length}</span>
                      </div>
                    </div>

                    {!isCollapsed && (
                      <div className="date-group-sessions">
                        {group.sessions.map(s => (
                          <SessionRow
                            key={s.id}
                            session={s}
                            isActive={s.id === activeSessionId}
                            folders={folders}
                            activeMoveMenuSessionId={activeMoveMenuSessionId}
                            setActiveMoveMenuSessionId={setActiveMoveMenuSessionId}
                            onSelectSession={onSelectSession}
                            onDeleteSession={onDeleteSession}
                            onMoveSessionToFolder={onMoveSessionToFolder}
                          />
                        ))}
                      </div>
                    )}
                  </div>
                )
              })
            )
          ) : (
            /* 2. Vista Agrupada por Carpetas */
            <>
              {folders.map(folder => {
                const folderSessions = filteredSessions.filter(s => s.folder_id === folder.id)
                const isCollapsed = Boolean(collapsedFolders[folder.id])
                const isEditing = editingFolderId === folder.id

                return (
                  <div key={folder.id} className="folder-group">
                    {/* Folder Header */}
                    <div 
                      className="folder-header"
                      onClick={() => toggleFolderCollapse(folder.id)}
                    >
                      <div className="folder-header-left">
                        <span className="folder-chevron">
                          {isCollapsed ? <ChevronRight size={14} /> : <ChevronDown size={14} />}
                        </span>
                        <span className="folder-icon" style={{ color: folder.color || 'var(--gold)' }}>
                          {isCollapsed ? <Folder size={15} /> : <FolderOpen size={15} />}
                        </span>

                        {isEditing ? (
                          <input
                            type="text"
                            className="folder-edit-input"
                            value={editingFolderName}
                            onClick={e => e.stopPropagation()}
                            onChange={e => setEditingFolderName(e.target.value)}
                            onKeyDown={e => {
                              if (e.key === 'Enter') handleSaveEditFolder(folder.id, folder.color)
                              if (e.key === 'Escape') setEditingFolderId(null)
                            }}
                            onBlur={() => handleSaveEditFolder(folder.id, folder.color)}
                            autoFocus
                          />
                        ) : (
                          <span className="folder-title" title={folder.name}>
                            {folder.name}
                          </span>
                        )}

                        <span className="folder-count">
                          {folderSessions.length}
                        </span>
                      </div>

                      <div className="folder-header-right" onClick={e => e.stopPropagation()}>
                        <button
                          className="folder-action-btn"
                          title="Nuevo chat en esta carpeta"
                          onClick={() => onNewChat(folder.id)}
                        >
                          <Plus size={13} />
                        </button>

                        <div className="dropdown-wrapper">
                          <button
                            className="folder-action-btn dropdown-trigger"
                            title="Opciones de carpeta"
                            onClick={() => setActiveFolderMenuId(activeFolderMenuId === folder.id ? null : folder.id)}
                          >
                            <MoreVertical size={13} />
                          </button>

                          {activeFolderMenuId === folder.id && (
                            <div className="floating-menu folder-action-menu">
                              <button 
                                className="floating-menu-item"
                                onClick={(e) => handleStartEditFolder(folder, e)}
                              >
                                <Edit2 size={13} />
                                <span>Renombrar</span>
                              </button>
                              <button 
                                className="floating-menu-item delete"
                                onClick={() => {
                                  setActiveFolderMenuId(null)
                                  onDeleteFolder(folder.id)
                                }}
                              >
                                <Trash2 size={13} />
                                <span>Eliminar carpeta</span>
                              </button>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>

                    {/* Folder Sessions List */}
                    {!isCollapsed && (
                      <div className="folder-sessions-container">
                        {folderSessions.length === 0 ? (
                          <div className="folder-empty-hint">
                            Sin conversaciones aquí.
                          </div>
                        ) : (
                          folderSessions.map(s => (
                            <SessionRow
                              key={s.id}
                              session={s}
                              isActive={s.id === activeSessionId}
                              folders={folders}
                              activeMoveMenuSessionId={activeMoveMenuSessionId}
                              setActiveMoveMenuSessionId={setActiveMoveMenuSessionId}
                              onSelectSession={onSelectSession}
                              onDeleteSession={onDeleteSession}
                              onMoveSessionToFolder={onMoveSessionToFolder}
                            />
                          ))
                        )}
                      </div>
                    )}
                  </div>
                )
              })}

              {/* 2. Sección Sin Clasificar */}
              {(uncategorizedSessions.length > 0 || folders.length === 0) && (
                <div className="folder-group uncategorized-group">
                  {folders.length > 0 && (
                    <div 
                      className="folder-header uncategorized-header"
                      onClick={() => toggleFolderCollapse('uncategorized')}
                    >
                      <div className="folder-header-left">
                        <span className="folder-chevron">
                          {collapsedFolders['uncategorized'] ? <ChevronRight size={14} /> : <ChevronDown size={14} />}
                        </span>
                        <span className="folder-icon" style={{ color: 'var(--text-dim)' }}>
                          <Folder size={15} />
                        </span>
                        <span className="folder-title">Sin clasificar</span>
                        <span className="folder-count">{uncategorizedSessions.length}</span>
                      </div>
                    </div>
                  )}

                  {(!folders.length || !collapsedFolders['uncategorized']) && (
                    <div className="folder-sessions-container">
                      {uncategorizedSessions.map(s => (
                        <SessionRow
                          key={s.id}
                          session={s}
                          isActive={s.id === activeSessionId}
                          folders={folders}
                          activeMoveMenuSessionId={activeMoveMenuSessionId}
                          setActiveMoveMenuSessionId={setActiveMoveMenuSessionId}
                          onSelectSession={onSelectSession}
                          onDeleteSession={onDeleteSession}
                          onMoveSessionToFolder={onMoveSessionToFolder}
                        />
                      ))}
                    </div>
                  )}
                </div>
              )}
            </>
          )}

          {/* Empty state when searching */}
          {searchQuery && filteredSessions.length === 0 && (
            <div className="sidebar-empty-search">
              No se encontraron conversaciones con "{searchQuery}"
            </div>
          )}
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
    </>
  )
}

/**
 * Fila individual de una conversación dentro del sidebar
 */
function SessionRow({
  session,
  isActive,
  folders,
  activeMoveMenuSessionId,
  setActiveMoveMenuSessionId,
  onSelectSession,
  onDeleteSession,
  onMoveSessionToFolder
}) {
  const isMoveMenuOpen = activeMoveMenuSessionId === session.id
  const dateFormatted = formatSessionDate(session.updated_at || session.created_at)

  return (
    <div
      className={`session-item ${isActive ? 'active' : ''}`}
      onClick={() => onSelectSession(session.id)}
    >
      <div className="session-item-content">
        <span className="session-title" title={session.title}>
          {session.title}
        </span>
        <div className="session-meta">
          {dateFormatted && (
            <span className="session-date" title={`Última actividad: ${dateFormatted}`}>
              <Clock size={10} className="session-date-icon" />
              <span>{dateFormatted}</span>
            </span>
          )}
          {session.folder_name && (
            <span
              className="session-folder-tag"
              style={{
                borderColor: `${session.folder_color || '#F59E0B'}55`,
                color: session.folder_color || '#F59E0B'
              }}
              title={`Carpeta: ${session.folder_name}`}
            >
              {session.folder_name}
            </span>
          )}
        </div>
      </div>

      <div className="session-item-actions" onClick={e => e.stopPropagation()}>
        {/* Move to Folder Button */}
        {folders.length > 0 && (
          <div className="dropdown-wrapper">
            <button
              className="session-action-btn dropdown-trigger"
              title="Mover a carpeta..."
              onClick={(e) => {
                e.stopPropagation()
                setActiveMoveMenuSessionId(isMoveMenuOpen ? null : session.id)
              }}
            >
              <FolderInput size={13} />
            </button>

            {isMoveMenuOpen && (
              <div className="floating-menu move-folder-menu">
                <div className="floating-menu-header">Mover a tema/carpeta:</div>
                {folders.map(f => (
                  <button
                    key={f.id}
                    className={`floating-menu-item ${session.folder_id === f.id ? 'active' : ''}`}
                    onClick={() => {
                      onMoveSessionToFolder(session.id, f.id)
                      setActiveMoveMenuSessionId(null)
                    }}
                  >
                    <span className="color-dot-mini" style={{ backgroundColor: f.color || 'var(--gold)' }} />
                    <span className="floating-menu-item-text">{f.name}</span>
                    {session.folder_id === f.id && <Check size={12} className="check-icon" />}
                  </button>
                ))}
                {session.folder_id && (
                  <>
                    <div className="floating-menu-divider" />
                    <button
                      className="floating-menu-item"
                      onClick={() => {
                        onMoveSessionToFolder(session.id, null)
                        setActiveMoveMenuSessionId(null)
                      }}
                    >
                      <X size={12} />
                      <span className="floating-menu-item-text">Sin clasificar</span>
                    </button>
                  </>
                )}
              </div>
            )}
          </div>
        )}

        {/* Delete Session Button */}
        <button
          className="delete-session-btn"
          onClick={(e) => {
            e.stopPropagation()
            onDeleteSession(session.id)
          }}
          title="Eliminar conversación"
        >
          <Trash2 size={13} />
        </button>
      </div>
    </div>
  )
}
