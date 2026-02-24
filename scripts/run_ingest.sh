#!/usr/bin/env bash
# run_ingest.sh — Full data pipeline: scrape → clean → chunk → embed
#
# Run this to go from nothing to a fully populated ChromaDB collection.
# Prerequisites:
#   - Python virtual environment activated (.venv)
#   - Ollama running: ollama serve
#   - nomic-embed-text model pulled: ollama pull nomic-embed-text
#   - .env file configured (copy from .env.example)
#
# Usage:
#   bash scripts/run_ingest.sh            # Full run (skips already-done steps)
#   bash scripts/run_ingest.sh --force    # Force re-run all steps
#
# Individual steps can be re-run with:
#   python -m ingest.scraper
#   python -m ingest.cleaner
#   python -m ingest.chunker
#   python -m embeddings.embed

set -euo pipefail

FORCE=""
if [[ "${1:-}" == "--force" ]]; then
    FORCE="--force"
    echo "Force mode: re-running all pipeline steps."
fi

echo "=============================================="
echo "  llresearch-agent — Ingest Pipeline"
echo "=============================================="
echo ""

# ── Step 1: Scrape ─────────────────────────────────────────────────────────────
echo "[1/4] Scraping transcripts from llresearch.org..."
python -m ingest.scraper $FORCE

echo ""

# ── Step 2: Clean ──────────────────────────────────────────────────────────────
echo "[2/4] Cleaning and parsing HTML transcripts..."
python -m ingest.cleaner $FORCE

echo ""

# ── Step 3: Chunk ──────────────────────────────────────────────────────────────
echo "[3/4] Chunking into Q&A pairs..."
python -m ingest.chunker $FORCE

echo ""

# ── Step 4: Embed ──────────────────────────────────────────────────────────────
echo "[4/4] Generating embeddings and storing in ChromaDB..."
python -m embeddings.embed $FORCE

echo ""
echo "=============================================="
echo "  Ingest pipeline complete."
echo "  Start the API: uvicorn api.main:app --reload"
echo "=============================================="
