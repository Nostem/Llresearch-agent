'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'

const LINKS = [
  { href: '/', label: 'Chat' },
  { href: '/search', label: 'Search' },
  { href: '/sessions', label: 'Sessions' },
]

export default function Nav() {
  const pathname = usePathname()

  return (
    <header className="h-14 border-b border-zinc-800 bg-zinc-950/90 backdrop-blur-sm sticky top-0 z-40 flex items-center">
      <div className="max-w-5xl mx-auto px-4 w-full flex items-center justify-between">
        {/* Wordmark */}
        <div className="flex items-center gap-2.5">
          <span className="text-ra-gold font-semibold tracking-tight">⬡ llresearch</span>
          <span className="text-zinc-700 text-xs hidden sm:block">Ra Material · Law of One</span>
        </div>

        {/* Navigation */}
        <nav className="flex items-center gap-0.5">
          {LINKS.map(({ href, label }) => (
            <Link
              key={href}
              href={href}
              className={`px-3 py-1.5 rounded-lg text-sm transition-colors ${
                pathname === href
                  ? 'bg-ra-muted text-ra-gold'
                  : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/60'
              }`}
            >
              {label}
            </Link>
          ))}
        </nav>
      </div>
    </header>
  )
}
