'use client'

import { useState, useEffect } from 'react'

interface SessionSummary {
  session: number
  book: number
  date: string
  source_url: string
  chunk_count: number
}

interface Chunk {
  id: string
  session: number
  book: number
  date: string
  question_number: number
  source_url: string
  text: string
}

interface SessionDetail {
  session: number
  book: number
  date: string
  source_url: string
  chunks: Chunk[]
}

export default function SessionsPage() {
  const [sessions, setSessions] = useState<SessionSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [filterBook, setFilterBook] = useState<number | null>(null)
  const [selected, setSelected] = useState<SessionDetail | null>(null)
  const [loadingDetail, setLoadingDetail] = useState(false)

  useEffect(() => {
    fetch('/api/sessions')
      .then(r => r.json())
      .then((data: SessionSummary[]) => setSessions(data))
      .catch(() => setError('Failed to load sessions — is the API running?'))
      .finally(() => setLoading(false))
  }, [])

  async function openSession(n: number) {
    setSelected(null)
    setLoadingDetail(true)
    try {
      const res = await fetch(`/api/sessions?session=${n}`)
      if (!res.ok) throw new Error()
      const data = await res.json() as SessionDetail
      setSelected(data)
    } catch {
      // silently ignore — modal just won't open
    } finally {
      setLoadingDetail(false)
    }
  }

  const totalChunks = sessions.reduce((acc, s) => acc + s.chunk_count, 0)
  const filtered = filterBook ? sessions.filter(s => s.book === filterBook) : sessions

  return (
    <div className="max-w-5xl mx-auto px-4 py-8 w-full">

      {/* Header */}
      <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-lg font-semibold text-zinc-100">Sessions</h1>
          <p className="text-zinc-500 text-sm mt-1">
            {sessions.length} sessions · {totalChunks} Q&amp;A chunks indexed
          </p>
        </div>

        {/* Book filter */}
        <div className="flex gap-1 flex-wrap">
          {[null, 1, 2, 3, 4, 5].map(b => (
            <button
              key={b ?? 'all'}
              onClick={() => setFilterBook(b)}
              className={`px-3 py-1 rounded-md text-xs font-medium transition-colors ${
                filterBook === b
                  ? 'bg-ra-muted text-ra-gold border border-ra-gold/30'
                  : 'text-zinc-500 hover:text-zinc-300 bg-zinc-900 border border-transparent'
              }`}
            >
              {b == null ? 'All' : `Book ${b}`}
            </button>
          ))}
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="mb-4 p-3 rounded-lg bg-red-950/40 border border-red-800/40 text-red-400 text-sm">
          {error}
        </div>
      )}

      {/* Session grid */}
      {loading ? (
        <p className="text-zinc-500 text-sm">Loading sessions…</p>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-2">
          {filtered.map(s => (
            <button
              key={s.session}
              onClick={() => openSession(s.session)}
              disabled={loadingDetail}
              className="text-left p-3 rounded-xl border border-zinc-800 bg-zinc-900/40 hover:border-ra-gold/30 hover:bg-zinc-900 transition-colors disabled:opacity-50"
            >
              <div className="text-ra-gold/80 text-xs font-mono font-semibold">
                Session {s.session}
              </div>
              <div className="text-zinc-500 text-xs mt-0.5">Book {s.book}</div>
              <div className="text-zinc-600 text-xs">{s.date}</div>
              <div className="text-zinc-600 text-xs mt-1">{s.chunk_count} Q&amp;A</div>
            </button>
          ))}
        </div>
      )}

      {/* Session detail modal */}
      {(loadingDetail || selected) && (
        <div
          className="fixed inset-0 bg-zinc-950/80 backdrop-blur-sm z-50 flex items-start justify-center p-4 overflow-y-auto"
          onClick={e => {
            if (e.target === e.currentTarget) setSelected(null)
          }}
        >
          <div className="bg-zinc-900 border border-zinc-700 rounded-2xl max-w-2xl w-full my-8 p-6 shadow-2xl">
            {loadingDetail ? (
              <p className="text-zinc-500 text-sm">Loading…</p>
            ) : selected ? (
              <>
                {/* Modal header */}
                <div className="flex items-start justify-between mb-5">
                  <div>
                    <h2 className="text-base font-semibold text-zinc-100">
                      Session {selected.session}
                    </h2>
                    <p className="text-zinc-500 text-sm mt-0.5">
                      Book {selected.book} · {selected.date} · {selected.chunks.length} exchanges
                    </p>
                  </div>
                  <button
                    onClick={() => setSelected(null)}
                    className="text-zinc-500 hover:text-zinc-300 text-xl leading-none ml-4"
                    aria-label="Close"
                  >
                    ×
                  </button>
                </div>

                {/* Chunks */}
                <div className="space-y-5 max-h-[60vh] overflow-y-auto pr-1">
                  {selected.chunks.map(chunk => (
                    <div key={chunk.id}>
                      <div className="font-mono text-ra-gold/50 text-xs mb-1">
                        Q{chunk.question_number}
                      </div>
                      <p className="text-sm text-zinc-300 leading-relaxed">{chunk.text}</p>
                    </div>
                  ))}
                </div>

                {/* Footer */}
                <div className="mt-5 pt-4 border-t border-zinc-800">
                  <a
                    href={selected.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-ra-gold/50 hover:text-ra-gold transition-colors"
                  >
                    View on llresearch.org →
                  </a>
                </div>
              </>
            ) : null}
          </div>
        </div>
      )}
    </div>
  )
}
