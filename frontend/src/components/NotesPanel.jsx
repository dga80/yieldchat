import React, { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import {
  StickyNote,
  Plus,
  X,
  ChevronDown,
  ChevronUp,
  Copy,
  Check,
  Trash2,
  Edit3,
  Tag,
  Sparkles,
  BookOpen,
  Download
} from 'lucide-react'
import toast from 'react-hot-toast'
import { downloadTextAsFile } from '../utils/fileDownloader'

const CATEGORY_COLORS = {
  Estrategia: { bg: 'rgba(245, 158, 11, 0.15)', text: '#F59E0B', border: 'rgba(245, 158, 11, 0.3)' },
  Packaging: { bg: 'rgba(59, 130, 246, 0.15)', text: '#60A5FA', border: 'rgba(59, 130, 246, 0.3)' },
  Outliers: { bg: 'rgba(16, 185, 129, 0.15)', text: '#34D399', border: 'rgba(16, 185, 129, 0.3)' },
  Guion: { bg: 'rgba(168, 85, 247, 0.15)', text: '#C084FC', border: 'rgba(168, 85, 247, 0.3)' },
  General: { bg: 'rgba(148, 163, 184, 0.15)', text: '#94A3B8', border: 'rgba(148, 163, 184, 0.3)' }
}

const DEFAULT_CATEGORIES = ['Estrategia', 'Packaging', 'Outliers', 'Guion', 'General']

export default function NotesPanel({
  isOpen,
  onClose,
  notes = [],
  expandedNoteIds = [],
  onToggleExpandNote,
  onCreateNote,
  onUpdateNote,
  onDeleteNote,
  activeSessionTitle
}) {
  const [isCreating, setIsCreating] = useState(false)
  const [newTitle, setNewTitle] = useState('')
  const [newCategory, setNewCategory] = useState('Estrategia')
  const [newContent, setNewContent] = useState('')

  const [editingNoteId, setEditingNoteId] = useState(null)
  const [editTitle, setEditTitle] = useState('')
  const [editCategory, setEditCategory] = useState('Estrategia')
  const [editContent, setEditContent] = useState('')

  const [copiedNoteId, setCopiedNoteId] = useState(null)

  const handleStartCreate = () => {
    setNewTitle('')
    setNewCategory('Estrategia')
    setNewContent('')
    setIsCreating(true)
    setEditingNoteId(null)
  }

  const handleCancelCreate = () => {
    setIsCreating(false)
    setNewTitle('')
    setNewContent('')
  }

  const handleSaveNew = async (e) => {
    e?.preventDefault()
    if (!newTitle.trim()) {
      toast.error('Indica un título para la nota')
      return
    }
    if (!newContent.trim()) {
      toast.error('Indica el contenido de la nota')
      return
    }

    try {
      await onCreateNote({
        title: newTitle.trim(),
        category: newCategory.trim() || 'Estrategia',
        content: newContent.trim()
      })
      setIsCreating(false)
      setNewTitle('')
      setNewContent('')
      toast.success('Nota guardada')
    } catch (err) {
      toast.error('Error al guardar la nota')
    }
  }

  const handleStartEdit = (note, e) => {
    e?.stopPropagation()
    setEditingNoteId(note.id)
    setEditTitle(note.title)
    setEditCategory(note.category || 'Estrategia')
    setEditContent(note.content)
    setIsCreating(false)
    // Asegurar que la nota esté expandida para editar
    if (!expandedNoteIds.includes(note.id)) {
      onToggleExpandNote(note.id)
    }
  }

  const handleCancelEdit = () => {
    setEditingNoteId(null)
    setEditTitle('')
    setEditContent('')
  }

  const handleSaveEdit = async (noteId, e) => {
    e?.preventDefault()
    if (!editTitle.trim()) {
      toast.error('El título no puede estar vacío')
      return
    }
    if (!editContent.trim()) {
      toast.error('El contenido no puede estar vacío')
      return
    }

    try {
      await onUpdateNote(noteId, {
        title: editTitle.trim(),
        category: editCategory.trim() || 'Estrategia',
        content: editContent.trim()
      })
      setEditingNoteId(null)
      toast.success('Nota actualizada')
    } catch (err) {
      toast.error('Error al actualizar la nota')
    }
  }

  const handleCopyNote = (note, e) => {
    e?.stopPropagation()
    const textToCopy = `# ${note.title}\n\n${note.content}`
    navigator.clipboard.writeText(textToCopy)
    setCopiedNoteId(note.id)
    toast.success('Nota copiada al portapapeles')
    setTimeout(() => {
      setCopiedNoteId(null)
    }, 2000)
  }

  const handleDownloadNote = (note, e) => {
    e?.stopPropagation()
    const safeTitle = (note.title || 'nota')
      .replace(/[^a-zA-Z0-9áéíóúÁÉÍÓÚñÑ\s_-]/g, '')
      .trim()
      .slice(0, 30)
      .replace(/\s+/g, '_')
      .toLowerCase()
    const content = `# [${(note.category || 'ESTRATEGIA').toUpperCase()}] ${note.title}\n\n${note.content}`
    downloadTextAsFile(`${safeTitle}.txt`, content)
  }

  const handleDownloadAllNotes = () => {
    if (!notes.length) return
    let combined = `# NOTAS ESTRATÉGICAS: ${activeSessionTitle || 'Conversación'}\n`
    combined += `Generado el: ${new Date().toLocaleString('es-ES')}\n`
    combined += `Total de notas: ${notes.length}\n\n`
    combined += '==================================================\n\n'

    notes.forEach((n, idx) => {
      combined += `=== ${idx + 1}. [${(n.category || 'ESTRATEGIA').toUpperCase()}] ${n.title} ===\n`
      combined += `Fecha: ${formatDate(n.updated_at || n.created_at)}\n\n`
      combined += `${n.content}\n\n`
      combined += '--------------------------------------------------\n\n'
    })

    const safeTitle = (activeSessionTitle || 'notas_yieldchat')
      .replace(/[^a-zA-Z0-9áéíóúÁÉÍÓÚñÑ\s_-]/g, '')
      .trim()
      .slice(0, 30)
      .replace(/\s+/g, '_')
      .toLowerCase()
    downloadTextAsFile(`${safeTitle}_todas_las_notas.txt`, combined)
  }

  const handleDelete = (noteId, e) => {
    e?.stopPropagation()
    if (window.confirm('¿Deseas eliminar esta nota?')) {
      onDeleteNote(noteId)
      toast.success('Nota eliminada')
    }
  }

  const formatDate = (isoStr) => {
    if (!isoStr) return ''
    try {
      const d = new Date(isoStr)
      return d.toLocaleDateString('es-ES', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })
    } catch {
      return ''
    }
  }

  const getCategoryStyle = (cat) => {
    return CATEGORY_COLORS[cat] || CATEGORY_COLORS.General
  }

  return (
    <>
      {/* Backdrop para móviles */}
      {isOpen && <div className="notes-panel-backdrop" onClick={onClose} />}

      <aside className={`notes-panel ${isOpen ? 'open' : 'closed'}`}>
        {/* Header del panel */}
        <div className="notes-panel-header">
          <div className="notes-panel-title-group">
            <div className="notes-brand-icon">
              <StickyNote size={17} />
            </div>
            <div>
              <div className="notes-header-title">Notas de la Conversación</div>
              <div className="notes-header-subtitle">
                {notes.length} {notes.length === 1 ? 'nota guardada' : 'notas guardadas'}
              </div>
            </div>
          </div>

          <div className="notes-panel-actions">
            {notes.length > 0 && (
              <button
                className="notes-download-all-btn"
                onClick={handleDownloadAllNotes}
                title="Descargar todas las notas unidas en un archivo .txt"
              >
                <Download size={14} />
              </button>
            )}
            <button
              className="notes-add-btn"
              onClick={handleStartCreate}
              title="Nueva nota rápida"
              disabled={isCreating}
            >
              <Plus size={15} />
              <span>Nueva</span>
            </button>
            <button
              className="notes-close-btn"
              onClick={onClose}
              title="Ocultar panel de notas"
              aria-label="Cerrar panel de notas"
            >
              <X size={18} />
            </button>
          </div>
        </div>

        {/* Formulario de creación de nueva nota */}
        {isCreating && (
          <div className="note-create-card">
            <div className="note-card-form-title">
              <Sparkles size={14} style={{ color: 'var(--gold)' }} />
              <span>Crear Nueva Nota</span>
            </div>
            <form onSubmit={handleSaveNew}>
              <input
                type="text"
                className="note-input-title"
                placeholder="Título de la nota (ej. Outliers @cosmoexplains)..."
                value={newTitle}
                onChange={e => setNewTitle(e.target.value)}
                autoFocus
              />

              <div className="note-category-picker">
                <span className="note-picker-label">Categoría:</span>
                <div className="note-category-pills">
                  {DEFAULT_CATEGORIES.map(cat => {
                    const style = getCategoryStyle(cat)
                    const isSelected = newCategory === cat
                    return (
                      <button
                        key={cat}
                        type="button"
                        className={`note-cat-pill ${isSelected ? 'active' : ''}`}
                        onClick={() => setNewCategory(cat)}
                        style={{
                          backgroundColor: isSelected ? style.bg : 'transparent',
                          color: isSelected ? style.text : 'var(--text-muted)',
                          borderColor: isSelected ? style.border : 'rgba(255,255,255,0.08)'
                        }}
                      >
                        {cat}
                      </button>
                    )
                  })}
                </div>
              </div>

              <textarea
                className="note-textarea-content"
                rows={5}
                placeholder="Escribe el contenido en Markdown..."
                value={newContent}
                onChange={e => setNewContent(e.target.value)}
              />

              <div className="note-form-buttons">
                <button type="button" className="note-btn-cancel" onClick={handleCancelCreate}>
                  Cancelar
                </button>
                <button type="submit" className="note-btn-save">
                  Guardar Nota
                </button>
              </div>
            </form>
          </div>
        )}

        {/* Lista de notas tipo acordeón colapsable/desplegable */}
        <div className="notes-list-container">
          {notes.length === 0 && !isCreating ? (
            <div className="notes-empty-state">
              <div className="notes-empty-icon">
                <BookOpen size={28} />
              </div>
              <h4>Sin notas en esta conversación</h4>
              <p>
                Pide al asistente en el chat <em>"crea una nota sobre estos outliers..."</em> o haz clic en <strong>+ Nueva</strong> para redactar tus apuntes estratégicos.
              </p>
              <button className="notes-create-first-btn" onClick={handleStartCreate}>
                <Plus size={15} />
                <span>Crear Primera Nota</span>
              </button>
            </div>
          ) : (
            notes.map(note => {
              const isExpanded = expandedNoteIds.includes(note.id)
              const isEditing = editingNoteId === note.id
              const catStyle = getCategoryStyle(note.category)

              return (
                <div
                  key={note.id}
                  className={`note-capsule ${isExpanded ? 'expanded' : 'collapsed'}`}
                >
                  {/* Barra de cabecera de la cápsula (Clic para desplegar/colapsar) */}
                  <div
                    className="note-capsule-header"
                    onClick={() => onToggleExpandNote(note.id)}
                  >
                    <div className="note-header-left">
                      <span
                        className="note-tag-badge"
                        style={{
                          backgroundColor: catStyle.bg,
                          color: catStyle.text,
                          borderColor: catStyle.border
                        }}
                      >
                        {note.category || 'Estrategia'}
                      </span>
                      <span className="note-title-text" title={note.title}>
                        {note.title}
                      </span>
                    </div>

                    <div className="note-header-right">
                      {/* Acciones de la nota */}
                      <button
                        type="button"
                        className="note-action-btn"
                        onClick={(e) => handleCopyNote(note, e)}
                        title="Copiar nota"
                      >
                        {copiedNoteId === note.id ? (
                          <Check size={13} style={{ color: 'var(--green)' }} />
                        ) : (
                          <Copy size={13} />
                        )}
                      </button>

                      <button
                        type="button"
                        className="note-action-btn"
                        onClick={(e) => handleDownloadNote(note, e)}
                        title="Descargar esta nota en .txt"
                      >
                        <Download size={13} style={{ color: '#38BDF8' }} />
                      </button>

                      <button
                        type="button"
                        className="note-action-btn"
                        onClick={(e) => handleStartEdit(note, e)}
                        title="Editar nota"
                      >
                        <Edit3 size={13} />
                      </button>

                      <button
                        type="button"
                        className="note-action-btn note-action-btn-danger"
                        onClick={(e) => handleDelete(note.id, e)}
                        title="Eliminar nota"
                      >
                        <Trash2 size={13} />
                      </button>

                      {/* Icono Chevron indicador de colapso */}
                      <div className="note-chevron-wrapper">
                        {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                      </div>
                    </div>
                  </div>

                  {/* Cuerpo desplegable de la nota */}
                  {isExpanded && (
                    <div className="note-capsule-body">
                      {isEditing ? (
                        <form onSubmit={(e) => handleSaveEdit(note.id, e)} className="note-edit-form">
                          <input
                            type="text"
                            className="note-input-title"
                            value={editTitle}
                            onChange={e => setEditTitle(e.target.value)}
                            placeholder="Título..."
                            autoFocus
                          />

                          <div className="note-category-picker">
                            <div className="note-category-pills">
                              {DEFAULT_CATEGORIES.map(cat => {
                                const style = getCategoryStyle(cat)
                                const isSelected = editCategory === cat
                                return (
                                  <button
                                    key={cat}
                                    type="button"
                                    className={`note-cat-pill ${isSelected ? 'active' : ''}`}
                                    onClick={() => setEditCategory(cat)}
                                    style={{
                                      backgroundColor: isSelected ? style.bg : 'transparent',
                                      color: isSelected ? style.text : 'var(--text-muted)',
                                      borderColor: isSelected ? style.border : 'rgba(255,255,255,0.08)'
                                    }}
                                  >
                                    {cat}
                                  </button>
                                )
                              })}
                            </div>
                          </div>

                          <textarea
                            className="note-textarea-content"
                            rows={6}
                            value={editContent}
                            onChange={e => setEditContent(e.target.value)}
                          />

                          <div className="note-form-buttons">
                            <button type="button" className="note-btn-cancel" onClick={handleCancelEdit}>
                              Cancelar
                            </button>
                            <button type="submit" className="note-btn-save">
                              Guardar Cambios
                            </button>
                          </div>
                        </form>
                      ) : (
                        <>
                          <div className="note-markdown-content">
                            <ReactMarkdown remarkPlugins={[remarkGfm]}>
                              {note.content}
                            </ReactMarkdown>
                          </div>
                          <div className="note-footer-meta">
                            <span>{formatDate(note.updated_at || note.created_at)}</span>
                          </div>
                        </>
                      )}
                    </div>
                  )}
                </div>
              )
            })
          )}
        </div>
      </aside>
    </>
  )
}
