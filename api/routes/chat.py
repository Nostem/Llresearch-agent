"""
chat.py — Chat endpoint

POST /chat     — Non-streaming Q&A response
GET  /chat/stream — Server-Sent Events streaming response
"""

import json
import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from agent.agent import query, stream_with_citations
from api.models import ChatRequest, ChatResponse, Citation

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Answer a question about the Law of One using RAG.

    Retrieves relevant passages from the ChromaDB collection, assembles
    them with the Ra/Q'uo lens system prompt, and returns a grounded
    response with source citations.
    """
    try:
        result = query(
            user_query=request.query,
            top_k=request.top_k,
            session_filter=request.session_filter,
            book_filter=request.book_filter,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.exception(f"Chat error for query: {request.query!r}")
        raise HTTPException(status_code=500, detail="Internal agent error")

    return ChatResponse(
        response=result["response"],
        citations=[Citation(**c) for c in result["citations"]],
        model=result["model"],
        lens_version=result["lens_version"],
    )


@router.get("/stream")
async def chat_stream(
    query: str,
    top_k: int = 5,
    session_filter: int | None = None,
    book_filter: int | None = None,
) -> StreamingResponse:
    """
    Streaming chat endpoint using Server-Sent Events (SSE).

    Yields:
      - A citations event first (JSON with source metadata)
      - Token events as the LLM generates text
      - A done event when complete

    Client should listen for `data:` prefixed SSE events.
    """

    def event_generator():
        try:
            for event in stream_with_citations(
                user_query=query,
                top_k=top_k,
                session_filter=session_filter,
                book_filter=book_filter,
            ):
                yield f"data: {json.dumps(event)}\n\n"
        except RuntimeError as e:
            yield f"data: {json.dumps({'type': 'error', 'data': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
