import React, { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import {
  Copy,
  Check,
  Bot,
  User,
  Download,
  ExternalLink,
  Sparkles,
  FileText,
  FileCode,
  FileSpreadsheet,
  Maximize2,
  X,
  Eye,
  StickyNote
} from 'lucide-react'
import toast from 'react-hot-toast'
import { downloadTextAsFile } from '../utils/fileDownloader'

function parseAttachmentLine(str) {
  if (typeof str !== 'string') return null
  const isAttachment = str.includes('Archivo adjunto:') || str.includes('Documento adjunto:') || str.includes('Documento PDF adjunto:')
  if (!isAttachment) return null

  let filename = ''
  let size = ''
  let url = null

  const linkMatch = str.match(/\[([^\]]+)\]\(([^)]+)\)/)
  if (linkMatch) {
    filename = linkMatch[1]
    url = linkMatch[2]
  } else {
    const codeMatch = str.match(/`([^`]+)`/)
    if (codeMatch) {
      filename = codeMatch[1]
    }
  }

  const sizeMatch = str.match(/\*\(([^)]+)\)\*/)
  if (sizeMatch) {
    size = sizeMatch[1]
  }

  if (!filename) return null

  const ext = filename.split('.').pop()?.toLowerCase() || ''
  const isPdf = ext === 'pdf' || str.toLowerCase().includes('pdf')
  const isCode = ['py', 'js', 'jsx', 'ts', 'tsx', 'html', 'css', 'json', 'sql', 'sh', 'yaml', 'yml'].includes(ext)
  const isSheet = ['csv', 'tsv', 'xlsx', 'xls'].includes(ext)

  return {
    filename,
    size,
    url,
    extension: ext || 'txt',
    type: isPdf ? 'pdf' : isCode ? 'code' : isSheet ? 'spreadsheet' : 'text'
  }
}

function MessageItemComponent({ message, onSaveAsNote }) {
  const isUser = message.role === 'user'
  const [lightboxImg, setLightboxImg] = useState(null)
  const [isCopied, setIsCopied] = useState(false)

  const handleCopyFullMessage = () => {
    navigator.clipboard.writeText(message.content)
    setIsCopied(true)
    toast.success('Respuesta copiada')
    setTimeout(() => setIsCopied(false), 2000)
  }

  const handleDownloadMessageTxt = () => {
    let filename = 'respuesta_yieldchat.txt'
    const firstLine = message.content.split('\n').find(l => l.trim().length > 0) || ''
    if (firstLine) {
      const clean = firstLine.replace(/[^a-zA-Z0-9áéíóúÁÉÍÓÚñÑ\s_-]/g, '').trim().slice(0, 35).replace(/\s+/g, '_').toLowerCase()
      if (clean) filename = `${clean}.txt`
    }
    downloadTextAsFile(filename, message.content)
  }

  return (
    <>
      <div className={`message-row ${isUser ? 'user-row' : 'agent-row'}`}>
        <div className={`message-avatar ${isUser ? 'avatar-user' : 'avatar-agent'}`}>
          {isUser ? <User size={16} /> : <Bot size={18} />}
        </div>

        <div className="message-body">
          {isUser ? (
            <div className="message-user-content">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  p({ node, children, ...props }) {
                    // Comprobar si el texto del párrafo describe un archivo adjunto
                    const textContent = React.Children.toArray(children)
                      .map(child => (typeof child === 'string' ? child : child?.props?.children || ''))
                      .join('')

                    const attachmentInfo = parseAttachmentLine(textContent)
                    if (attachmentInfo) {
                      return <UserFileAttachmentCard info={attachmentInfo} />
                    }

                    return <p {...props}>{children}</p>
                  },
                  img({ node, src, alt, ...props }) {
                    return (
                      <UserImageAttachmentCard
                        src={src}
                        alt={alt || 'Referencia visual'}
                        onOpenLightbox={() => setLightboxImg(src)}
                      />
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
                    return <ImageCard src={src} alt={alt} onOpenLightbox={() => setLightboxImg(src)} />
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

              {message.id !== 'streaming-agent' && !message.isStreaming && (
                <div className="message-agent-footer-actions">
                <button
                  type="button"
                  className="msg-footer-action-btn"
                  onClick={handleCopyFullMessage}
                  title="Copiar texto completo"
                >
                  {isCopied ? <Check size={12} style={{ color: 'var(--green)' }} /> : <Copy size={12} />}
                  <span>{isCopied ? 'Copiado' : 'Copiar'}</span>
                </button>
                <button
                  type="button"
                  className="msg-footer-action-btn note-download-btn"
                  onClick={handleDownloadMessageTxt}
                  title="Descargar esta respuesta completa en archivo .txt"
                >
                  <Download size={12} style={{ color: '#38BDF8' }} />
                  <span>Descargar .txt</span>
                </button>
                {onSaveAsNote && (
                  <button
                    type="button"
                    className="msg-footer-action-btn note-save-btn"
                    onClick={() => onSaveAsNote(message.content)}
                    title="Guardar esta respuesta como nota en la columna derecha"
                  >
                    <StickyNote size={12} style={{ color: 'var(--gold)' }} />
                    <span>Guardar como nota</span>
                  </button>
                )}
              </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Lightbox Modal para ver imágenes adjuntas en grande */}
      {lightboxImg && (
        <div className="lightbox-overlay" onClick={() => setLightboxImg(null)}>
          <div className="lightbox-content" onClick={e => e.stopPropagation()}>
            <button 
              className="lightbox-close-btn" 
              onClick={() => setLightboxImg(null)}
              title="Cerrar vista previa"
            >
              <X size={20} />
            </button>
            <img src={lightboxImg} alt="Vista previa completa" className="lightbox-image" />
            <div className="lightbox-footer">
              <a 
                href={lightboxImg} 
                target="_blank" 
                rel="noreferrer" 
                className="lightbox-action-btn"
                download
              >
                <Download size={14} />
                <span>Descargar archivo</span>
              </a>
            </div>
          </div>
        </div>
      )}
    </>
  )
}

/**
 * Tarjeta para imágenes adjuntas por el usuario con miniatura y botón de zoom
 */
function UserImageAttachmentCard({ src, alt, onOpenLightbox }) {
  return (
    <div className="user-attached-image-card">
      <div className="user-attached-thumb-container" onClick={onOpenLightbox} title="Clic para ampliar imagen">
        <img src={src} alt={alt} className="user-attached-img" />
        <div className="user-attached-hover-overlay">
          <Maximize2 size={16} />
          <span>Ampliar</span>
        </div>
      </div>
      <div className="user-attached-caption">
        <span className="user-attached-tag">📷 Imagen adjunta</span>
        <button type="button" className="user-attached-zoom-btn" onClick={onOpenLightbox} title="Ver tamaño completo">
          <Eye size={12} />
          <span>Ver</span>
        </button>
      </div>
    </div>
  )
}

/**
 * Tarjeta visual para documentos y archivos de texto adjuntos por el usuario
 */
function UserFileAttachmentCard({ info }) {
  const { filename, size, url, extension, type } = info

  return (
    <div className={`user-file-card ${type}`}>
      <div className="user-file-icon-wrap">
        {type === 'pdf' ? (
          <FileText size={20} className="file-icon-svg pdf" />
        ) : type === 'code' ? (
          <FileCode size={20} className="file-icon-svg code" />
        ) : type === 'spreadsheet' ? (
          <FileSpreadsheet size={20} className="file-icon-svg sheet" />
        ) : (
          <FileText size={20} className="file-icon-svg txt" />
        )}
        <span className="file-extension-pill">{extension.toUpperCase()}</span>
      </div>

      <div className="user-file-details">
        <span className="user-file-name" title={filename}>{filename}</span>
        <div className="user-file-meta">
          <span className="user-file-badge">{type === 'pdf' ? 'Documento PDF' : type === 'code' ? 'Código / Script' : type === 'spreadsheet' ? 'Hoja de cálculo' : 'Archivo de texto'}</span>
          {size && <span className="user-file-size">{size}</span>}
        </div>
      </div>

      {url && (
        <a 
          href={url} 
          target="_blank" 
          rel="noreferrer" 
          className="user-file-action-btn"
          title="Abrir o descargar archivo"
        >
          <Download size={13} />
          <span>Abrir</span>
        </a>
      )}
    </div>
  )
}

const API_BASE = import.meta.env.VITE_API_URL || '/api'

const ImageCard = React.memo(function ImageCard({ src, alt, onOpenLightbox }) {
  const [downloading, setDownloading] = useState(false)
  const resolvedSrc = src?.startsWith('/api')
    ? `${API_BASE.replace(/\/api$/, '')}${src}`
    : src

  const handleDownload = async () => {
    setDownloading(true)
    try {
      const response = await fetch(resolvedSrc)
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
          {onOpenLightbox && (
            <button className="image-action-btn" onClick={onOpenLightbox} title="Ver ampliada">
              <Maximize2 size={13} />
            </button>
          )}
          <a href={resolvedSrc} target="_blank" rel="noopener noreferrer" className="image-action-btn" title="Abrir en pestaña nueva">
            <ExternalLink size={13} />
          </a>
        </div>
      </div>
      <div className="image-preview-container" onClick={onOpenLightbox} style={{ cursor: onOpenLightbox ? 'pointer' : 'default' }}>
        <img src={resolvedSrc} alt={alt || 'Imagen generada'} className="generated-img" loading="lazy" />
      </div>
    </div>
  )
})

const CodeBlock = React.memo(function CodeBlock({ text, language }) {
  const [copied, setCopied] = useState(false)

  let cleanLang = (language || 'text').trim()
  let customFilename = null
  if (cleanLang.includes(':')) {
    const parts = cleanLang.split(':')
    cleanLang = parts[0].trim()
    customFilename = parts.slice(1).join(':').trim()
  }

  const isPrompt = text.toLowerCase().includes('--ar') || text.toLowerCase().includes('illustration') || text.toLowerCase().includes('anime')
  const defaultFilename = customFilename || (isPrompt ? 'prompt_imagen.txt' : (cleanLang === 'json' ? 'datos.json' : 'documento_yieldchat.txt'))

  const handleCopy = () => {
    navigator.clipboard.writeText(text)
    setCopied(true)
    toast.success(isPrompt ? 'Prompt copiado' : 'Texto copiado')
    setTimeout(() => setCopied(false), 2000)
  }

  const handleDownload = () => {
    downloadTextAsFile(defaultFilename, text)
  }

  return (
    <div className="code-container">
      <div className="code-header">
        <span className="code-header-title">
          {customFilename ? (
            <span style={{ display: 'flex', alignItems: 'center', gap: 6, color: '#38BDF8', fontWeight: 600 }}>
              <FileText size={13} />
              <span>{customFilename}</span>
            </span>
          ) : isPrompt ? (
            'PROMPT DE IMAGEN'
          ) : (
            cleanLang.toUpperCase()
          )}
        </span>
        <div className="code-header-actions" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <button
            className="copy-btn code-download-btn"
            onClick={handleDownload}
            title={`Descargar como ${defaultFilename}`}
          >
            <Download size={12} style={{ color: '#38BDF8' }} />
            <span>Descargar .txt</span>
          </button>
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
      </div>
      <pre>{text}</pre>
    </div>
  )
})

const MessageItem = React.memo(MessageItemComponent, (prevProps, nextProps) => {
  return prevProps.message.id === nextProps.message.id &&
         prevProps.message.content === nextProps.message.content &&
         prevProps.message.role === nextProps.message.role &&
         prevProps.onSaveAsNote === nextProps.onSaveAsNote
})

export default MessageItem
