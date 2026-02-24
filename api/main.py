"""
main.py — FastAPI application entry point

Starts the llresearch-agent API server.

Routes:
    GET  /health          — System health check
    POST /chat/           — RAG Q&A (non-streaming)
    GET  /chat/stream     — RAG Q&A (SSE streaming)
    POST /search/         — Semantic search (no LLM)
    GET  /sessions/       — List all indexed sessions
    GET  /sessions/{n}    — Browse a specific session

Run with:
    uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
"""

import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from api.routes import chat, search, sessions
from api.models import HealthResponse

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

app = FastAPI(
    title="llresearch-agent",
    description=(
        "A local RAG-based AI agent for exploring the Law of One transcripts. "
        "Grounded in the Ra/Q'uo teachings from the L/L Research library."
    ),
    version="0.1.0",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
# Allow local development — tighten this before any public deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ────────────────────────────────────────────────────────────────────
app.include_router(chat.router)
app.include_router(search.router)
app.include_router(sessions.router)


# ── Health check ──────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """
    System health check.

    Returns collection stats and confirms the vector store is accessible.
    """
    from agent.retriever import collection_stats
    from agent.lens import get_lens_version

    try:
        stats = collection_stats()
    except RuntimeError as e:
        return HealthResponse(
            status="degraded",
            collection_name=os.getenv("CHROMA_COLLECTION", "llresearch"),
            total_chunks=0,
            embed_model=os.getenv("EMBED_MODEL", "nomic-embed-text"),
            llm_model=os.getenv("LLM_MODEL", "llama3"),
            lens_version=get_lens_version(),
        )

    return HealthResponse(
        status="ok",
        collection_name=stats["collection"],
        total_chunks=stats["total_chunks"],
        embed_model=stats["embed_model"],
        llm_model=os.getenv("LLM_MODEL", "llama3"),
        lens_version=get_lens_version(),
    )


@app.get("/")
async def root():
    return {
        "name": "llresearch-agent",
        "message": "We are those of Ra. The API is running.",
        "docs": "/docs",
        "health": "/health",
    }
