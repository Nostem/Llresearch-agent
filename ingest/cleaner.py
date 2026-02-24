"""
cleaner.py — Parse and normalize raw HTML session transcripts

Takes raw HTML files from data/raw/ and produces clean, structured JSON
in data/cleaned/ — one file per session.

The output JSON per session looks like:
{
  "session": 42,
  "book": 3,
  "date": "1982-03-22",
  "questioner": "Don Elkins",
  "entity": "Ra",
  "source_url": "https://llresearch.org/channeling/the-law-of-one/session-42",
  "raw_pairs": [
    {
      "question_number": 1,
      "question": "...",
      "answer": "..."
    },
    ...
  ]
}

Notes on the source material:
  - Sessions 1–26 are in Book 1, formatted slightly differently from later sessions
  - All 106 sessions are Q&A pairs between Don Elkins (Questioner) and Ra
  - Ra's answers always begin with "Ra: I am Ra."
  - Question numbering restarts at 1 for each session

Run directly:
    python -m ingest.cleaner
"""

import json
import logging
import re
from pathlib import Path

from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────

RAW_DIR = Path("data/raw")
CLEANED_DIR = Path("data/cleaned")

# Book → session range mapping (inclusive)
BOOK_MAP: dict[int, tuple[int, int]] = {
    1: (1, 26),
    2: (27, 50),
    3: (51, 75),
    4: (76, 99),
    5: (100, 106),
}


def session_to_book(n: int) -> int:
    for book, (start, end) in BOOK_MAP.items():
        if start <= n <= end:
            return book
    raise ValueError(f"Session {n} not in any known book range")


# ── HTML Parsing ───────────────────────────────────────────────────────────────


def extract_date(soup: BeautifulSoup, session_n: int) -> str:
    """
    Try to find the session date in the HTML.
    llresearch.org pages typically include the date in the header or metadata.
    Falls back to "unknown" if not found.
    """
    # Common patterns: look for text that matches a date format
    date_patterns = [
        r"\b(\w+ \d{1,2},\s*\d{4})\b",     # "January 15, 1981"
        r"\b(\d{4}-\d{2}-\d{2})\b",          # "1981-01-15"
    ]

    # Search visible text for a date near the top of the document
    text = soup.get_text()
    for pattern in date_patterns:
        match = re.search(pattern, text[:2000])  # Look in first ~2000 chars
        if match:
            return match.group(1)

    return "unknown"


def extract_qa_pairs_from_html(html: str, session_n: int) -> list[dict]:
    """
    Parse Q&A pairs from an llresearch.org session HTML page.

    The site wraps transcript content in identifiable HTML structure.
    We extract all text, then use the consistent Ra/Questioner pattern
    to split it into Q&A pairs.

    Returns a list of dicts: [{question_number, question, answer}, ...]
    """
    soup = BeautifulSoup(html, "lxml")

    # Remove navigation, header, footer, script, style elements
    for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
        tag.decompose()

    # Get clean text — preserving newlines between block elements
    text = soup.get_text(separator="\n")
    text = _normalize_whitespace(text)

    pairs = _parse_qa_pairs(text, session_n)

    if not pairs:
        # Fallback: the HTML structure might differ — try a simpler split
        logger.warning(
            f"Session {session_n:03d}: no Q&A pairs parsed from HTML. "
            "Trying fallback parser."
        )
        pairs = _parse_qa_pairs_fallback(text, session_n)

    return pairs


def _normalize_whitespace(text: str) -> str:
    """Collapse excessive blank lines, normalize whitespace."""
    # Replace smart quotes and em-dashes with plain ASCII equivalents
    text = text.replace("\u2018", "'").replace("\u2019", "'")
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    text = text.replace("\u2014", "--").replace("\u2013", "-")

    # Collapse 3+ blank lines to 2
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _parse_qa_pairs(text: str, session_n: int) -> list[dict]:
    """
    Parse the full session text into Q&A pairs.

    The Law of One has a very consistent structure:
      - Numbered questions: "1. Questioner: ..." or just "Questioner: ..."
      - Ra's answers: "Ra: I am Ra. ..."

    We split on Ra's signature opening "Ra: I am Ra" and pair with
    the preceding question block.
    """
    pairs = []

    # Pattern for a question block (various numbering styles)
    # Matches: "1." or "1.0" or "RA CONTACT SESSION n" headers before text
    # Then "Questioner:" (or just the numbered line before Ra speaks)

    # Split on Ra's answer marker
    ra_marker = re.compile(
        r"(?m)^(?:Ra:|RA:)\s*I am Ra[.,]?",
        re.IGNORECASE,
    )

    segments = ra_marker.split(text)

    if len(segments) < 2:
        return []

    # segments[0] is content before the first Ra answer (session header)
    # segments[1..] are Ra's answers; the question precedes each
    question_counter = 0

    # Work through answer segments
    for i, answer_text in enumerate(segments[1:], start=1):
        # The question for this answer is the tail of the previous segment
        preceding = segments[i - 1]

        # Extract the question: look for "Questioner:" near the end of preceding
        question = _extract_question(preceding)

        if question is None:
            # First segment might just be session header — skip
            continue

        question_counter += 1
        answer = "I am Ra. " + answer_text.strip()

        pairs.append(
            {
                "question_number": question_counter,
                "question": question.strip(),
                "answer": answer,
            }
        )

    return pairs


def _extract_question(text: str) -> str | None:
    """
    Extract the question from a block of text that precedes a Ra answer.
    The question is typically near the end of this block.
    """
    # Look for "Questioner:" marker
    q_match = re.search(r"Questioner:\s*(.+?)$", text, re.IGNORECASE | re.DOTALL)
    if q_match:
        # Take text after "Questioner:" — trim trailing whitespace
        q_text = q_match.group(1).strip()
        # Remove anything that's clearly not the question (e.g., trailing Ra markers)
        q_text = re.sub(r"\s*Ra:.*$", "", q_text, flags=re.DOTALL).strip()
        if q_text:
            return q_text

    # Fallback: if no "Questioner:" found, take the last non-empty paragraph
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if paragraphs:
        last = paragraphs[-1]
        # Skip if it looks like a session header
        if len(last) > 20 and not re.match(r"^Session\s+\d+", last, re.I):
            return last

    return None


def _parse_qa_pairs_fallback(text: str, session_n: int) -> list[dict]:
    """
    Alternative parser for sessions with non-standard formatting.
    Uses numbered question pattern (e.g. "1.1", "1.2", "2.0") found in
    early sessions (Books 1–2).
    """
    pairs = []
    # Pattern: "n.m Questioner: ..." followed by "Ra: I am Ra. ..."
    pattern = re.compile(
        r"(\d+\.\d+)\s+Questioner:\s+(.*?)(?=\d+\.\d+\s+Ra:|$)",
        re.DOTALL | re.IGNORECASE,
    )
    ra_pattern = re.compile(r"Ra:\s+I am Ra[.,]?\s+(.*?)(?=\d+\.\d+\s+|$)", re.DOTALL)

    for i, match in enumerate(pattern.finditer(text), start=1):
        question_text = match.group(2).strip()

        # Find corresponding Ra answer immediately following
        ra_match = ra_pattern.search(text, match.end())
        answer_text = ra_match.group(1).strip() if ra_match else ""

        pairs.append(
            {
                "question_number": i,
                "question": question_text,
                "answer": "I am Ra. " + answer_text if answer_text else "",
            }
        )

    return pairs


# ── Main pipeline ─────────────────────────────────────────────────────────────


def clean_session(n: int, force: bool = False) -> dict | None:
    """
    Clean one session: parse HTML → structured dict.
    Returns the cleaned session dict, or None if skipped/failed.
    """
    raw_path = RAW_DIR / f"session-{n:03d}.html"
    cleaned_path = CLEANED_DIR / f"session-{n:03d}.json"

    if cleaned_path.exists() and not force:
        logger.info(f"  → Session {n:03d} — already cleaned, skipping")
        return None

    if not raw_path.exists():
        logger.warning(f"  ✗ Session {n:03d} — raw file not found: {raw_path}")
        return None

    html = raw_path.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "lxml")

    date = extract_date(soup, n)
    pairs = extract_qa_pairs_from_html(html, n)

    session_data = {
        "session": n,
        "book": session_to_book(n),
        "date": date,
        "questioner": "Don Elkins",
        "entity": "Ra",
        "source_url": f"https://llresearch.org/channeling/the-law-of-one/session-{n}",
        "raw_pairs": pairs,
    }

    cleaned_path.write_text(
        json.dumps(session_data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    logger.info(
        f"  ✓ Session {n:03d} — {len(pairs)} Q&A pairs extracted, date: {date}"
    )
    return session_data


def clean_all(force: bool = False) -> dict[str, list[int]]:
    """
    Clean all sessions found in data/raw/.

    Returns:
        A dict with keys "success", "skipped", "failed" and lists of session nums.
    """
    CLEANED_DIR.mkdir(parents=True, exist_ok=True)
    results: dict[str, list[int]] = {"success": [], "skipped": [], "failed": []}

    raw_files = sorted(RAW_DIR.glob("session-*.html"))

    if not raw_files:
        logger.warning(f"No raw HTML files found in {RAW_DIR}. Run scraper first.")
        return results

    logger.info(f"Cleaning {len(raw_files)} session files...")

    for raw_file in raw_files:
        # Extract session number from filename
        match = re.match(r"session-(\d+)\.html", raw_file.name)
        if not match:
            continue
        n = int(match.group(1))

        result = clean_session(n, force=force)
        if result is None:
            cleaned_path = CLEANED_DIR / f"session-{n:03d}.json"
            if cleaned_path.exists():
                results["skipped"].append(n)
            else:
                results["failed"].append(n)
        else:
            results["success"].append(n)

    logger.info("─" * 50)
    logger.info(f"Cleaning complete.")
    logger.info(f"  Cleaned: {len(results['success'])}")
    logger.info(f"  Skipped: {len(results['skipped'])}")
    logger.info(f"  Failed:  {len(results['failed'])}")

    return results


# ── CLI ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Clean and parse raw Law of One HTML transcripts"
    )
    parser.add_argument(
        "--session", type=int, default=None,
        help="Clean a single session (default: all)"
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Re-clean sessions already processed"
    )
    args = parser.parse_args()

    if args.session:
        clean_session(args.session, force=args.force)
    else:
        clean_all(force=args.force)
