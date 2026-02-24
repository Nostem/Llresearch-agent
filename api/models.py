"""
models.py — Pydantic request/response models for the FastAPI API

All endpoints use these for validation and serialization.
"""

from pydantic import BaseModel, Field


# ── Shared ────────────────────────────────────────────────────────────────────


class Citation(BaseModel):
    """A source reference returned with every response."""
    id: str
    session: int
    book: int
    date: str
    question_number: int
    source_url: str
    relevance_distance: float | None = None


# ── Chat (/chat) ──────────────────────────────────────────────────────────────


class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=20)
    session_filter: int | None = Field(
        default=None, ge=1, le=106,
        description="Restrict retrieval to a specific session number"
    )
    book_filter: int | None = Field(
        default=None, ge=1, le=5,
        description="Restrict retrieval to a specific book (1–5)"
    )


class ChatResponse(BaseModel):
    response: str
    citations: list[Citation]
    model: str
    lens_version: str


# ── Search (/search) ──────────────────────────────────────────────────────────


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=20)
    session: int | None = Field(default=None, ge=1, le=106)
    book: int | None = Field(default=None, ge=1, le=5)
    entity: str | None = Field(default=None, description="Filter by entity (e.g. 'Ra')")
    date_from: str | None = Field(default=None, description="ISO date lower bound (YYYY-MM-DD)")
    date_to: str | None = Field(default=None, description="ISO date upper bound (YYYY-MM-DD)")


class SearchResult(BaseModel):
    id: str
    session: int
    book: int
    date: str
    question_number: int
    source_url: str
    text: str
    distance: float | None = None


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult]
    total: int


# ── Sessions (/sessions) ──────────────────────────────────────────────────────


class SessionSummary(BaseModel):
    session: int
    book: int
    date: str
    source_url: str
    chunk_count: int


class SessionDetail(BaseModel):
    session: int
    book: int
    date: str
    source_url: str
    chunks: list[SearchResult]


# ── Health (/health) ─────────────────────────────────────────────────────────


class HealthResponse(BaseModel):
    status: str
    collection_name: str
    total_chunks: int
    embed_model: str
    llm_model: str
    lens_version: str
