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
    The site renders dates in a <time> element or as visible text.
    Falls back to "unknown" if not found.
    """
    # Try a <time> element first (most reliable)
    time_el = soup.find("time")
    if time_el:
        dt = time_el.get("datetime") or time_el.get_text(strip=True)
        if dt:
            return dt

    # Search all visible text for a date pattern
    # The date is typically rendered somewhere on the page after JS loads
    text = soup.get_text()
    date_patterns = [
        r"\b(January|February|March|April|May|June|July|August|"
        r"September|October|November|December)\s+\d{1,2},\s*\d{4}\b",
        r"\b\d{4}-\d{2}-\d{2}\b",
    ]
    for pattern in date_patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(0)

    return "unknown"


def extract_qa_pairs_from_html(html: str, session_n: int) -> list[dict]:
    """
    Parse Q&A pairs from an llresearch.org session HTML page.

    The actual DOM structure (confirmed via debug) is:
      <article id="fountain">
        <h4 class="speaker">1.0Ra</h4>      ← Ra's opening monologue
        <p>...</p> ...
        <h4 class="speaker">1.1Questioner</h4>
        <p>[question text]</p>
        <h4 class="speaker">Ra</h4>          ← Ra's answer gets its own h4
        <p>I am Ra. [answer text]</p>
        <h4 class="speaker">1.2Questioner</h4>
        ...
      </article>

    Strategy:
      1. Walk all elements in document order, building a list of speaker
         turns: [(speaker_text, [p_elements]), ...]
      2. Find consecutive Questioner→Ra turn pairs and combine them.

    Returns a list of dicts: [{question_number, question, answer}, ...]
    """
    soup = BeautifulSoup(html, "lxml")

    for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
        tag.decompose()

    all_elements = soup.find_all(["h4", "p"])

    speaker_h4s = [
        el for el in all_elements
        if el.name == "h4" and "speaker" in (el.get("class") or [])
    ]
    if not speaker_h4s:
        logger.warning(
            f"Session {session_n:03d}: no <h4 class='speaker'> elements found. "
            "Page structure may have changed."
        )
        return []

    # Build speaker turns: [(speaker_label, [p_tags]), ...]
    # speaker_label is the full text of the h4, e.g. "1.1Questioner" or "Ra"
    turns: list[tuple[str, list]] = []
    current_speaker: str | None = None
    current_ps: list = []

    for el in all_elements:
        if el.name == "h4" and "speaker" in (el.get("class") or []):
            if current_speaker is not None:
                turns.append((current_speaker, current_ps))
            current_speaker = el.get_text(strip=True)
            current_ps = []
        elif el.name == "p" and current_speaker is not None:
            # Skip editorial notes like "[Two-minute pause.]"
            if "notes" not in " ".join(el.get("class") or []):
                current_ps.append(el)

    if current_speaker is not None:
        turns.append((current_speaker, current_ps))

    # Pair consecutive Questioner → Ra turns
    pairs = []
    question_counter = 0

    for i, (speaker, q_ps) in enumerate(turns):
        if "questioner" not in speaker.lower():
            continue

        # The next turn should be Ra
        if i + 1 >= len(turns):
            continue
        next_speaker, a_ps = turns[i + 1]
        if "questioner" in next_speaker.lower():
            # Two questioner turns in a row — no Ra answer found
            logger.warning(
                f"Session {session_n:03d}: Questioner turn '{speaker}' not followed "
                f"by Ra (got '{next_speaker}'). Skipping."
            )
            continue

        question_text = _clean_text(
            "\n\n".join(p.get_text(separator=" ", strip=True) for p in q_ps)
        )
        answer_text = _clean_text(
            "\n\n".join(p.get_text(separator=" ", strip=True) for p in a_ps)
        )

        question_counter += 1
        pairs.append(
            {
                "question_number": question_counter,
                "question": question_text,
                "answer": answer_text,
            }
        )

    return pairs


def _clean_text(text: str) -> str:
    """Normalize whitespace and replace Unicode punctuation with ASCII equivalents."""
    text = text.replace("\u2018", "'").replace("\u2019", "'")
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    text = text.replace("\u2014", "--").replace("\u2013", "-")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


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
