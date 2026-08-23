import React, { useState, useEffect } from 'react'
import { Toaster, toast } from 'react-hot-toast'
import Sidebar from './components/Sidebar'
import ChatArea from './components/ChatArea'
import MemoryModal from './components/MemoryModal'

const API_BASE = '/api'

export default function App() {
  const [sessions, setSessions] = useState([])
  const [activeSessionId, setActiveSessionId] = useState(null)
  const [activeSession, setActiveSession] = useState(null)
  const [messages, setMessages] = useState([])
  const [streamingMessage, setStreamingMessage] = useState('')
  const [currentTool, setCurrentTool] = useState(null)
  const [loading, setLoading] = useState(false)
  const [status, setStatus] = useState(null)
  const [insights, setInsights] = useState([])
  const [isMemoryOpen, setIsMemoryOpen] = useState(false)
  const [syncing, setSyncing] = useState(false)

  // 1. Initial Load: Sessions, Memory and Status
  useEffect(() => {
    fetchStatus()
    fetchMemory()
    loadSessions()
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

  const fetchMemory = async () => {
    try {
      const res = await fetch(`${API_BASE}/memory`)
      const data = await res.json()
      setInsights(data)
    } catch (e) {
      console.error('Error fetching memory:', e)
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

  const handleNewChat = async () => {
    try {
      const res = await fetch(`${API_BASE}/sessions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: 'Nueva Conversación' })
      })
      const newSession = await res.json()
      setSessions(prev => [newSession, ...prev])
      selectSession(newSession.id)
    } catch (e) {
      toast.error('Error al crear nueva conversación')
    }
  }

  const handleDeleteSession = async (sessionId) => {
    try {
      await fetch(`${API_BASE}/sessions/${sessionId}`, { method: 'DELETE' })
      const updated = sessions.filter(s => s.id !== sessionId)
      setSessions(updated)
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

  // 2. Handle Message Send with Streaming Reader
  const handleSendMessage = async (text) => {
    if (!text.trim() || loading || !activeSessionId) return

    const userMsg = { role: 'user', content: text, created_at: new Date().toISOString() }
    setMessages(prev => [...prev, userMsg])
    setLoading(true)
    setStreamingMessage('')
    setCurrentTool(null)

    // Auto-update title if it's the first message of "Nueva Conversación"
    if (activeSession?.title === 'Nueva Conversación' && messages.length === 0) {
      const autoTitle = text.slice(0, 32) + (text.length > 32 ? '...' : '')
      handleUpdateTitle(autoTitle)
    }

    try {
      const response = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: activeSessionId,
          message: text
        })
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
    } catch (e) {
      console.error('Error during streaming chat:', e)
      toast.error('Error al comunicarse con el servidor')
    } finally {
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
    } catch (e) {
      toast.error('Error al guardar regla')
    }
  }

  const handleDeleteInsight = async (id) => {
    try {
      await fetch(`${API_BASE}/memory/${id}`, { method: 'DELETE' })
      setInsights(prev => prev.filter(i => i.id !== id))
      toast.success('Regla eliminada')
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
    } catch (e) {
      console.error('Error syncing with GitHub:', e)
      toast.error(e.message || 'Error al conectar con GitHub', { id: toastId })
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
        activeSessionId={activeSessionId}
        onSelectSession={selectSession}
        onNewChat={handleNewChat}
        onDeleteSession={handleDeleteSession}
        onOpenMemory={() => setIsMemoryOpen(true)}
        onSyncGitHub={handleSyncGitHub}
        syncing={syncing}
        status={status}
      />

      <ChatArea
        session={activeSession}
        messages={messages}
        streamingMessage={streamingMessage}
        currentTool={currentTool}
        loading={loading}
        onSendMessage={handleSendMessage}
        onUpdateTitle={handleUpdateTitle}
      />

      <MemoryModal
        isOpen={isMemoryOpen}
        onClose={() => setIsMemoryOpen(false)}
        insights={insights}
        onAddInsight={handleAddInsight}
        onDeleteInsight={handleDeleteInsight}
        onSyncGitHub={handleSyncGitHub}
        syncing={syncing}
      />
    </div>
  )
}
