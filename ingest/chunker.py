"""
chunker.py — Produce final RAG chunks from cleaned session JSON files

Reads from data/cleaned/ and outputs a flat list of chunk dicts to
data/chunks/all_chunks.json, plus individual per-session chunk files.

Each chunk corresponds to exactly one Q&A pair — we never split a
question from its answer. This preserves the semantic integrity of
Ra's responses, which are often dense with meaning that depends on
the question context.

Chunk document ID format:
    ra-s{session:03d}-q{question:03d}
    e.g. ra-s042-q006

Metadata schema per chunk:
    {
      "id": "ra-s042-q006",
      "session": 42,
      "book": 3,
      "questioner": "Don Elkins",
      "entity": "Ra",
      "date": "1982-03-22",
      "question_number": 6,
      "source_url": "https://llresearch.org/channeling/the-law-of-one/session-42",
      "text": "<full Q&A text for embedding>"
    }

Run directly:
    python -m ingest.chunker
"""

import json
import logging
import re
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────

CLEANED_DIR = Path("data/cleaned")
CHUNKS_DIR = Path("data/chunks")

# Minimum character length to include a chunk.
# Very short answers (e.g. "Ra: I am Ra. This is correct.") are included
# but anything below this is suspicious and logged.
MIN_CHUNK_CHARS = 50


# ── Chunk construction ─────────────────────────────────────────────────────────


def make_chunk_id(session: int, question: int) -> str:
    """Return the canonical document ID for a Q&A chunk."""
    return f"ra-s{session:03d}-q{question:03d}"


def build_chunk_text(question: str, answer: str) -> str:
    """
    Combine question and answer into a single text string for embedding.

    We format it as:
        Questioner: <question>

        Ra: <answer>

    This ensures the embedding captures both the question context and
    Ra's response as a unified semantic unit.
    """
    return f"Questioner: {question.strip()}\n\nRa: {answer.strip()}"


def chunk_session(session_data: dict) -> list[dict]:
    """
    Convert one cleaned session dict into a list of chunk dicts.

    Args:
        session_data: Parsed JSON from data/cleaned/session-NNN.json

    Returns:
        List of chunk dicts, one per Q&A pair.
    """
    session_n = session_data["session"]
    chunks = []
    anomalies = []

    for pair in session_data.get("raw_pairs", []):
        q_num = pair["question_number"]
        question = pair.get("question", "").strip()
        answer = pair.get("answer", "").strip()

        if not question and not answer:
            logger.debug(f"  Session {session_n:03d} Q{q_num}: empty pair, skipping")
            continue

        text = build_chunk_text(question, answer)

        if len(text) < MIN_CHUNK_CHARS:
            anomalies.append(q_num)
            logger.warning(
                f"  Session {session_n:03d} Q{q_num}: "
                f"very short chunk ({len(text)} chars)"
            )

        chunk = {
            "id": make_chunk_id(session_n, q_num),
            "session": session_n,
            "book": session_data["book"],
            "questioner": session_data["questioner"],
            "entity": session_data["entity"],
            "date": session_data["date"],
            "question_number": q_num,
            "source_url": session_data["source_url"],
            "text": text,
        }
        chunks.append(chunk)

    if anomalies:
        logger.warning(
            f"  Session {session_n:03d}: {len(anomalies)} short chunks: {anomalies}"
        )

    return chunks


# ── Main pipeline ─────────────────────────────────────────────────────────────


def chunk_all(force: bool = False) -> list[dict]:
    """
    Chunk all sessions in data/cleaned/.

    Returns:
        Flat list of all chunks across all sessions.
    """
    CHUNKS_DIR.mkdir(parents=True, exist_ok=True)

    all_chunks: list[dict] = []

    cleaned_files = sorted(CLEANED_DIR.glob("session-*.json"))

    if not cleaned_files:
        logger.warning(
            f"No cleaned session files found in {CLEANED_DIR}. "
            "Run cleaner.py first."
        )
        return []

    logger.info(f"Chunking {len(cleaned_files)} session files...")

    for cleaned_file in cleaned_files:
        match = re.match(r"session-(\d+)\.json", cleaned_file.name)
        if not match:
            continue
        n = int(match.group(1))

        # Per-session chunk file (useful for inspection)
        session_chunk_path = CHUNKS_DIR / f"session-{n:03d}-chunks.json"
        if session_chunk_path.exists() and not force:
            logger.info(f"  → Session {n:03d} — chunks already exist, loading")
            existing = json.loads(session_chunk_path.read_text(encoding="utf-8"))
            all_chunks.extend(existing)
            continue

        session_data = json.loads(cleaned_file.read_text(encoding="utf-8"))
        chunks = chunk_session(session_data)

        session_chunk_path.write_text(
            json.dumps(chunks, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        logger.info(
            f"  ✓ Session {n:03d} — {len(chunks)} chunks"
        )
        all_chunks.extend(chunks)

    # Write the combined flat file — useful for bulk embedding operations
    combined_path = CHUNKS_DIR / "all_chunks.json"
    combined_path.write_text(
        json.dumps(all_chunks, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    logger.info("─" * 50)
    logger.info(f"Chunking complete.")
    logger.info(f"  Total chunks: {len(all_chunks)}")
    logger.info(f"  Combined file: {combined_path}")

    # Sanity check: report any sessions with 0 chunks
    indexed_sessions = {c["session"] for c in all_chunks}
    sessions_with_no_chunks = []
    for f in cleaned_files:
        m = re.match(r"session-(\d+)\.json", f.name)
        if m and int(m.group(1)) not in indexed_sessions:
            sessions_with_no_chunks.append(f.name)
    if sessions_with_no_chunks:
        logger.warning(f"  Sessions with 0 chunks: {sessions_with_no_chunks}")

    return all_chunks


# ── CLI ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Chunk cleaned Law of One sessions into Q&A pairs for embedding"
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Re-chunk sessions already processed"
    )
    args = parser.parse_args()

    chunks = chunk_all(force=args.force)
    logger.info(f"Done. {len(chunks)} total chunks ready for embedding.")
