'use client'

import { useState, FormEvent } from 'react'
import CitationCard from '@/components/CitationCard'

interface SearchResult {
  id: string
  session: number
  book: number
  date: string
  question_number: number
  source_url: string
  text: string
  distance?: number | null
}

export default function SearchPage() {
  const [query, setQuery] = useState('')
  const [book, setBook] = useState('')
  const [topK, setTopK] = useState('5')
  const [results, setResults] = useState<SearchResult[]>([])
  const [loading, setLoading] = useState(false)
  const [searched, setSearched] = useState(false)
  const [error, setError] = useState('')

  async function handleSearch(e: FormEvent) {
    e.preventDefault()
    if (!query.trim()) return

    setLoading(true)
    setError('')
    setSearched(true)

    try {
      const res = await fetch('/api/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: query.trim(),
          top_k: parseInt(topK),
          book: book ? parseInt(book) : null,
        }),
      })
      if (!res.ok) throw new Error(`Search failed (${res.status})`)
      const data = await res.json() as { results: SearchResult[] }
      setResults(data.results)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Search failed')
      setResults([])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-3xl mx-auto px-4 py-8 w-full">
      <div className="mb-6">
        <h1 className="text-lg font-semibold text-zinc-100">Semantic Search</h1>
        <p className="text-zinc-500 text-sm mt-1">
          Direct retrieval from the vector store — no LLM, just the source passages.
        </p>
      </div>

      {/* Search form */}
      <form onSubmit={handleSearch} className="space-y-2 mb-8">
        <div className="flex gap-2">
          <input
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="veil of forgetting, harvest, Logos, intelligent infinity…"
            className="flex-1 bg-zinc-900 border border-zinc-700 rounded-xl px-4 py-2.5 text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-ra-gold/50 focus:ring-1 focus:ring-ra-gold/20 transition-colors"
          />
          <button
            type="submit"
            disabled={loading || !query.trim()}
            className="px-4 py-2.5 rounded-xl bg-ra-gold text-zinc-950 hover:bg-ra-light disabled:opacity-40 disabled:cursor-not-allowed text-sm font-semibold transition-colors shrink-0"
          >
            {loading ? '…' : 'Search'}
          </button>
        </div>

        {/* Filters */}
        <div className="flex gap-2 flex-wrap">
          <select
            value={book}
            onChange={e => setBook(e.target.value)}
            className="bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-zinc-400 text-xs focus:outline-none focus:border-ra-gold/50 transition-colors"
          >
            <option value="">All books</option>
            <option value="1">Book 1 · Sessions 1–26</option>
            <option value="2">Book 2 · Sessions 27–50</option>
            <option value="3">Book 3 · Sessions 51–75</option>
            <option value="4">Book 4 · Sessions 76–99</option>
            <option value="5">Book 5 · Sessions 100–106</option>
          </select>
          <select
            value={topK}
            onChange={e => setTopK(e.target.value)}
            className="bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-zinc-400 text-xs focus:outline-none focus:border-ra-gold/50 transition-colors"
          >
            <option value="3">Top 3</option>
            <option value="5">Top 5</option>
            <option value="10">Top 10</option>
            <option value="20">Top 20</option>
          </select>
        </div>
      </form>

      {/* Error */}
      {error && (
        <div className="mb-4 p-3 rounded-lg bg-red-950/40 border border-red-800/40 text-red-400 text-sm">
          {error}
        </div>
      )}

      {/* Empty state */}
      {searched && !loading && results.length === 0 && !error && (
        <p className="text-zinc-500 text-sm">No results found for that query.</p>
      )}

      {/* Results */}
      <div className="space-y-4">
        {results.map((r, i) => (
          <div key={r.id} className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-4">
            <div className="flex items-center justify-between gap-3 mb-3">
              <div className="flex items-center gap-2">
                <span className="text-zinc-600 text-xs font-mono">#{i + 1}</span>
                <span className="font-mono text-ra-gold/70 text-xs">{r.id}</span>
              </div>
              {r.distance != null && (
                <span className="text-zinc-500 text-xs">
                  {(1 - r.distance).toFixed(3)} relevance
                </span>
              )}
            </div>

            {/* Passage text */}
            <p className="text-sm text-zinc-300 leading-relaxed mb-3 line-clamp-6">
              {r.text}
            </p>

            {/* Source metadata */}
            <CitationCard
              citation={{
                id: r.id,
                session: r.session,
                book: r.book,
                date: r.date,
                question_number: r.question_number,
                source_url: r.source_url,
                relevance_distance: r.distance,
              }}
            />
          </div>
        ))}
      </div>
    </div>
  )
}
