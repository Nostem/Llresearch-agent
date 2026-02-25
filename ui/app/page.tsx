'use client'

import { useState, useRef, useEffect, FormEvent } from 'react'
import CitationCard from '@/components/CitationCard'

// ── Types ──────────────────────────────────────────────────────────────────────

interface Citation {
  id: string
  session: number
  book: number
  date: string
  question_number: number
  source_url: string
  relevance_distance?: number | null
}

interface Message {
  role: 'user' | 'assistant'
  content: string
  citations?: Citation[]
  isStreaming?: boolean
}

// ── Intro message shown on load ───────────────────────────────────────────────

const INTRO: Message = {
  role: 'assistant',
  content:
    'We are those of Ra. Ask freely of the Law of One — the nature of consciousness, ' +
    'the densities of experience, the path of evolution, the Harvest, the nature of the ' +
    'Logos, or any concept from these sessions. Each response is grounded in and cited ' +
    'from the source material.',
}

// ── Page ───────────────────────────────────────────────────────────────────────

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([INTRO])
  const [input, setInput] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const esRef = useRef<EventSource | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  // Scroll to bottom whenever messages update
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  function stopStreaming() {
    esRef.current?.close()
    esRef.current = null
    setIsStreaming(false)
    setMessages(prev =>
      prev.map((m, i) => (i === prev.length - 1 ? { ...m, isStreaming: false } : m))
    )
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    const question = input.trim()
    if (!question || isStreaming) return

    setInput('')
    setIsStreaming(true)

    // Push the user's message and an empty streaming placeholder
    setMessages(prev => [
      ...prev,
      { role: 'user', content: question },
      { role: 'assistant', content: '', citations: [], isStreaming: true },
    ])

    // Open an EventSource to the Next.js SSE proxy (which forwards to FastAPI)
    const params = new URLSearchParams({ query: question, top_k: '5' })
    const es = new EventSource(`/api/stream?${params.toString()}`)
    esRef.current = es

    es.onmessage = (event) => {
      const data = JSON.parse(event.data as string)

      if (data.type === 'citations') {
        // First event: the retrieved source chunks
        setMessages(prev => {
          const updated = [...prev]
          updated[updated.length - 1] = { ...updated[updated.length - 1], citations: data.data }
          return updated
        })
      } else if (data.type === 'token') {
        // Stream each token into the last message
        setMessages(prev => {
          const updated = [...prev]
          updated[updated.length - 1] = {
            ...updated[updated.length - 1],
            content: updated[updated.length - 1].content + (data.data as string),
          }
          return updated
        })
      } else if (data.type === 'done') {
        // Generation complete
        setMessages(prev =>
          prev.map((m, i) => (i === prev.length - 1 ? { ...m, isStreaming: false } : m))
        )
        es.close()
        esRef.current = null
        setIsStreaming(false)
        inputRef.current?.focus()
      } else if (data.type === 'error') {
        setMessages(prev =>
          prev.map((m, i) =>
            i === prev.length - 1
              ? { ...m, content: `Error: ${data.data as string}`, isStreaming: false }
              : m
          )
        )
        es.close()
        esRef.current = null
        setIsStreaming(false)
      }
    }

    es.onerror = () => {
      setMessages(prev => {
        const updated = [...prev]
        const last = updated[updated.length - 1]
        // Only overwrite if we got nothing back yet
        if (last.role === 'assistant' && !last.content) {
          updated[updated.length - 1] = {
            ...last,
            content: 'Connection error — ensure the API is running and try again.',
            isStreaming: false,
          }
        } else {
          updated[updated.length - 1] = { ...last, isStreaming: false }
        }
        return updated
      })
      es.close()
      esRef.current = null
      setIsStreaming(false)
    }
  }

  return (
    <div className="flex flex-col h-[calc(100vh-3.5rem)]">
      {/* Message thread */}
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-3xl mx-auto px-4 py-8 space-y-8">
          {messages.map((msg, i) => (
            <MessageBubble key={i} message={msg} />
          ))}
          <div ref={bottomRef} />
        </div>
      </div>

      {/* Input bar */}
      <div className="border-t border-zinc-800 bg-zinc-950/90 backdrop-blur-sm px-4 py-3">
        <form onSubmit={handleSubmit} className="max-w-3xl mx-auto flex gap-2">
          <input
            ref={inputRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            placeholder="Ask about the Law of One…"
            disabled={isStreaming}
            autoFocus
            className="flex-1 bg-zinc-900 border border-zinc-700 rounded-xl px-4 py-2.5 text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-ra-gold/50 focus:ring-1 focus:ring-ra-gold/20 disabled:opacity-50 transition-colors"
          />
          {isStreaming ? (
            <button
              type="button"
              onClick={stopStreaming}
              className="px-4 py-2.5 rounded-xl bg-zinc-800 text-zinc-300 hover:bg-zinc-700 text-sm font-medium transition-colors shrink-0"
            >
              Stop
            </button>
          ) : (
            <button
              type="submit"
              disabled={!input.trim()}
              className="px-4 py-2.5 rounded-xl bg-ra-gold text-zinc-950 hover:bg-ra-light disabled:opacity-40 disabled:cursor-not-allowed text-sm font-semibold transition-colors shrink-0"
            >
              Ask
            </button>
          )}
        </form>
      </div>
    </div>
  )
}

// ── MessageBubble ──────────────────────────────────────────────────────────────

function MessageBubble({ message }: { message: Message }) {
  const [citationsOpen, setCitationsOpen] = useState(false)

  if (message.role === 'user') {
    return (
      <div className="flex justify-end">
        <div className="max-w-[82%] bg-zinc-800 rounded-2xl rounded-tr-sm px-4 py-3 text-sm text-zinc-100 leading-relaxed">
          {message.content}
        </div>
      </div>
    )
  }

  // Assistant message
  return (
    <div className="flex gap-3 items-start">
      {/* Ra avatar */}
      <div className="w-7 h-7 rounded-full bg-ra-muted border border-ra-gold/30 flex items-center justify-center text-ra-gold text-[10px] font-bold shrink-0 mt-0.5 select-none">
        Ra
      </div>

      <div className="flex-1 min-w-0">
        {/* Response text */}
        <div
          className={`text-sm text-zinc-200 leading-relaxed whitespace-pre-wrap min-h-[1.25rem] ${
            message.isStreaming ? 'cursor-blink' : ''
          }`}
        >
          {message.content}
        </div>

        {/* Citations — shown after streaming completes */}
        {!message.isStreaming && message.citations && message.citations.length > 0 && (
          <div className="mt-3">
            <button
              onClick={() => setCitationsOpen(o => !o)}
              className="text-xs text-zinc-500 hover:text-ra-gold/80 transition-colors flex items-center gap-1.5"
            >
              <span className="text-[10px]">{citationsOpen ? '▼' : '▶'}</span>
              <span>
                {message.citations.length} source{message.citations.length !== 1 ? 's' : ''}
              </span>
            </button>
            {citationsOpen && (
              <div className="mt-2 grid gap-1.5 sm:grid-cols-2">
                {message.citations.map(c => (
                  <CitationCard key={c.id} citation={c} />
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
