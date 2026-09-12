import React, { useState, useRef, useEffect, useCallback } from 'react'
import { Send, Sparkles, Activity, Bot, ImagePlus, X, Paperclip, Square, FileText, FileCode, UploadCloud, Menu, PanelLeft, Plus, SquarePen, RefreshCw } from 'lucide-react'
import MessageItem from './MessageItem'

const QUICK_PROMPTS = [
  'Generar una miniatura de alto CTR sobre hábitos de riqueza',
  'Aprende el estilo de esta imagen de referencia y guárdalo',
  'Analizar el canal @TheWillWisdom y sus mejores outliers',
  'Generar un fondo vertical para un YouTube Short'
]

function formatFileSize(bytes) {
  if (!bytes || bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
}

export default function ChatArea({
  session,
  messages,
  streamingMessage,
  currentTool,
  loading,
  isLoadingMessages = false,
  onSendMessage,
  onUpdateTitle,
  onToggleSidebar,
  onNewChat,
  onStop,
  isSidebarOpen
}) {
  const [isEditingTitle, setIsEditingTitle] = useState(false)
  const [titleText, setTitleText] = useState('')
  const messagesContainerRef = useRef(null)
  const messagesEndRef = useRef(null)

  useEffect(() => {
    if (session) {
      setTitleText(session.title)
    }
  }, [session])

  const scrollToBottom = () => {
    if (messagesContainerRef.current) {
      messagesContainerRef.current.scrollTop = messagesContainerRef.current.scrollHeight
    }
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages, streamingMessage, currentTool])

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
      {/* Header estilo Gemini App */}
      <header className="chat-header">
        <button 
          className="gemini-menu-btn" 
          onClick={onToggleSidebar}
          title={isSidebarOpen ? "Ocultar menú" : "Abrir conversaciones"}
          aria-label="Abrir menú de conversaciones"
        >
          <Menu size={20} />
        </button>

        <div className="chat-header-center">
          <span className="app-title-badge">
            <Sparkles size={15} style={{ color: 'var(--gold)' }} />
            <span>YieldChat</span>
          </span>
          {session?.title && session.title !== 'Nueva Conversación' && (
            <>
              <span className="chat-title-separator">/</span>
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
                    padding: '2px 8px',
                    borderRadius: '4px',
                    fontSize: '13px',
                    outline: 'none',
                    maxWidth: '180px'
                  }}
                />
              ) : (
                <span
                  className="chat-header-session-title"
                  onClick={() => setIsEditingTitle(true)}
                  title="Haz clic para renombrar"
                >
                  {session.title}
                </span>
              )}
            </>
          )}
        </div>

        <button
          className="gemini-new-btn"
          onClick={() => onNewChat?.()}
          title="Nueva conversación"
          aria-label="Nueva conversación"
        >
          <SquarePen size={19} />
        </button>
      </header>

      {/* Messages List */}
      <div className="messages-container" ref={messagesContainerRef}>
        {isLoadingMessages && displayMessages.length === 0 ? (
          <div className="empty-state-wrapper">
            <RefreshCw size={28} className="spin-icon" style={{ color: 'var(--gold)', margin: '0 auto 14px auto' }} />
            <h2 style={{ fontSize: '1.15rem', color: '#fff', marginBottom: 8, fontWeight: 600 }}>Cargando conversación...</h2>
            <p style={{ fontSize: '13px', lineHeight: 1.6, color: 'var(--text-muted)' }}>
              Recuperando historial y contexto estratégico...
            </p>
          </div>
        ) : displayMessages.length === 0 ? (
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
            <MessageItem 
              key={msg.id || `msg-${idx}-${msg.role}`} 
              message={msg} 
            />
          ))
        )}

        {/* Thinking / Tool Execution Indicator */}
        {loading && !streamingMessage && (
          <div className="message-row">
            <div className="message-avatar avatar-agent pulse-avatar">
              <Bot size={18} />
            </div>
            <div className="message-body">
              <div className="thinking-bubble" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: 'fit-content' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <div className="typing-dots">
                    <span className="dot" />
                    <span className="dot" />
                    <span className="dot" />
                  </div>
                  <span className="thinking-text">
                    {currentTool ? `Ejecutando ${currentTool}...` : 'YieldChat está procesando y creando...'}
                  </span>
                </div>
                {onStop && (
                  <button
                    type="button"
                    className="stop-bubble-btn"
                    onClick={onStop}
                    title="Detener consulta actual"
                  >
                    <Square size={10} fill="currentColor" />
                    <span>Detener</span>
                  </button>
                )}
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Area (Isolated to prevent re-rendering message list on keystrokes) */}
      <ChatInputBox 
        loading={loading}
        onSendMessage={onSendMessage}
        onStop={onStop}
        showQuickPrompts={displayMessages.length === 0}
      />
    </main>
  )
}

/**
 * Isolated ChatInputBox Component
 * Keystrokes inside this component only re-render the input box itself,
 * ensuring zero-latency typing regardless of conversation history size.
 */
const ChatInputBox = React.memo(function ChatInputBox({
  loading,
  onSendMessage,
  onStop,
  showQuickPrompts
}) {
  const [input, setInput] = useState('')
  const [attachments, setAttachments] = useState([])
  const [isDragging, setIsDragging] = useState(false)
  const textareaRef = useRef(null)
  const fileInputRef = useRef(null)

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleFiles = (files) => {
    if (!files || files.length === 0) return
    const imageExtensions = ['jpg', 'jpeg', 'png', 'webp', 'gif', 'svg', 'bmp', 'ico', 'avif', 'heic']
    const codeExtensions = ['js', 'jsx', 'ts', 'tsx', 'py', 'html', 'css', 'json', 'sql', 'sh', 'yaml', 'yml', 'md', 'markdown']
    const spreadsheetExtensions = ['csv', 'tsv', 'xlsx', 'xls']

    Array.from(files).forEach(file => {
      const ext = file.name.split('.').pop()?.toLowerCase() || ''
      const isImg = file.type.startsWith('image/') || imageExtensions.includes(ext)
      const isPdf = file.type === 'application/pdf' || ext === 'pdf'
      const isCode = codeExtensions.includes(ext)
      const isSheet = spreadsheetExtensions.includes(ext)
      const sizeStr = formatFileSize(file.size)

      if (isImg) {
        const reader = new FileReader()
        reader.onload = (e) => {
          setAttachments(prev => [
            ...prev,
            {
              id: Math.random().toString(36).substring(7),
              name: file.name,
              type: 'image',
              extension: ext || 'img',
              data: e.target.result,
              size: sizeStr
            }
          ])
        }
        reader.readAsDataURL(file)
      } else if (isPdf) {
        const reader = new FileReader()
        reader.onload = (e) => {
          setAttachments(prev => [
            ...prev,
            {
              id: Math.random().toString(36).substring(7),
              name: file.name,
              type: 'pdf',
              extension: 'pdf',
              data: e.target.result,
              size: sizeStr
            }
          ])
        }
        reader.readAsDataURL(file)
      } else {
        const reader = new FileReader()
        reader.onload = (e) => {
          setAttachments(prev => [
            ...prev,
            {
              id: Math.random().toString(36).substring(7),
              name: file.name,
              type: isCode ? 'code' : isSheet ? 'spreadsheet' : 'text',
              extension: ext || 'txt',
              text: e.target.result,
              size: sizeStr
            }
          ])
        }
        reader.readAsText(file)
      }
    })

    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const handlePaste = (e) => {
    const items = e.clipboardData?.items
    if (!items) return
    const pastedFiles = []
    for (let i = 0; i < items.length; i++) {
      if (items[i].kind === 'file') {
        const file = items[i].getAsFile()
        if (file) pastedFiles.push(file)
      }
    }
    if (pastedFiles.length > 0) {
      e.preventDefault()
      handleFiles(pastedFiles)
    }
  }

  const handleDragOver = (e) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(true)
  }

  const handleDragLeave = (e) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)
  }

  const handleDrop = (e) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)
    if (e.dataTransfer?.files && e.dataTransfer.files.length > 0) {
      handleFiles(e.dataTransfer.files)
    }
  }

  const removeAttachment = (id) => {
    setAttachments(prev => prev.filter(a => a.id !== id))
  }

  const handleSend = () => {
    if ((!input.trim() && attachments.length === 0) || loading) return
    onSendMessage(input.trim(), attachments)
    setInput('')
    setAttachments([])
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }
  }

  const handleInputResize = (e) => {
    const val = e.target.value
    setInput(val)
    const target = e.target
    target.style.height = 'auto'
    target.style.height = `${Math.min(target.scrollHeight, 180)}px`
  }

  return (
    <div className="input-area-wrapper">
      {showQuickPrompts && (
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

      <div 
        className={`chat-input-box ${isDragging ? 'dragging-over' : ''}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        {/* Attached Files & Images Preview */}
        {attachments.length > 0 && (
          <div className="attachment-preview-bar">
            {attachments.map(att => (
              <div key={att.id} className={`attachment-chip ${att.type}`}>
                {att.type === 'image' ? (
                  <div className="attachment-image-thumb-wrap">
                    <img src={att.data} alt="Miniatura" className="attachment-thumb" />
                    <span className="attachment-type-tag">IMG</span>
                  </div>
                ) : att.type === 'pdf' ? (
                  <div className="attachment-file-badge pdf-badge">
                    <FileText size={18} />
                    <span className="badge-sub">PDF</span>
                  </div>
                ) : att.type === 'code' ? (
                  <div className="attachment-file-badge code-badge">
                    <FileCode size={18} />
                    <span className="badge-sub">{att.extension?.toUpperCase() || 'CODE'}</span>
                  </div>
                ) : att.type === 'spreadsheet' ? (
                  <div className="attachment-file-badge sheet-badge">
                    <FileText size={18} />
                    <span className="badge-sub">{att.extension?.toUpperCase() || 'DATA'}</span>
                  </div>
                ) : (
                  <div className="attachment-file-badge txt-badge">
                    <FileText size={18} />
                    <span className="badge-sub">{att.extension?.toUpperCase() || 'TXT'}</span>
                  </div>
                )}
                <div className="attachment-meta">
                  <span className="attachment-name" title={att.name}>{att.name}</span>
                  <div className="attachment-sub-meta">
                    <span className="attachment-type-pill">{att.type === 'image' ? 'Imagen' : att.type === 'pdf' ? 'PDF' : 'Archivo'}</span>
                    {att.size && <span className="attachment-size">{att.size}</span>}
                  </div>
                </div>
                <button 
                  type="button"
                  className="remove-attachment-btn" 
                  onClick={() => removeAttachment(att.id)}
                  title="Quitar archivo"
                >
                  <X size={14} />
                </button>
              </div>
            ))}
          </div>
        )}

        {isDragging && (
          <div className="drag-drop-overlay">
            <UploadCloud size={24} />
            <span>Suelta los archivos aquí para adjuntarlos</span>
          </div>
        )}

        <textarea
          ref={textareaRef}
          className="chat-textarea"
          placeholder="Escribe tu consulta o arrastra/pega texto, PDFs o imágenes de referencia..."
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
              accept="image/*,.txt,.md,.markdown,.json,.csv,.pdf,.py,.js,.jsx,.ts,.tsx,.html,.css,.yaml,.yml,.log,.tsv,.docx,.doc"
              onChange={(e) => handleFiles(e.target.files)}
            />
            <button
              type="button"
              className="attach-btn"
              onClick={() => fileInputRef.current?.click()}
              title="Adjuntar archivos de texto (.txt, .md, .csv, .json), PDFs o imágenes de referencia"
              disabled={loading}
            >
              <Paperclip size={15} />
              <span>Adjuntar Archivo</span>
            </button>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span className="input-hint">{loading ? 'Generando respuesta...' : 'Enter para enviar'}</span>
            {loading ? (
              <button
                type="button"
                className="stop-btn"
                onClick={onStop}
                title="Detener generación"
              >
                <Square size={12} fill="currentColor" />
                <span>Detener</span>
              </button>
            ) : (
              <button
                type="button"
                className="send-btn"
                onClick={handleSend}
                disabled={(!input.trim() && attachments.length === 0)}
                title="Enviar consulta"
              >
                <Send size={15} />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
})
