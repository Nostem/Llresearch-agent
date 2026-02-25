#!/usr/bin/env bash
# start_all.sh — Start FastAPI + Next.js UI + Cloudflare Tunnel
#
# Usage:
#   ./scripts/start_all.sh
#
# This starts three processes:
#   1. FastAPI backend   → http://localhost:8000
#   2. Next.js UI        → http://localhost:3000
#   3. Cloudflare Tunnel → public HTTPS URL printed to console
#
# The public URL changes each run (quick tunnel).
# For a permanent URL see: scripts/setup_tunnel.md

set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# ── Check Ollama is running ────────────────────────────────────────────────────
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
  echo "[warn] Ollama does not appear to be running."
  echo "       Start it with: ollama serve"
  echo "       Continuing anyway — chat will fail until Ollama is up."
  echo ""
fi

# ── Activate Python venv if present ───────────────────────────────────────────
if [ -f "$REPO_ROOT/.venv/bin/activate" ]; then
  source "$REPO_ROOT/.venv/bin/activate"
fi

# ── 1. Start FastAPI ───────────────────────────────────────────────────────────
echo "[1/3] Starting FastAPI on :8000 ..."
cd "$REPO_ROOT"
uvicorn api.main:app --host 0.0.0.0 --port 8000 &
API_PID=$!

# Give FastAPI a moment to bind
sleep 2

# ── 2. Start Next.js UI ────────────────────────────────────────────────────────
echo "[2/3] Starting Next.js UI on :3000 ..."
cd "$REPO_ROOT/ui"
npm run start &
UI_PID=$!

sleep 2

# ── 3. Start Cloudflare Tunnel ─────────────────────────────────────────────────
echo "[3/3] Starting Cloudflare Tunnel ..."
echo ""
echo "  Your public URL will appear below."
echo "  Share it or open it on any device."
echo "  (URL changes each run — see setup_tunnel.md for a permanent address)"
echo ""
cloudflared tunnel --url http://localhost:3000 &
TUNNEL_PID=$!

# ── Shutdown handler ───────────────────────────────────────────────────────────
trap "echo ''; echo 'Stopping...'; kill $API_PID $UI_PID $TUNNEL_PID 2>/dev/null; exit 0" INT TERM

wait
