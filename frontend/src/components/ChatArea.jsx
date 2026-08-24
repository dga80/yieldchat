import React, { useState, useRef, useEffect } from 'react'
import { Send, Sparkles, Activity, Bot, ImagePlus, X, Paperclip, Menu } from 'lucide-react'
import MessageItem from './MessageItem'

const QUICK_PROMPTS = [
  'Generar una miniatura de alto CTR sobre hábitos de riqueza',
  'Aprende el estilo de esta imagen de referencia y guárdalo',
  'Analizar el canal @TheWillWisdom y sus mejores outliers',
  'Generar un fondo vertical para un YouTube Short'
]

export default function ChatArea({
  session,
  messages,
  streamingMessage,
  currentTool,
  loading,
  onSendMessage,
  onUpdateTitle,
  onToggleSidebar
}) {
  const [input, setInput] = useState('')
  const [attachments, setAttachments] = useState([]) // [{ id, data, name }]
  const [isEditingTitle, setIsEditingTitle] = useState(false)
  const [titleText, setTitleText] = useState('')
  const messagesEndRef = useRef(null)
  const textareaRef = useRef(null)
  const fileInputRef = useRef(null)

  useEffect(() => {
    if (session) {
      setTitleText(session.title)
    }
  }, [session])

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages, streamingMessage, currentTool])

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleFiles = (files) => {
    if (!files || files.length === 0) return
    Array.from(files).forEach(file => {
      if (!file.type.startsWith('image/')) return
      const reader = new FileReader()
      reader.onload = (e) => {
        setAttachments(prev => [
          ...prev,
          { id: Math.random().toString(36).substring(7), data: e.target.result, name: file.name }
        ])
      }
      reader.readAsDataURL(file)
    })
  }

  const handlePaste = (e) => {
    const items = e.clipboardData?.items
    if (!items) return
    const imageFiles = []
    for (let i = 0; i < items.length; i++) {
      if (items[i].type.startsWith('image/')) {
        const file = items[i].getAsFile()
        if (file) imageFiles.push(file)
      }
    }
    if (imageFiles.length > 0) {
      e.preventDefault()
      handleFiles(imageFiles)
    }
  }

  const removeAttachment = (id) => {
    setAttachments(prev => prev.filter(a => a.id !== id))
  }

  const handleSend = () => {
    if ((!input.trim() && attachments.length === 0) || loading) return
    const imagesPayload = attachments.map(a => a.data)
    onSendMessage(input.trim(), imagesPayload)
    setInput('')
    setAttachments([])
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }
  }

  const handleInputResize = (e) => {
    setInput(e.target.value)
    e.target.style.height = 'auto'
    e.target.style.height = `${Math.min(e.target.scrollHeight, 180)}px`
  }

  const handleTitleSubmit = () => {
    setIsEditingTitle(false)
    if (titleText.trim() && titleText !== session.title) {
      onUpdateTitle(titleText.trim())
    }
  }

  const displayMessages = [...messages]
  if (streamingMessage) {
    displayMessages.push({
      id: 'streaming-agent',
      role: 'assistant',
      content: streamingMessage
    })
  }

  return (
    <main className="chat-main">
      {/* Header */}
      <div className="chat-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, flex: 1, minWidth: 0 }}>
          <button 
            className="mobile-menu-btn" 
            onClick={onToggleSidebar}
            title="Abrir menú"
            aria-label="Abrir menú"
          >
            <Menu size={20} />
          </button>
          <div className="chat-header-title">
            {isEditingTitle ? (
              <input
                type="text"
                value={titleText}
                onChange={e => setTitleText(e.target.value)}
                onBlur={handleTitleSubmit}
                onKeyDown={e => e.key === 'Enter' && handleTitleSubmit()}
                autoFocus
                style={{
                  background: '#161F2E',
                  border: '1px solid var(--border-focus)',
                  color: 'var(--text-main)',
                  padding: '4px 8px',
                  borderRadius: '4px',
                  fontSize: '14px',
                  outline: 'none',
                  maxWidth: '100%'
                }}
              />
            ) : (
              <span
                onClick={() => setIsEditingTitle(true)}
                style={{ cursor: 'pointer' }}
                title="Haz clic para renombrar"
              >
                {session?.title || 'Conversación'}
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Messages List */}
      <div className="messages-container">
        {displayMessages.length === 0 ? (
          <div className="empty-state-wrapper">
            <div style={{ width: 48, height: 48, borderRadius: '50%', background: 'rgba(245, 158, 11, 0.1)', color: 'var(--gold)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px auto', boxShadow: '0 0 16px var(--gold-glow)' }}>
              <Bot size={26} />
            </div>
            <h2 style={{ fontSize: '1.25rem', color: '#fff', marginBottom: 8, fontWeight: 700 }}>¿En qué canal o estrategia trabajamos hoy?</h2>
            <p style={{ fontSize: '14px', lineHeight: 1.6, color: 'var(--text-muted)' }}>
              Puedo auditar canales, generar miniaturas en alta definición con IA, aprender estilos visuales de tus imágenes de referencia y redactar guiones optimizados.
            </p>
          </div>
        ) : (
          displayMessages.map((msg, idx) => (
            <MessageItem key={msg.id || idx} message={msg} />
          ))
        )}

        {/* Thinking / Tool Execution Indicator */}
        {loading && !streamingMessage && (
          <div className="message-row">
            <div className="message-avatar avatar-agent pulse-avatar">
              <Bot size={18} />
            </div>
            <div className="message-body">
              <div className="thinking-bubble">
                <div className="typing-dots">
                  <span className="dot" />
                  <span className="dot" />
                  <span className="dot" />
                </div>
                <span className="thinking-text">
                  {currentTool ? `Ejecutando ${currentTool}...` : 'YieldChat está procesando y creando...'}
                </span>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="input-area-wrapper">
        {displayMessages.length === 0 && (
          <div className="quick-prompts">
            {QUICK_PROMPTS.map((prompt, i) => (
              <button
                key={i}
                className="quick-pill"
                onClick={() => onSendMessage(prompt, [])}
              >
                {prompt}
              </button>
            ))}
          </div>
        )}

        <div className="chat-input-box">
          {/* Attached Images Preview */}
          {attachments.length > 0 && (
            <div className="attachment-preview-bar">
              {attachments.map(att => (
                <div key={att.id} className="attachment-chip">
                  <img src={att.data} alt="Referencia" className="attachment-thumb" />
                  <span className="attachment-name">{att.name}</span>
                  <button 
                    className="remove-attachment-btn" 
                    onClick={() => removeAttachment(att.id)}
                    title="Quitar imagen"
                  >
                    <X size={12} />
                  </button>
                </div>
              ))}
            </div>
          )}

          <textarea
            ref={textareaRef}
            className="chat-textarea"
            placeholder="Escribe tu consulta o arrastra/pega imágenes de referencia..."
            value={input}
            onChange={handleInputResize}
            onKeyDown={handleKeyDown}
            onPaste={handlePaste}
            rows={1}
            disabled={loading}
          />

          <div className="chat-input-footer">
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <input
                type="file"
                ref={fileInputRef}
                style={{ display: 'none' }}
                multiple
                accept="image/*"
                onChange={(e) => handleFiles(e.target.files)}
              />
              <button
                type="button"
                className="attach-btn"
                onClick={() => fileInputRef.current?.click()}
                title="Adjuntar imagen de referencia para que el agente aprenda o se inspire"
              >
                <ImagePlus size={16} />
                <span>Adjuntar Referencia</span>
              </button>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <span className="input-hint">Enter para enviar</span>
              <button
                className="send-btn"
                onClick={handleSend}
                disabled={(!input.trim() && attachments.length === 0) || loading}
              >
                {loading ? <div className="spinner" style={{ width: 14, height: 14, borderWidth: 2, borderTopColor: '#000' }} /> : <Send size={15} />}
              </button>
            </div>
          </div>
        </div>
      </div>
    </main>
  )
}
