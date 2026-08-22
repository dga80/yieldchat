import React, { useState, useRef, useEffect } from 'react'
import { Send, Sparkles, Activity, Bot } from 'lucide-react'
import MessageItem from './MessageItem'

const QUICK_PROMPTS = [
  'Analizar el canal @TheWillWisdom y sus mejores outliers',
  '¿Cuántas palabras tienen los guiones de @CosmoExplainsYT?',
  'Generar 5 prompts de miniaturas estilo Ghibli para Mente Kaizen',
  'Buscar canales similares de religión y sueño en español'
]

export default function ChatArea({
  session,
  messages,
  streamingMessage,
  currentTool,
  loading,
  onSendMessage,
  onUpdateTitle
}) {
  const [input, setInput] = useState('')
  const [isEditingTitle, setIsEditingTitle] = useState(false)
  const [titleText, setTitleText] = useState('')
  const messagesEndRef = useRef(null)
  const textareaRef = useRef(null)

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

  const handleSend = () => {
    if (!input.trim() || loading) return
    onSendMessage(input.trim())
    setInput('')
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
                outline: 'none'
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

      {/* Messages List */}
      <div className="messages-container">
        {displayMessages.length === 0 ? (
          <div className="empty-state-wrapper">
            <div style={{ width: 48, height: 48, borderRadius: '50%', background: 'rgba(245, 158, 11, 0.1)', color: 'var(--gold)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px auto', boxShadow: '0 0 16px var(--gold-glow)' }}>
              <Bot size={26} />
            </div>
            <h2 style={{ fontSize: '1.25rem', color: '#fff', marginBottom: 8, fontWeight: 700 }}>¿En qué canal o nicho trabajamos hoy?</h2>
            <p style={{ fontSize: '14px', lineHeight: 1.6, color: 'var(--text-muted)' }}>
              Puedo auditar canales de YouTube en tiempo real, calcular la velocidad de vistas por día, extraer transcripciones de guiones o redactar prompts de miniaturas.
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
                  {currentTool ? `Consultando ${currentTool}...` : 'YieldChat está analizando y redactando...'}
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
                onClick={() => onSendMessage(prompt)}
              >
                {prompt}
              </button>
            ))}
          </div>
        )}

        <div className="chat-input-box">
          <textarea
            ref={textareaRef}
            className="chat-textarea"
            placeholder="Pregunta sobre cualquier canal, pide guiones, estadísticas o prompts..."
            value={input}
            onChange={handleInputResize}
            onKeyDown={handleKeyDown}
            rows={1}
            disabled={loading}
          />
          <div className="chat-input-footer">
            <span className="input-hint">Presiona Enter para enviar, Shift+Enter para nueva línea</span>
            <button
              className="send-btn"
              onClick={handleSend}
              disabled={!input.trim() || loading}
            >
              {loading ? <div className="spinner" style={{ width: 14, height: 14, borderWidth: 2, borderTopColor: '#000' }} /> : <Send size={15} />}
            </button>
          </div>
        </div>
      </div>
    </main>
  )
}
