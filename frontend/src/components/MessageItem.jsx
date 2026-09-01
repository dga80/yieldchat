import React, { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Copy, Check, Bot, User, Download, ExternalLink, Sparkles } from 'lucide-react'
import toast from 'react-hot-toast'

function MessageItemComponent({ message }) {
  const isUser = message.role === 'user'

  return (
    <div className="message-row">
      <div className={`message-avatar ${isUser ? 'avatar-user' : 'avatar-agent'}`}>
        {isUser ? <User size={16} /> : <Bot size={18} />}
      </div>

      <div className="message-body">
        {isUser ? (
          <div className="message-user-content">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                img({ node, src, alt, ...props }) {
                  return (
                    <div className="user-attached-image-wrapper">
                      <img src={src} alt={alt || 'Referencia visual'} className="user-attached-img" />
                      <span className="user-attached-tag">Referencia visual adjunta</span>
                    </div>
                  )
                }
              }}
            >
              {message.content}
            </ReactMarkdown>
          </div>
        ) : (
          <div className="message-agent-content">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                img({ node, src, alt, ...props }) {
                  return <ImageCard src={src} alt={alt} />
                },
                code({ node, inline, className, children, ...props }) {
                  const match = /language-(\w+)/.exec(className || '')
                  const codeText = String(children).replace(/\n$/, '')

                  if (inline) {
                    return (
                      <code style={{ background: '#1E293B', color: '#F59E0B', padding: '2px 6px', borderRadius: '4px', fontFamily: 'var(--font-mono)', fontSize: '0.9em' }}>
                        {children}
                      </code>
                    )
                  }

                  return (
                    <CodeBlock text={codeText} language={match ? match[1] : 'text'} />
                  )
                },
                a({ node, href, children, ...props }) {
                  return (
                    <a
                      href={href}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{ color: '#3B82F6', textDecoration: 'underline', fontWeight: 500 }}
                      {...props}
                    >
                      {children}
                    </a>
                  )
                }
              }}
            >
              {message.content}
            </ReactMarkdown>
          </div>
        )}
      </div>
    </div>
  )
}

const ImageCard = React.memo(function ImageCard({ src, alt }) {
  const [downloading, setDownloading] = useState(false)

  const handleDownload = async () => {
    setDownloading(true)
    try {
      const response = await fetch(src)
      const blob = await response.blob()
      const blobUrl = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = blobUrl
      link.download = `yieldchat_${Date.now()}.jpg`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(blobUrl)
      toast.success('Imagen descargada en HD')
    } catch (e) {
      toast.error('Error al descargar la imagen')
    } finally {
      setDownloading(false)
    }
  }

  return (
    <div className="generated-image-card">
      <div className="image-card-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <Sparkles size={14} color="#F59E0B" />
          <span style={{ fontSize: '12px', fontWeight: 600, color: '#F59E0B' }}>Miniatura IA Generada</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <button className="image-action-btn" onClick={handleDownload} title="Descargar imagen en alta calidad">
            <Download size={13} />
            <span>{downloading ? 'Descargando...' : 'Descargar HD'}</span>
          </button>
          <a href={src} target="_blank" rel="noopener noreferrer" className="image-action-btn" title="Abrir en pestaña nueva">
            <ExternalLink size={13} />
          </a>
        </div>
      </div>
      <div className="image-preview-container">
        <img src={src} alt={alt || 'Imagen generada'} className="generated-img" loading="lazy" />
      </div>
    </div>
  )
})

const CodeBlock = React.memo(function CodeBlock({ text, language }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = () => {
    navigator.clipboard.writeText(text)
    setCopied(true)
    toast.success('Prompt copiado al portapapeles')
    setTimeout(() => setCopied(false), 2000)
  }

  const isPrompt = text.toLowerCase().includes('--ar') || text.toLowerCase().includes('illustration') || text.toLowerCase().includes('anime')

  return (
    <div className="code-container">
      <div className="code-header">
        <span>{isPrompt ? 'PROMPT DE IMAGEN' : language.toUpperCase()}</span>
        <button className="copy-btn" onClick={handleCopy}>
          {copied ? (
            <>
              <Check size={12} /> Copiado
            </>
          ) : (
            <>
              <Copy size={12} /> {isPrompt ? 'Copiar Prompt' : 'Copiar'}
            </>
          )}
        </button>
      </div>
      <pre>{text}</pre>
    </div>
  )
})

const MessageItem = React.memo(MessageItemComponent, (prevProps, nextProps) => {
  return prevProps.message.id === nextProps.message.id &&
         prevProps.message.content === nextProps.message.content &&
         prevProps.message.role === nextProps.message.role
})

export default MessageItem
