"""
retriever.py — Semantic search and hybrid retrieval over the ChromaDB collection

Provides two retrieval strategies:
  1. Semantic search — pure vector similarity via ChromaDB + nomic-embed-text
  2. Hybrid search — semantic + keyword filtering (by session, book, entity, date)

Returned results include the full chunk text and all metadata, ready to
be passed into the prompt builder.

Result schema:
    {
      "id": "ra-s042-q006",
      "session": 42,
      "book": 3,
      "date": "1982-03-22",
      "question_number": 6,
      "source_url": "...",
      "text": "Questioner: ...\n\nRa: I am Ra. ...",
      "distance": 0.12   # cosine distance — lower = more similar
    }
"""

import logging
import os
import sys
from pathlib import Path
from typing import Any

import chromadb
from chromadb.config import Settings
import ollama
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────

CHROMA_PATH = Path(os.getenv("CHROMA_PERSIST_PATH", "embeddings/chroma_store"))
COLLECTION_NAME = os.getenv("CHROMA_COLLECTION", "llresearch")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
DEFAULT_TOP_K = int(os.getenv("RETRIEVAL_TOP_K", "5"))

# ── Collection access ─────────────────────────────────────────────────────────


def _get_collection() -> chromadb.Collection:
    """Open the persistent ChromaDB collection (read-only access pattern)."""
    if not CHROMA_PATH.exists():
        raise RuntimeError(
            f"ChromaDB store not found at {CHROMA_PATH}.\n"
            "Run the ingest pipeline first: bash scripts/run_ingest.sh"
        )
    client = chromadb.PersistentClient(
        path=str(CHROMA_PATH),
        settings=Settings(anonymized_telemetry=False),
    )
    collection = client.get_collection(name=COLLECTION_NAME)
    return collection


# ── Embedding ─────────────────────────────────────────────────────────────────


def _embed_query(query: str) -> list[float]:
    """
    Embed the user query using the same model used during ingestion.
    The embedding model must match exactly — mismatched models will produce
    meaningless similarity scores.
    """
    client = ollama.Client(host=OLLAMA_BASE_URL)
    try:
        response = client.embeddings(model=EMBED_MODEL, prompt=query)
        return response.embedding
    except Exception as e:
        raise RuntimeError(
            f"Failed to embed query via Ollama ({OLLAMA_BASE_URL}).\n"
            f"Is Ollama running with '{EMBED_MODEL}' available?\n"
            f"Error: {e}"
        ) from e


# ── Result formatting ─────────────────────────────────────────────────────────


def _format_results(
    chroma_results: dict[str, Any],
) -> list[dict]:
    """
    Convert raw ChromaDB query results into our standard result schema.
    ChromaDB returns parallel lists: ids, documents, metadatas, distances.
    """
    results = []
    ids = chroma_results.get("ids", [[]])[0]
    documents = chroma_results.get("documents", [[]])[0]
    metadatas = chroma_results.get("metadatas", [[]])[0]
    distances = chroma_results.get("distances", [[]])[0]

    for doc_id, text, meta, dist in zip(ids, documents, metadatas, distances):
        results.append(
            {
                "id": doc_id,
                "session": meta.get("session"),
                "book": meta.get("book"),
                "date": meta.get("date"),
                "question_number": meta.get("question_number"),
                "source_url": meta.get("source_url"),
                "questioner": meta.get("questioner"),
                "entity": meta.get("entity"),
                "text": text,
                "distance": round(dist, 4),
            }
        )

    return results


# ── Search functions ──────────────────────────────────────────────────────────


def semantic_search(
    query: str,
    top_k: int = DEFAULT_TOP_K,
) -> list[dict]:
    """
    Find the top_k most semantically similar chunks to the query.

    Args:
        query:  Natural language question or concept to search for.
        top_k:  Number of results to return.

    Returns:
        List of result dicts, sorted by ascending distance (most similar first).
    """
    collection = _get_collection()
    query_embedding = _embed_query(query)

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(top_k, collection.count()),
        include=["documents", "metadatas", "distances"],
    )

    formatted = _format_results(results)
    logger.info(
        f"Semantic search: '{query[:60]}...' → {len(formatted)} results "
        f"(top distance: {formatted[0]['distance'] if formatted else 'N/A'})"
    )
    return formatted


def hybrid_search(
    query: str,
    top_k: int = DEFAULT_TOP_K,
    session: int | None = None,
    book: int | None = None,
    entity: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> list[dict]:
    """
    Semantic search with optional metadata filters.

    Filters are applied by ChromaDB before similarity scoring.
    You can narrow results to a specific session, book, or entity
    (useful for "What did Ra say in Book 2 about harvest?").

    Args:
        query:      Natural language query.
        top_k:      Max results to return.
        session:    Filter to a specific session number (1–106).
        book:       Filter to a specific book (1–5).
        entity:     Filter by channeled entity (e.g. "Ra").
        date_from:  ISO date string lower bound (inclusive).
        date_to:    ISO date string upper bound (inclusive).

    Returns:
        List of result dicts, sorted by ascending distance.
    """
    # Build ChromaDB where clause
    where_conditions: list[dict] = []

    if session is not None:
        where_conditions.append({"session": {"$eq": session}})
    if book is not None:
        where_conditions.append({"book": {"$eq": book}})
    if entity is not None:
        where_conditions.append({"entity": {"$eq": entity}})
    # Date filtering — ChromaDB stores dates as strings so we compare lexicographically.
    # ISO format (YYYY-MM-DD) sorts correctly as strings.
    if date_from is not None:
        where_conditions.append({"date": {"$gte": date_from}})
    if date_to is not None:
        where_conditions.append({"date": {"$lte": date_to}})

    # Combine conditions with $and if multiple filters
    where: dict | None = None
    if len(where_conditions) == 1:
        where = where_conditions[0]
    elif len(where_conditions) > 1:
        where = {"$and": where_conditions}

    collection = _get_collection()
    query_embedding = _embed_query(query)

    query_kwargs: dict[str, Any] = {
        "query_embeddings": [query_embedding],
        "n_results": min(top_k, collection.count()),
        "include": ["documents", "metadatas", "distances"],
    }
    if where is not None:
        query_kwargs["where"] = where

    results = collection.query(**query_kwargs)
    formatted = _format_results(results)

    filter_desc = ", ".join(
        f"{k}={v}"
        for k, v in [
            ("session", session),
            ("book", book),
            ("entity", entity),
        ]
        if v is not None
    )
    logger.info(
        f"Hybrid search: '{query[:60]}' [filters: {filter_desc or 'none'}] "
        f"→ {len(formatted)} results"
    )
    return formatted


def get_by_session(session_n: int) -> list[dict]:
    """
    Retrieve all chunks from a specific session, ordered by question number.
    Useful for session browsing without a query.
    """
    collection = _get_collection()

    results = collection.get(
        where={"session": {"$eq": session_n}},
        include=["documents", "metadatas"],
    )

    ids = results.get("ids", [])
    documents = results.get("documents", [])
    metadatas = results.get("metadatas", [])

    chunks = []
    for doc_id, text, meta in zip(ids, documents, metadatas):
        chunks.append(
            {
                "id": doc_id,
                "session": meta.get("session"),
                "book": meta.get("book"),
                "date": meta.get("date"),
                "question_number": meta.get("question_number"),
                "source_url": meta.get("source_url"),
                "questioner": meta.get("questioner"),
                "entity": meta.get("entity"),
                "text": text,
                "distance": None,  # Not ranked by similarity — browsing mode
            }
        )

    # Sort by question number
    chunks.sort(key=lambda c: c["question_number"] or 0)
    return chunks


def collection_stats() -> dict:
    """Return basic stats about the ChromaDB collection."""
    collection = _get_collection()
    count = collection.count()
    return {
        "collection": COLLECTION_NAME,
        "total_chunks": count,
        "embed_model": EMBED_MODEL,
        "chroma_path": str(CHROMA_PATH),
    }
