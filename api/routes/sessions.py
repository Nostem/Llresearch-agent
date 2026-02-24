"""
sessions.py — Session browsing endpoints

GET /sessions           — List all sessions with chunk counts
GET /sessions/{n}       — Get all Q&A chunks for a specific session
"""

import logging

from fastapi import APIRouter, HTTPException, Path

from agent.retriever import get_by_session, collection_stats
from api.models import SessionSummary, SessionDetail, SearchResult

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/sessions", tags=["sessions"])

# Book → session range (inclusive) — for summary metadata
BOOK_MAP = {
    1: (1, 26),
    2: (27, 50),
    3: (51, 75),
    4: (76, 99),
    5: (100, 106),
}


def _session_to_book(n: int) -> int:
    for book, (start, end) in BOOK_MAP.items():
        if start <= n <= end:
            return book
    return 0


@router.get("/", response_model=list[SessionSummary])
async def list_sessions() -> list[SessionSummary]:
    """
    List all sessions available in the vector store.

    Returns a summary for each session: session number, book, date,
    source URL, and how many Q&A chunks were indexed.
    """
    try:
        stats = collection_stats()
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    # Build a summary by fetching metadata for each session
    # We query all 106 possible sessions — only those with data will return results
    summaries = []
    for n in range(1, 107):
        chunks = get_by_session(n)
        if not chunks:
            continue

        first = chunks[0]
        summaries.append(
            SessionSummary(
                session=n,
                book=first.get("book") or _session_to_book(n),
                date=first.get("date") or "unknown",
                source_url=first.get("source_url") or "",
                chunk_count=len(chunks),
            )
        )

    return summaries


@router.get("/{session_n}", response_model=SessionDetail)
async def get_session(
    session_n: int = Path(..., ge=1, le=106, description="Session number (1–106)"),
) -> SessionDetail:
    """
    Get all Q&A pairs for a specific session, in order.

    Returns the full text of each chunk with metadata.
    Useful for reading a session sequentially or reviewing its full scope.
    """
    try:
        chunks = get_by_session(session_n)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    if not chunks:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Session {session_n} not found in the vector store. "
                "It may not have been indexed yet."
            ),
        )

    first = chunks[0]
    chunk_models = [
        SearchResult(
            id=c["id"],
            session=c["session"],
            book=c["book"],
            date=c["date"],
            question_number=c["question_number"],
            source_url=c["source_url"],
            text=c["text"],
            distance=None,
        )
        for c in chunks
    ]

    return SessionDetail(
        session=session_n,
        book=first.get("book") or _session_to_book(session_n),
        date=first.get("date") or "unknown",
        source_url=first.get("source_url") or "",
        chunks=chunk_models,
    )
