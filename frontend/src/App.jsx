import React, { useState, useEffect, useRef } from 'react'
import { Toaster, toast } from 'react-hot-toast'
import Sidebar from './components/Sidebar'
import ChatArea from './components/ChatArea'
import MemoryModal from './components/MemoryModal'

const API_BASE = import.meta.env.VITE_API_URL || '/api'

export default function App() {
  const [sessions, setSessions] = useState([])
  const [folders, setFolders] = useState([])
  const [activeSessionId, setActiveSessionId] = useState(null)
  const [activeSession, setActiveSession] = useState(null)
  const [messages, setMessages] = useState([])
  const [streamingMessage, setStreamingMessage] = useState('')
  const [currentTool, setCurrentTool] = useState(null)
  const [loading, setLoading] = useState(false)
  const [status, setStatus] = useState(null)
  const [insights, setInsights] = useState([])
  const [isMemoryOpen, setIsMemoryOpen] = useState(false)
  const [isSidebarOpen, setIsSidebarOpen] = useState(false)
  const [syncing, setSyncing] = useState(false)
  const [syncStatus, setSyncStatus] = useState(null)
  const abortControllerRef = useRef(null)

  // 1. Initial Load: Sessions, Folders, Memory, Status and Sync
  useEffect(() => {
    fetchStatus()
    fetchMemory()
    fetchSyncStatus()
    fetchFolders()
    loadSessions()

    // Intervalo de comprobación de estado de sincronización cada 20 segundos
    const syncInterval = setInterval(() => {
      fetchSyncStatus()
    }, 20000)

    return () => clearInterval(syncInterval)
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
    } catch (e) {
      console.error('Error fetching folders:', e)
    }
  }

  const loadSessions = async () => {
    try {
      const res = await fetch(`${API_BASE}/sessions`)
      const data = await res.json()
      setSessions(data)
      if (data.length > 0 && !activeSessionId) {
        selectSession(data[0].id)
      } else if (data.length === 0) {
        handleNewChat()
      }
    } catch (e) {
      console.error('Error loading sessions:', e)
    }
  }

  const selectSession = async (sessionId) => {
    setActiveSessionId(sessionId)
    setStreamingMessage('')
    setCurrentTool(null)
    setIsSidebarOpen(false)
    try {
      const res = await fetch(`${API_BASE}/sessions/${sessionId}`)
      const data = await res.json()
      setActiveSession(data)
      setMessages(data.messages || [])
    } catch (e) {
      console.error('Error fetching session:', e)
      toast.error('Error al cargar la conversación')
    }
  }

  const handleNewChat = async (folderId = null) => {
    setIsSidebarOpen(false)
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

    const userMsg = { role: 'user', content: displayText, created_at: new Date().toISOString() }
    setMessages(prev => [...prev, userMsg])
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

              if (event.type === 'model_info') {
                setStatus(prev => ({ ...prev, active_gemini_model: event.model }))
              } else if (event.type === 'tool_start') {
                const toolNamePretty = event.tool.replace('herramienta_', '').replaceAll('_', ' ')
                setCurrentTool(toolNamePretty)
              } else if (event.type === 'tool_done') {
                setCurrentTool(null)
              } else if (event.type === 'content') {
                fullAssistantContent += event.content
                setStreamingMessage(fullAssistantContent)
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
        onSyncGitHub={handleSyncGitHub}
        syncing={syncing}
        syncStatus={syncStatus}
        status={status}
        isOpen={isSidebarOpen}
        onClose={() => setIsSidebarOpen(false)}
      />

      <ChatArea
        session={activeSession}
        messages={messages}
        streamingMessage={streamingMessage}
        currentTool={currentTool}
        loading={loading}
        onSendMessage={handleSendMessage}
        onUpdateTitle={handleUpdateTitle}
        onToggleSidebar={() => setIsSidebarOpen(prev => !prev)}
        onStop={handleStopChat}
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
    </div>
  )
}
