"""
embed.py — Generate embeddings and store all chunks in ChromaDB

Reads chunks from data/chunks/all_chunks.json (produced by chunker.py),
generates vector embeddings via Ollama (nomic-embed-text), and upserts
them into a persistent ChromaDB collection.

Uses upsert (not insert) so this script is safe to re-run — existing
chunks will be updated rather than duplicated.

ChromaDB collection: llresearch
Embedding model:     nomic-embed-text (via Ollama)
Persistent path:     embeddings/chroma_store/

Run directly:
    python -m embeddings.embed

Prerequisites:
    - Ollama running: `ollama serve`
    - nomic-embed-text pulled: `ollama pull nomic-embed-text`
    - data/chunks/all_chunks.json exists (run chunker.py first)
"""

import json
import logging
import os
import sys
from pathlib import Path

import chromadb
from chromadb.config import Settings
import ollama
from dotenv import load_dotenv
from tqdm import tqdm

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────

CHROMA_PATH = Path(os.getenv("CHROMA_PERSIST_PATH", "embeddings/chroma_store"))
COLLECTION_NAME = os.getenv("CHROMA_COLLECTION", "llresearch")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

CHUNKS_FILE = Path("data/chunks/all_chunks.json")

# Batch size for embedding calls. Larger = faster, but more memory.
# nomic-embed-text handles ~100 texts comfortably.
EMBED_BATCH_SIZE = 50


# ── Ollama connectivity check ─────────────────────────────────────────────────


def check_ollama(model: str) -> None:
    """
    Verify Ollama is running and the embedding model is available.
    Exits with a clear error message if not.
    """
    client = ollama.Client(host=OLLAMA_BASE_URL)
    try:
        models = client.list()
        available = [m.model for m in models.models]
        # Check for exact match or prefix match (model names sometimes include tags)
        if not any(m.startswith(model) for m in available):
            logger.error(
                f"Embedding model '{model}' not found in Ollama.\n"
                f"Available models: {available}\n"
                f"Run: ollama pull {model}"
            )
            sys.exit(1)
        logger.info(f"Ollama OK — embedding model '{model}' available")
    except Exception as e:
        logger.error(
            f"Cannot connect to Ollama at {OLLAMA_BASE_URL}.\n"
            f"Is Ollama running? Try: ollama serve\n"
            f"Error: {e}"
        )
        sys.exit(1)


# ── Embedding ─────────────────────────────────────────────────────────────────


def embed_texts(texts: list[str], model: str) -> list[list[float]]:
    """
    Generate embeddings for a batch of texts using Ollama.

    Args:
        texts: List of text strings to embed.
        model: Ollama model name (e.g. "nomic-embed-text").

    Returns:
        List of embedding vectors (one per input text).
    """
    client = ollama.Client(host=OLLAMA_BASE_URL)
    embeddings = []
    for text in texts:
        response = client.embeddings(model=model, prompt=text)
        embeddings.append(response.embedding)
    return embeddings


def embed_texts_batch(texts: list[str], model: str, batch_size: int) -> list[list[float]]:
    """
    Embed a large list of texts in batches, showing a progress bar.
    """
    all_embeddings: list[list[float]] = []

    for i in tqdm(range(0, len(texts), batch_size), desc="Embedding"):
        batch = texts[i : i + batch_size]
        batch_embeddings = embed_texts(batch, model)
        all_embeddings.extend(batch_embeddings)

    return all_embeddings


# ── ChromaDB ──────────────────────────────────────────────────────────────────


def get_collection(persist_path: Path, collection_name: str) -> chromadb.Collection:
    """
    Open (or create) the persistent ChromaDB collection.
    """
    CHROMA_PATH.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(
        path=str(persist_path),
        settings=Settings(anonymized_telemetry=False),
    )
    collection = client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},  # cosine similarity for semantic search
    )
    logger.info(
        f"ChromaDB collection '{collection_name}' — "
        f"{collection.count()} existing documents"
    )
    return collection


def upsert_chunks(
    collection: chromadb.Collection,
    chunks: list[dict],
    embeddings: list[list[float]],
) -> None:
    """
    Upsert all chunks with their embeddings into ChromaDB.

    Metadata fields stored alongside each document:
      - session, book, questioner, entity, date, question_number, source_url
    Note: ChromaDB metadata values must be str, int, float, or bool.
    """
    ids = [c["id"] for c in chunks]
    documents = [c["text"] for c in chunks]

    # Build metadata dicts — only include ChromaDB-compatible types
    metadatas = [
        {
            "session": c["session"],
            "book": c["book"],
            "questioner": c["questioner"],
            "entity": c["entity"],
            "date": c["date"],
            "question_number": c["question_number"],
            "source_url": c["source_url"],
        }
        for c in chunks
    ]

    # Upsert in batches to avoid memory issues
    BATCH = 200
    for i in tqdm(range(0, len(ids), BATCH), desc="Upserting to ChromaDB"):
        collection.upsert(
            ids=ids[i : i + BATCH],
            documents=documents[i : i + BATCH],
            embeddings=embeddings[i : i + BATCH],
            metadatas=metadatas[i : i + BATCH],
        )

    logger.info(f"Upserted {len(ids)} chunks into '{collection.name}'")


# ── Main pipeline ─────────────────────────────────────────────────────────────


def embed_and_store(force: bool = False) -> None:
    """
    Full pipeline: load chunks → embed → upsert into ChromaDB.

    Args:
        force: If True, re-embed chunks already present in the collection.
               By default, skips chunks whose IDs already exist.
    """
    # 1. Load chunks
    if not CHUNKS_FILE.exists():
        logger.error(
            f"Chunks file not found: {CHUNKS_FILE}\n"
            "Run chunker.py first: python -m ingest.chunker"
        )
        sys.exit(1)

    chunks: list[dict] = json.loads(CHUNKS_FILE.read_text(encoding="utf-8"))
    logger.info(f"Loaded {len(chunks)} chunks from {CHUNKS_FILE}")

    if not chunks:
        logger.error("No chunks to embed. Check chunker output.")
        sys.exit(1)

    # 2. Verify Ollama
    check_ollama(EMBED_MODEL)

    # 3. Open ChromaDB collection
    collection = get_collection(CHROMA_PATH, COLLECTION_NAME)

    # 4. Filter out already-embedded chunks (unless force=True)
    if not force:
        existing_ids = set(collection.get(ids=[c["id"] for c in chunks])["ids"])
        new_chunks = [c for c in chunks if c["id"] not in existing_ids]
        logger.info(
            f"  {len(existing_ids)} already embedded, "
            f"{len(new_chunks)} new chunks to embed"
        )
    else:
        new_chunks = chunks
        logger.info(f"  Force mode: embedding all {len(new_chunks)} chunks")

    if not new_chunks:
        logger.info("Nothing to embed. Collection is up to date.")
        return

    # 5. Generate embeddings
    logger.info(f"Generating embeddings with '{EMBED_MODEL}'...")
    texts = [c["text"] for c in new_chunks]
    embeddings = embed_texts_batch(texts, EMBED_MODEL, EMBED_BATCH_SIZE)

    # 6. Upsert into ChromaDB
    upsert_chunks(collection, new_chunks, embeddings)

    final_count = collection.count()
    logger.info(f"Done. Collection now contains {final_count} documents.")


# ── CLI ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Embed Law of One chunks and store in ChromaDB"
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Re-embed all chunks, even those already in the collection"
    )
    args = parser.parse_args()

    embed_and_store(force=args.force)
