// Proxy:
//   GET /api/sessions            → FastAPI GET /sessions/     (list all)
//   GET /api/sessions?session=N  → FastAPI GET /sessions/{N}  (single session)

import { NextRequest, NextResponse } from 'next/server'

const FASTAPI = process.env.FASTAPI_URL ?? 'http://localhost:8000'

export async function GET(request: NextRequest) {
  const session = new URL(request.url).searchParams.get('session')
  const url = session ? `${FASTAPI}/sessions/${session}` : `${FASTAPI}/sessions/`

  try {
    const res = await fetch(url)
    const data = await res.json()
    return NextResponse.json(data, { status: res.status })
  } catch {
    return NextResponse.json({ detail: 'Proxy error: API may be unreachable' }, { status: 502 })
  }
}
