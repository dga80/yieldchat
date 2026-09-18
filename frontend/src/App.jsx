import React, { useState, useEffect, useRef } from 'react'
import { Toaster, toast } from 'react-hot-toast'
import Sidebar from './components/Sidebar'
import ChatArea from './components/ChatArea'
import MemoryModal from './components/MemoryModal'
import NotesPanel from './components/NotesPanel'
import ImageStudioModal from './components/ImageStudioModal'

const API_BASE = import.meta.env.VITE_API_URL || '/api'

export default function App() {
  // Inicializar sesiones y conversación desde localStorage para carga inmediata en móvil (0 ms)
  const [sessions, setSessions] = useState(() => {
    try {
      const cached = localStorage.getItem('yieldchat_cached_sessions')
      return cached ? JSON.parse(cached) : []
    } catch {
      return []
    }
  })
  const [folders, setFolders] = useState(() => {
    try {
      const cached = localStorage.getItem('yieldchat_cached_folders')
      return cached ? JSON.parse(cached) : []
    } catch {
      return []
    }
  })
  const [activeSessionId, setActiveSessionId] = useState(() => {
    try {
      return localStorage.getItem('yieldchat_active_session_id') || null
    } catch {
      return null
    }
  })
  const [activeSession, setActiveSession] = useState(() => {
    try {
      const cached = localStorage.getItem('yieldchat_cached_active_session')
      return cached ? JSON.parse(cached) : null
    } catch {
      return null
    }
  })
  const [messages, setMessages] = useState(() => {
    try {
      const cached = localStorage.getItem('yieldchat_cached_active_session')
      if (cached) {
        const parsed = JSON.parse(cached)
        return parsed?.messages || []
      }
      return []
    } catch {
      return []
    }
  })
  const [notes, setNotes] = useState(() => {
    try {
      const activeId = localStorage.getItem('yieldchat_active_session_id')
      if (activeId) {
        const cached = localStorage.getItem(`yieldchat_cached_notes_${activeId}`)
        return cached ? JSON.parse(cached) : []
      }
      return []
    } catch {
      return []
    }
  })
  const [isNotesOpen, setIsNotesOpen] = useState(() => {
    if (typeof window !== 'undefined') {
      return window.innerWidth > 1150
    }
    return false
  })
  const [expandedNoteIds, setExpandedNoteIds] = useState([])
  const [streamingMessage, setStreamingMessage] = useState('')
  const [currentTool, setCurrentTool] = useState(null)
  const [loading, setLoading] = useState(false)
  const [isLoadingSessions, setIsLoadingSessions] = useState(false)
  const [sessionsError, setSessionsError] = useState(false)
  const [isLoadingMessages, setIsLoadingMessages] = useState(false)
  const [status, setStatus] = useState(null)
  const [insights, setInsights] = useState([])
  const [isMemoryOpen, setIsMemoryOpen] = useState(false)
  const [isImageStudioOpen, setIsImageStudioOpen] = useState(false)
  const [isSidebarOpen, setIsSidebarOpen] = useState(() => {
    if (typeof window !== 'undefined') {
      return window.innerWidth > 900
    }
    return false
  })
  const [syncing, setSyncing] = useState(false)
  const [syncStatus, setSyncStatus] = useState(null)
  const abortControllerRef = useRef(null)

  const activeSessionIdRef = useRef(activeSessionId)
  const messagesRef = useRef(messages)

  useEffect(() => {
    activeSessionIdRef.current = activeSessionId
  }, [activeSessionId])

  useEffect(() => {
    messagesRef.current = messages
  }, [messages])

  // 1. Initial Load: Sessions, Folders, Memory, Status and Multi-device Sync
  useEffect(() => {
    fetchStatus()
    fetchMemory()
    fetchSyncStatus()
    fetchFolders()
    loadSessions()
    const initialSessionId = localStorage.getItem('yieldchat_active_session_id')
    if (initialSessionId) {
      loadNotesForSession(initialSessionId)
    }

    // Sincronización automática periódica en segundo plano cada 25 segundos (actualiza lista sin resetear chat activo)
    const syncInterval = setInterval(() => {
      fetchSyncStatus()
      refreshSessionsList()
    }, 25000)

    // Sincronización inmediata al volver a la app o cambiar de ventana/pestaña
    const handleSyncOnResume = () => {
      if (document.visibilityState === 'visible') {
        refreshSessionsList()
        fetchFolders()
        fetchSyncStatus()
      }
    }

    window.addEventListener('focus', handleSyncOnResume)
    document.addEventListener('visibilitychange', handleSyncOnResume)

    return () => {
      clearInterval(syncInterval)
      window.removeEventListener('focus', handleSyncOnResume)
      document.removeEventListener('visibilitychange', handleSyncOnResume)
    }
  }, [])

  const fetchStatus = async () => {
    try {
      const res = await fetch(`${API_BASE}/status`)
      const data = await res.json()
      setStatus(data)
    } catch (e) {
      console.error('Error fetching status:', e)
    }
  }

  const fetchSyncStatus = async () => {
    try {
      const res = await fetch(`${API_BASE}/sync/status`)
      const data = await res.json()
      setSyncStatus(data)
    } catch (e) {
      console.error('Error fetching sync status:', e)
    }
  }

  const fetchMemory = async () => {
    try {
      const res = await fetch(`${API_BASE}/memory`)
      const data = await res.json()
      setInsights(data)
    } catch (e) {
      console.error('Error fetching memory:', e)
    }
  }

  const fetchFolders = async () => {
    try {
      const res = await fetch(`${API_BASE}/folders`)
      const data = await res.json()
      setFolders(data)
      try {
        localStorage.setItem('yieldchat_cached_folders', JSON.stringify(data))
      } catch (e) {}
    } catch (e) {
      console.error('Error fetching folders:', e)
    }
  }

  const refreshSessionsList = async () => {
    try {
      const res = await fetch(`${API_BASE}/sessions`)
      if (!res.ok) return
      const data = await res.json()
      setSessions(data)
      try {
        localStorage.setItem('yieldchat_cached_sessions', JSON.stringify(data))
      } catch (e) {}

      // Solo si no hay ninguna sesión activa seleccionada (caso muy raro), seleccionar una
      if (!activeSessionIdRef.current && data.length > 0) {
        selectSession(data[0].id, false)
      }
    } catch (e) {
      console.warn('Background sessions sync failed:', e)
    }
  }

  const loadSessions = async (retryCount = 0) => {
    try {
      setSessionsError(false)
      setIsLoadingSessions(prev => sessions.length === 0 ? true : prev)
      const res = await fetch(`${API_BASE}/sessions`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      setSessions(data)
      setIsLoadingSessions(false)
      setSessionsError(false)

      try {
        localStorage.setItem('yieldchat_cached_sessions', JSON.stringify(data))
      } catch (e) {}

      // Si hay sesiones, seleccionar la última activa o la primera de la lista
      const savedActiveId = localStorage.getItem('yieldchat_active_session_id')
      const targetId = (savedActiveId && data.some(s => s.id === savedActiveId))
        ? savedActiveId
        : (data.length > 0 ? data[0].id : null)

      if (targetId) {
        // Cargar conversación si no hay mensajes o es distinta a la activa actual
        const currentActive = activeSessionIdRef.current
        const currentMsgs = messagesRef.current
        if (!currentActive || currentActive !== targetId || currentMsgs.length === 0) {
          selectSession(targetId, false)
        }
      } else if (data.length === 0) {
        handleNewChat()
      }
    } catch (e) {
      console.error('Error loading sessions:', e)
      // Si el servidor de Render está despertando del modo reposo, reintentar automáticamente
      if (retryCount < 4) {
        setTimeout(() => loadSessions(retryCount + 1), 3500)
      } else {
        setIsLoadingSessions(false)
        if (sessions.length === 0) {
          setSessionsError(true)
        }
      }
    }
  }

  const selectSession = async (sessionId, closeSidebarOnMobile = true) => {
    setActiveSessionId(sessionId)
    try {
      localStorage.setItem('yieldchat_active_session_id', sessionId)
    } catch (e) {}

    setStreamingMessage('')
    setCurrentTool(null)
    loadNotesForSession(sessionId)
    if (closeSidebarOnMobile && typeof window !== 'undefined' && window.innerWidth <= 900) {
      setIsSidebarOpen(false)
    }

    setIsLoadingMessages(true)
    try {
      const res = await fetch(`${API_BASE}/sessions/${sessionId}`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      setActiveSession(data)
      setMessages(data.messages || [])
      setIsLoadingMessages(false)
      try {
        localStorage.setItem('yieldchat_cached_active_session', JSON.stringify(data))
      } catch (e) {}
    } catch (e) {
      console.error('Error fetching session:', e)
      setIsLoadingMessages(false)
      toast.error('Error al cargar la conversación')
    }
  }

  const handleNewChat = async (folderId = null) => {
    if (typeof window !== 'undefined' && window.innerWidth <= 900) {
      setIsSidebarOpen(false)
    }
    setNotes([])
    setExpandedNoteIds([])
    try {
      const res = await fetch(`${API_BASE}/sessions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: 'Nueva Conversación', folder_id: folderId })
      })
      const newSession = await res.json()
      setSessions(prev => [newSession, ...prev])
      selectSession(newSession.id)
      if (folderId) fetchFolders()
    } catch (e) {
      toast.error('Error al crear nueva conversación')
    }
  }

  const handleDeleteSession = async (sessionId) => {
    try {
      await fetch(`${API_BASE}/sessions/${sessionId}`, { method: 'DELETE' })
      const updated = sessions.filter(s => s.id !== sessionId)
      setSessions(updated)
      fetchFolders() // actualizar conteos de carpetas
      if (activeSessionId === sessionId) {
        if (updated.length > 0) {
          selectSession(updated[0].id)
        } else {
          handleNewChat()
        }
      }
      toast.success('Conversación eliminada')
    } catch (e) {
      toast.error('Error al eliminar conversación')
    }
  }

  const handleCreateFolder = async (name, color = '#F59E0B') => {
    try {
      const res = await fetch(`${API_BASE}/folders`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, color })
      })
      const newFolder = await res.json()
      setFolders(prev => [...prev, newFolder])
      toast.success(`Carpeta "${name}" creada`)
      return newFolder
    } catch (e) {
      toast.error('Error al crear carpeta')
    }
  }

  const handleUpdateFolder = async (folderId, name, color) => {
    try {
      const res = await fetch(`${API_BASE}/folders/${folderId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, color })
      })
      const updated = await res.json()
      setFolders(prev => prev.map(f => f.id === folderId ? { ...f, ...updated } : f))
      setSessions(prev => prev.map(s => s.folder_id === folderId ? {
        ...s,
        folder_name: updated.name,
        folder_color: updated.color
      } : s))
      toast.success('Carpeta actualizada')
    } catch (e) {
      toast.error('Error al actualizar carpeta')
    }
  }

  const handleDeleteFolder = async (folderId) => {
    try {
      await fetch(`${API_BASE}/folders/${folderId}`, { method: 'DELETE' })
      setFolders(prev => prev.filter(f => f.id !== folderId))
      setSessions(prev => prev.map(s => s.folder_id === folderId ? {
        ...s,
        folder_id: null,
        folder_name: null,
        folder_color: null
      } : s))
      toast.success('Carpeta eliminada (conversaciones conservadas)')
    } catch (e) {
      toast.error('Error al eliminar carpeta')
    }
  }

  const handleMoveSessionToFolder = async (sessionId, folderId) => {
    try {
      await fetch(`${API_BASE}/sessions/${sessionId}/folder`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ folder_id: folderId })
      })
      const targetFolder = folders.find(f => f.id === folderId)
      setSessions(prev => prev.map(s => s.id === sessionId ? {
        ...s,
        folder_id: folderId,
        folder_name: targetFolder ? targetFolder.name : null,
        folder_color: targetFolder ? targetFolder.color : null
      } : s))
      if (activeSession?.id === sessionId) {
        setActiveSession(prev => ({
          ...prev,
          folder_id: folderId,
          folder_name: targetFolder ? targetFolder.name : null,
          folder_color: targetFolder ? targetFolder.color : null
        }))
      }
      fetchFolders()
      toast.success(folderId ? `Movido a "${targetFolder?.name || 'Carpeta'}"` : 'Movido a Sin clasificar')
    } catch (e) {
      toast.error('Error al mover conversación')
    }
  }

  const handleUpdateTitle = async (newTitle) => {
    if (!activeSessionId) return
    try {
      await fetch(`${API_BASE}/sessions/${activeSessionId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: newTitle })
      })
      setSessions(prev => prev.map(s => s.id === activeSessionId ? { ...s, title: newTitle } : s))
      setActiveSession(prev => ({ ...prev, title: newTitle }))
    } catch (e) {
      toast.error('Error al renombrar título')
    }
  }

  // ── Gestión de Notas de la Conversación Activa ─────────────────────────────
  const loadNotesForSession = async (sessionId) => {
    if (!sessionId) {
      setNotes([])
      return
    }
    // Carga inmediata desde caché
    let cachedNotes = []
    try {
      const cached = localStorage.getItem(`yieldchat_cached_notes_${sessionId}`)
      if (cached) {
        cachedNotes = JSON.parse(cached)
        if (Array.isArray(cachedNotes) && cachedNotes.length > 0) {
          setNotes(cachedNotes)
          setExpandedNoteIds(prev => prev.length ? prev : [cachedNotes[0].id])
        }
      }
    } catch (e) {}

    try {
      const res = await fetch(`${API_BASE}/sessions/${sessionId}/notes`)
      if (res.ok) {
        const data = await res.json()
        if (Array.isArray(data) && data.length > 0) {
          setNotes(data)
          try {
            localStorage.setItem(`yieldchat_cached_notes_${sessionId}`, JSON.stringify(data))
          } catch (e) {}
          setExpandedNoteIds(prev => prev.length ? prev : [data[0].id])
        } else if (cachedNotes && cachedNotes.length > 0) {
          // Si el servidor aún no tiene las notas pero las teníamos en caché, conservarlas
          console.warn('Backend returned empty notes list, preserving locally cached notes')
        } else {
          setNotes([])
        }
      }
    } catch (e) {
      console.warn('Error fetching notes:', e)
    }
  }

  const handleToggleExpandNote = (noteId) => {
    setExpandedNoteIds(prev =>
      prev.includes(noteId) ? prev.filter(id => id !== noteId) : [...prev, noteId]
    )
  }

  const handleCreateNote = async ({ title, category, content }) => {
    if (!activeSessionId) return
    const tempId = `note_${Date.now()}`
    const newNote = {
      id: tempId,
      session_id: activeSessionId,
      title,
      category: category || 'Estrategia',
      content,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    }

    setNotes(prev => [newNote, ...prev])
    setExpandedNoteIds(prev => [tempId, ...prev])
    setIsNotesOpen(true)

    try {
      const res = await fetch(`${API_BASE}/sessions/${activeSessionId}/notes`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title, category, content })
      })
      if (res.ok) {
        const saved = await res.json()
        setNotes(prev => {
          const updated = prev.map(n => n.id === tempId ? saved : n)
          try {
            localStorage.setItem(`yieldchat_cached_notes_${activeSessionId}`, JSON.stringify(updated))
          } catch (e) {}
          return updated
        })
        setExpandedNoteIds(prev => prev.map(id => id === tempId ? saved.id : id))
      }
    } catch (e) {
      console.error('Error creating note:', e)
    }
  }

  const handleUpdateNote = async (noteId, { title, category, content }) => {
    setNotes(prev => {
      const updated = prev.map(n => n.id === noteId ? { ...n, title, category, content, updated_at: new Date().toISOString() } : n)
      try {
        localStorage.setItem(`yieldchat_cached_notes_${activeSessionId}`, JSON.stringify(updated))
      } catch (e) {}
      return updated
    })

    try {
      const res = await fetch(`${API_BASE}/notes/${noteId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title, category, content })
      })
      if (res.ok) {
        const updated = await res.json()
        setNotes(prev => {
          const list = prev.map(n => n.id === noteId ? updated : n)
          try {
            localStorage.setItem(`yieldchat_cached_notes_${activeSessionId}`, JSON.stringify(list))
          } catch (e) {}
          return list
        })
      }
    } catch (e) {
      console.error('Error updating note:', e)
    }
  }

  const handleDeleteNote = async (noteId) => {
    setNotes(prev => {
      const updated = prev.filter(n => n.id !== noteId)
      try {
        localStorage.setItem(`yieldchat_cached_notes_${activeSessionId}`, JSON.stringify(updated))
      } catch (e) {}
      return updated
    })
    setExpandedNoteIds(prev => prev.filter(id => id !== noteId))

    try {
      await fetch(`${API_BASE}/notes/${noteId}`, { method: 'DELETE' })
    } catch (e) {
      console.error('Error deleting note:', e)
    }
  }

  const handleSaveMessageAsNote = (messageText) => {
    if (!messageText) return
    let title = 'Nota Estratégica'
    let content = messageText
    const lines = messageText.split('\n')
    const firstNonEmpty = lines.find(l => l.trim().length > 0) || ''
    if (firstNonEmpty.startsWith('#')) {
      title = firstNonEmpty.replace(/^[#\s]+/, '').slice(0, 50)
    } else if (firstNonEmpty.toLowerCase().includes('nota estratégica:')) {
      title = firstNonEmpty.replace(/^[*\s]*nota estratégica:\s*/i, '').slice(0, 50)
    } else {
      title = firstNonEmpty.slice(0, 45) + (firstNonEmpty.length > 45 ? '...' : '')
    }

    let category = 'Estrategia'
    const lower = messageText.toLowerCase()
    if (lower.includes('outlier') || lower.includes('viral ratio')) category = 'Outliers'
    else if (lower.includes('packaging') || lower.includes('miniatura') || lower.includes('ctr')) category = 'Packaging'
    else if (lower.includes('guion') || lower.includes('hook') || lower.includes('retención')) category = 'Guion'

    handleCreateNote({ title, category, content })
    toast.success('Nota guardada en la columna lateral')
  }

  // 2. Handle Message Send with Streaming Reader and Abort Capability
  const handleStopChat = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
      abortControllerRef.current = null
    }
    setLoading(false)
    setCurrentTool(null)
    if (streamingMessage) {
      setMessages(prev => [
        ...prev,
        { role: 'assistant', content: streamingMessage + '\n\n*(Consulta detenida por el usuario)*', created_at: new Date().toISOString() }
      ])
      setStreamingMessage('')
    }
    toast('Consulta detenida', { icon: '⏹️' })
  }

  const handleSendMessage = async (text, attachments = []) => {
    if ((!text.trim() && (!attachments || attachments.length === 0)) || loading || !activeSessionId) return

    // Construir previsualización limpia del mensaje del usuario y payloads
    let displayText = ''
    const filesPayload = []
    const legacyImagesPayload = []

    if (attachments && attachments.length > 0) {
      attachments.forEach(att => {
        if (typeof att === 'string') {
          displayText += `![Referencia](${att})\n\n`
          legacyImagesPayload.push(att)
        } else if (att.type === 'image') {
          displayText += `![Referencia](${att.data})\n\n`
          filesPayload.push({
            name: att.name,
            type: 'image',
            data: att.data,
            size: att.size
          })
        } else if (att.type === 'pdf') {
          displayText += `📑 **Documento adjunto:** \`${att.name}\`${att.size ? ` *(${att.size})*` : ''}\n\n`
          filesPayload.push({
            name: att.name,
            type: 'pdf',
            data: att.data,
            size: att.size
          })
        } else if (att.type === 'text') {
          // Mostramos solo el badge del archivo en la burbuja visual (el contenido se envía en filesPayload)
          displayText += `📄 **Archivo adjunto:** \`${att.name}\`${att.size ? ` *(${att.size})*` : ''}\n\n`
          filesPayload.push({
            name: att.name,
            type: 'text',
            text: att.text,
            size: att.size
          })
        }
      })
    }

    displayText += text || (attachments.length > 0 ? 'Analiza los archivos adjuntos.' : '')

    const nowIso = new Date().toISOString()
    const userMsg = { role: 'user', content: displayText, created_at: nowIso }
    setMessages(prev => [...prev, userMsg])
    setSessions(prev => {
      const current = prev.find(s => s.id === activeSessionId)
      if (!current) return prev
      const updatedCurrent = { ...current, updated_at: nowIso }
      return [updatedCurrent, ...prev.filter(s => s.id !== activeSessionId)]
    })
    setLoading(true)
    setStreamingMessage('')
    setCurrentTool(null)

    // Auto-update title if it's the first message of "Nueva Conversación"
    if (activeSession?.title === 'Nueva Conversación' && messages.length === 0) {
      const autoTitle = (text || attachments[0]?.name || 'Análisis de Archivo').slice(0, 32)
      handleUpdateTitle(autoTitle)
    }

    const controller = new AbortController()
    abortControllerRef.current = controller

    try {
      const response = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: activeSessionId,
          message: text || 'Analiza los archivos adjuntos.',
          files: filesPayload.length > 0 ? filesPayload : undefined,
          images: legacyImagesPayload.length > 0 ? legacyImagesPayload : undefined
        }),
        signal: controller.signal
      })

      if (!response.body) throw new Error('No readable stream from server')

      const reader = response.body.getReader()
      const decoder = new TextDecoder('utf-8')
      let buffer = ''
      let fullAssistantContent = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n\n')
        buffer = lines.pop() // keep unparsed residue

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const event = JSON.parse(line.replace('data: ', '').trim())

              if (event.type === 'ping') {
                // Heartbeat to keep connection alive across proxies
                continue
              } else if (event.type === 'model_info') {
                setStatus(prev => ({ ...prev, active_gemini_model: event.model }))
              } else if (event.type === 'tool_start') {
                const rawName = event.message || event.tool || 'Procesando'
                const toolNamePretty = rawName.replace('herramienta_', '').replaceAll('_', ' ')
                setCurrentTool(toolNamePretty)
              } else if (event.type === 'tool_done') {
                setCurrentTool(null)
              } else if (event.type === 'content') {
                fullAssistantContent += event.content
                setStreamingMessage(fullAssistantContent)
              } else if (event.type === 'note_created') {
                const newNote = event.note
                setNotes(prev => [newNote, ...prev.filter(n => n.id !== newNote.id)])
                setExpandedNoteIds(prev => [newNote.id, ...prev.filter(id => id !== newNote.id)])
                setIsNotesOpen(true)
                try {
                  const currActive = activeSessionIdRef.current
                  if (currActive) {
                    const cached = localStorage.getItem(`yieldchat_cached_notes_${currActive}`)
                    const parsed = cached ? JSON.parse(cached) : []
                    const updated = [newNote, ...parsed.filter(n => n.id !== newNote.id)]
                    localStorage.setItem(`yieldchat_cached_notes_${currActive}`, JSON.stringify(updated))
                  }
                } catch (e) {}
                toast.success(`Nota guardada: ${newNote.title}`, { icon: '📌' })
              } else if (event.type === 'done') {
                setCurrentTool(null)
              } else if (event.type === 'error') {
                fullAssistantContent = `⚠️ **Aviso del Agente:** ${event.message || 'Error en la respuesta'}`
                setStreamingMessage(fullAssistantContent)
                toast.error(event.message || 'Error en la respuesta del agente')
              }
            } catch (err) {
              console.error('Error parsing SSE event', err)
            }
          }
        }
      }

      // Finalize message in state
      if (fullAssistantContent) {
        setMessages(prev => [
          ...prev,
          { role: 'assistant', content: fullAssistantContent, created_at: new Date().toISOString() }
        ])
        setStreamingMessage('')
      }
      fetchMemory() // refresh memory in case the agent stored a new insight
      fetchSyncStatus() // refresh sync status
    } catch (e) {
      if (e.name === 'AbortError') {
        console.log('Consulta abortada por el usuario.')
      } else {
        console.error('Error during streaming chat:', e)
        toast.error('Error al comunicarse con el servidor')
      }
    } finally {
      abortControllerRef.current = null
      setLoading(false)
      setCurrentTool(null)
    }
  }

  // 3. Memory handlers
  const handleAddInsight = async (newInsight) => {
    try {
      const res = await fetch(`${API_BASE}/memory`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newInsight)
      })
      const saved = await res.json()
      setInsights(prev => [...prev, saved])
      toast.success('Regla guardada en la memoria permanente')
      fetchSyncStatus()
    } catch (e) {
      toast.error('Error al guardar regla')
    }
  }

  const handleDeleteInsight = async (id) => {
    try {
      await fetch(`${API_BASE}/memory/${id}`, { method: 'DELETE' })
      setInsights(prev => prev.filter(i => i.id !== id))
      toast.success('Regla eliminada')
      fetchSyncStatus()
    } catch (e) {
      toast.error('Error al eliminar regla')
    }
  }

  // 4. GitHub Sync handler
  const handleSyncGitHub = async () => {
    if (syncing) return
    setSyncing(true)
    const toastId = toast.loading('Sincronizando memoria con GitHub...')
    try {
      const res = await fetch(`${API_BASE}/sync/github`, { method: 'POST' })
      const data = await res.json()
      if (!res.ok) {
        throw new Error(data.detail || 'Error al sincronizar con GitHub')
      }
      toast.success(data.message || 'Sincronizado con éxito', { id: toastId })
      fetchSyncStatus()
    } catch (e) {
      console.error('Error syncing with GitHub:', e)
      toast.error(e.message || 'Error al conectar con GitHub', { id: toastId })
      fetchSyncStatus()
    } finally {
      setSyncing(false)
    }
  }

  return (
    <div className="app-container">
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: '#161F2E',
            color: '#F1F5F9',
            border: '1px solid #1E293B',
            fontSize: '13px'
          }
        }}
      />

      <Sidebar
        sessions={sessions}
        folders={folders}
        activeSessionId={activeSessionId}
        onSelectSession={selectSession}
        onNewChat={handleNewChat}
        onDeleteSession={handleDeleteSession}
        onCreateFolder={handleCreateFolder}
        onUpdateFolder={handleUpdateFolder}
        onDeleteFolder={handleDeleteFolder}
        onMoveSessionToFolder={handleMoveSessionToFolder}
        onOpenMemory={() => {
          setIsSidebarOpen(false)
          setIsMemoryOpen(true)
        }}
        onOpenImageStudio={() => {
          setIsSidebarOpen(false)
          setIsImageStudioOpen(true)
        }}
        onSyncGitHub={handleSyncGitHub}
        syncing={syncing}
        syncStatus={syncStatus}
        status={status}
        isOpen={isSidebarOpen}
        onClose={() => setIsSidebarOpen(false)}
        isLoadingSessions={isLoadingSessions}
        sessionsError={sessionsError}
        onRetryLoadSessions={() => loadSessions()}
      />

      <ChatArea
        session={activeSession}
        messages={messages}
        streamingMessage={streamingMessage}
        currentTool={currentTool}
        loading={loading}
        isLoadingMessages={isLoadingMessages}
        onSendMessage={handleSendMessage}
        onUpdateTitle={handleUpdateTitle}
        onToggleSidebar={() => setIsSidebarOpen(prev => !prev)}
        onNewChat={() => handleNewChat()}
        onStop={handleStopChat}
        isSidebarOpen={isSidebarOpen}
        notesCount={notes.length}
        isNotesOpen={isNotesOpen}
        onToggleNotes={() => setIsNotesOpen(prev => !prev)}
        onOpenImageStudio={() => setIsImageStudioOpen(true)}
        onSaveAsNote={handleSaveMessageAsNote}
      />

      <NotesPanel
        isOpen={isNotesOpen}
        onClose={() => setIsNotesOpen(false)}
        notes={notes}
        expandedNoteIds={expandedNoteIds}
        onToggleExpandNote={handleToggleExpandNote}
        onCreateNote={handleCreateNote}
        onUpdateNote={handleUpdateNote}
        onDeleteNote={handleDeleteNote}
        activeSessionTitle={activeSession?.title}
      />

      <MemoryModal
        isOpen={isMemoryOpen}
        onClose={() => setIsMemoryOpen(false)}
        insights={insights}
        onAddInsight={handleAddInsight}
        onDeleteInsight={handleDeleteInsight}
        onSyncGitHub={handleSyncGitHub}
        syncing={syncing}
        syncStatus={syncStatus}
      />

      <ImageStudioModal
        isOpen={isImageStudioOpen}
        onClose={() => setIsImageStudioOpen(false)}
        folders={folders}
        activeFolderId={activeSession?.folder_id}
        activeSessionId={activeSessionId}
      />
    </div>
  )
}
