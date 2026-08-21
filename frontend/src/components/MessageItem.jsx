import React, { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Copy, Check, Bot, User } from 'lucide-react'
import toast from 'react-hot-toast'

export default function MessageItem({ message }) {
  const isUser = message.role === 'user'

  return (
    <div className="message-row">
      <div className={`message-avatar ${isUser ? 'avatar-user' : 'avatar-agent'}`}>
        {isUser ? <User size={16} /> : <Bot size={18} />}
      </div>

      <div className="message-body">
        {isUser ? (
          <div className="message-user-content">{message.content}</div>
        ) : (
          <div className="message-agent-content">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
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

function CodeBlock({ text, language }) {
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
}
