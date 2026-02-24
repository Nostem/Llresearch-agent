"""
agent.py — Core agent orchestration

The agent ties together:
  1. The retriever (semantic search over ChromaDB)
  2. The prompt builder (context + lens assembly)
  3. Ollama (Llama 3 8B local LLM)

Two modes:
  - query()  — returns a complete response string (good for API non-streaming)
  - stream() — yields response tokens as they arrive (better UX for chat)

Both modes return source citations alongside the response.
"""

import logging
import os
from typing import Generator

import ollama
from dotenv import load_dotenv

from agent.retriever import semantic_search, hybrid_search
from agent.prompt_builder import build_prompt

load_dotenv()

logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────

LLM_MODEL = os.getenv("LLM_MODEL", "llama3")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
DEFAULT_TOP_K = int(os.getenv("RETRIEVAL_TOP_K", "5"))


# ── Helpers ───────────────────────────────────────────────────────────────────


def _ollama_client() -> ollama.Client:
    return ollama.Client(host=OLLAMA_BASE_URL)


def _extract_citations(chunks: list[dict]) -> list[dict]:
    """
    Extract source citations from retrieved chunks for the API response.
    Returns a clean list of citation objects (no embedding data).
    """
    return [
        {
            "id": c.get("id"),
            "session": c.get("session"),
            "book": c.get("book"),
            "date": c.get("date"),
            "question_number": c.get("question_number"),
            "source_url": c.get("source_url"),
            "relevance_distance": c.get("distance"),
        }
        for c in chunks
    ]


# ── Core query function ───────────────────────────────────────────────────────


def query(
    user_query: str,
    top_k: int = DEFAULT_TOP_K,
    session_filter: int | None = None,
    book_filter: int | None = None,
) -> dict:
    """
    Answer a question using RAG over the Law of One corpus.

    Args:
        user_query:     The user's question.
        top_k:          Number of chunks to retrieve.
        session_filter: Optional — restrict retrieval to one session.
        book_filter:    Optional — restrict retrieval to one book.

    Returns:
        {
          "response": str,          # LLM answer
          "citations": list[dict],  # source chunks used
          "model": str,             # LLM model used
          "lens_version": str,      # system prompt version
        }
    """
    from agent.lens import get_lens_version

    # 1. Retrieve relevant chunks
    if session_filter is not None or book_filter is not None:
        chunks = hybrid_search(
            user_query,
            top_k=top_k,
            session=session_filter,
            book=book_filter,
        )
    else:
        chunks = semantic_search(user_query, top_k=top_k)

    logger.info(f"Retrieved {len(chunks)} chunks for query: '{user_query[:60]}'")

    # 2. Build prompt
    system_prompt, user_message = build_prompt(user_query, chunks)

    # 3. Call Ollama
    client = _ollama_client()
    try:
        response = client.chat(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            options={
                "temperature": 0.3,  # Lower temp for more grounded, citation-faithful answers
                "num_ctx": 8192,     # Context window — enough for 5 chunks + system prompt
            },
        )
        answer = response.message.content
    except Exception as e:
        raise RuntimeError(
            f"Ollama call failed. Is Ollama running with '{LLM_MODEL}'?\n"
            f"Error: {e}"
        ) from e

    return {
        "response": answer,
        "citations": _extract_citations(chunks),
        "model": LLM_MODEL,
        "lens_version": get_lens_version(),
    }


def stream(
    user_query: str,
    top_k: int = DEFAULT_TOP_K,
    session_filter: int | None = None,
    book_filter: int | None = None,
) -> Generator[str, None, None]:
    """
    Stream an answer token by token using Ollama streaming.

    Yields text tokens as they are generated.
    The caller is responsible for assembling the full response if needed.

    Usage:
        for token in stream("What is the harvest?"):
            print(token, end="", flush=True)
    """
    # 1. Retrieve
    if session_filter is not None or book_filter is not None:
        chunks = hybrid_search(
            user_query,
            top_k=top_k,
            session=session_filter,
            book=book_filter,
        )
    else:
        chunks = semantic_search(user_query, top_k=top_k)

    # 2. Build prompt
    system_prompt, user_message = build_prompt(user_query, chunks)

    # 3. Stream from Ollama
    client = _ollama_client()
    stream_response = client.chat(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        stream=True,
        options={
            "temperature": 0.3,
            "num_ctx": 8192,
        },
    )

    for chunk in stream_response:
        if chunk.message and chunk.message.content:
            yield chunk.message.content


def stream_with_citations(
    user_query: str,
    top_k: int = DEFAULT_TOP_K,
    session_filter: int | None = None,
    book_filter: int | None = None,
) -> Generator[dict, None, None]:
    """
    Stream response with citations metadata yielded first.

    Yields:
      - First: {"type": "citations", "data": [...]}
      - Then: {"type": "token", "data": "<token string>"} for each token
      - Finally: {"type": "done"}
    """
    from agent.lens import get_lens_version

    # Retrieve upfront so we can yield citations immediately
    if session_filter is not None or book_filter is not None:
        chunks = hybrid_search(
            user_query,
            top_k=top_k,
            session=session_filter,
            book=book_filter,
        )
    else:
        chunks = semantic_search(user_query, top_k=top_k)

    # Yield citations metadata first — the UI can show sources while response streams
    yield {
        "type": "citations",
        "data": _extract_citations(chunks),
        "model": LLM_MODEL,
        "lens_version": get_lens_version(),
    }

    system_prompt, user_message = build_prompt(user_query, chunks)

    client = _ollama_client()
    stream_response = client.chat(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        stream=True,
        options={"temperature": 0.3, "num_ctx": 8192},
    )

    for chunk in stream_response:
        if chunk.message and chunk.message.content:
            yield {"type": "token", "data": chunk.message.content}

    yield {"type": "done"}
