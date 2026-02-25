interface Citation {
  id: string
  session: number
  book: number
  date: string
  question_number: number
  source_url: string
  relevance_distance?: number | null
}

export default function CitationCard({ citation: c }: { citation: Citation }) {
  return (
    <a
      href={c.source_url}
      target="_blank"
      rel="noopener noreferrer"
      className="block px-3 py-2 rounded-lg border border-zinc-700/50 bg-zinc-800/50 hover:border-ra-gold/30 hover:bg-zinc-800 transition-colors text-xs group"
    >
      <div className="flex items-center justify-between gap-2">
        <span className="font-mono text-ra-gold/70 font-medium group-hover:text-ra-gold transition-colors">
          {c.id}
        </span>
        {c.relevance_distance != null && (
          <span className="text-zinc-600 text-[10px]">
            {(1 - c.relevance_distance).toFixed(3)}
          </span>
        )}
      </div>
      <div className="mt-0.5 text-zinc-500 flex flex-wrap gap-x-2">
        <span>Session {c.session}</span>
        <span>Book {c.book}</span>
        <span>Q{c.question_number}</span>
        <span>{c.date}</span>
      </div>
    </a>
  )
}
