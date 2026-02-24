"""
search.py — Concept/semantic search endpoint

POST /search — Direct vector search, no LLM generation
              Returns raw ranked passages with metadata
"""

import logging

from fastapi import APIRouter, HTTPException

from agent.retriever import hybrid_search
from api.models import SearchRequest, SearchResponse, SearchResult

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/search", tags=["search"])


@router.post("/", response_model=SearchResponse)
async def search(request: SearchRequest) -> SearchResponse:
    """
    Semantic search over the Law of One corpus — no LLM generation.

    Returns the top-k most relevant Q&A chunks for the query,
    with full metadata and relevance distances. Useful for:
      - Exploring what the corpus contains on a topic
      - Verifying which passages would be retrieved for a given query
      - Building concept maps or reading paths through the material
    """
    try:
        chunks = hybrid_search(
            query=request.query,
            top_k=request.top_k,
            session=request.session,
            book=request.book,
            entity=request.entity,
            date_from=request.date_from,
            date_to=request.date_to,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.exception(f"Search error for query: {request.query!r}")
        raise HTTPException(status_code=500, detail="Internal search error")

    results = [
        SearchResult(
            id=c["id"],
            session=c["session"],
            book=c["book"],
            date=c["date"],
            question_number=c["question_number"],
            source_url=c["source_url"],
            text=c["text"],
            distance=c.get("distance"),
        )
        for c in chunks
    ]

    return SearchResponse(
        query=request.query,
        results=results,
        total=len(results),
    )
