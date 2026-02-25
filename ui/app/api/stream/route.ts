// Proxy: GET /api/stream → FastAPI GET /chat/stream (Server-Sent Events)
//
// This proxy exists so only one port (Next.js :3000) needs to be publicly
// accessible. The FastAPI server stays on localhost.
//
// The frontend opens an EventSource to this route, which forwards the SSE
// stream from FastAPI back to the client unchanged.

import { NextRequest } from 'next/server'

const FASTAPI = process.env.FASTAPI_URL ?? 'http://localhost:8000'

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url)

  let upstream: Response
  try {
    upstream = await fetch(
      `${FASTAPI}/chat/stream?${searchParams.toString()}`,
      { headers: { Accept: 'text/event-stream' } }
    )
  } catch {
    return new Response('data: {"type":"error","data":"API unreachable"}\n\n', {
      headers: { 'Content-Type': 'text/event-stream' },
    })
  }

  if (!upstream.ok || !upstream.body) {
    return new Response(
      `data: {"type":"error","data":"Upstream returned ${upstream.status}"}\n\n`,
      { headers: { 'Content-Type': 'text/event-stream' } }
    )
  }

  // Forward the ReadableStream body directly — no buffering
  return new Response(upstream.body, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'X-Accel-Buffering': 'no',
    },
  })
}
