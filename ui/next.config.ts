import type { NextConfig } from 'next'

const nextConfig: NextConfig = {
  // FASTAPI_URL is read by API proxy routes at runtime via process.env
  // Set it in .env.local — defaults to localhost:8000
}

export default nextConfig
