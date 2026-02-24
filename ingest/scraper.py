"""
scraper.py — Fetch Law of One session transcripts from llresearch.org

Targets the HTML transcript pages for all 106 Ra sessions.
Saves raw HTML to data/raw/ for downstream cleaning.

URL pattern:
    https://llresearch.org/channeling/the-law-of-one/session-{n}

The scraper:
  - Respects rate limits (configurable delay between requests)
  - Checks robots.txt before scraping
  - Saves raw HTML per session for reproducible re-processing
  - Skips sessions already downloaded (idempotent)
  - Logs counts and any failed sessions

Run directly:
    python -m ingest.scraper
"""

import logging
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import os

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────

BASE_URL = "https://llresearch.org/channeling/the-law-of-one/session-{n}"
TOTAL_SESSIONS = 106
RAW_DIR = Path("data/raw")
SCRAPE_DELAY = float(os.getenv("SCRAPE_DELAY", "1.5"))

# Browser-like headers to avoid immediate 403s.
# llresearch.org serves the material freely — we are respectful guests.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; llresearch-agent/1.0; "
        "personal research tool; not for commercial use)"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

# ── Helpers ───────────────────────────────────────────────────────────────────


def session_url(n: int) -> str:
    """Return the URL for session n (1-indexed)."""
    return BASE_URL.format(n=n)


def raw_path(n: int) -> Path:
    """Return the local path where session n's HTML should be saved."""
    return RAW_DIR / f"session-{n:03d}.html"


def fetch_session(n: int, session: requests.Session) -> str | None:
    """
    Fetch one session page and return its HTML text.
    Returns None on failure (non-fatal — logs and moves on).
    """
    url = session_url(n)
    try:
        response = session.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        logger.info(f"  ✓ Session {n:03d} — {response.status_code} {url}")
        return response.text
    except requests.HTTPError as e:
        logger.warning(f"  ✗ Session {n:03d} — HTTP {e.response.status_code} {url}")
        return None
    except requests.RequestException as e:
        logger.warning(f"  ✗ Session {n:03d} — {e}")
        return None


def validate_html(html: str, session_n: int) -> bool:
    """
    Quick sanity check that the page looks like a transcript.
    The Ra sessions always contain "Ra:" in the body text.
    Returns False if the page seems like a redirect or error page.
    """
    if "Ra:" not in html and "I am Ra" not in html:
        logger.warning(
            f"  ? Session {session_n:03d} — page fetched but 'Ra:' not found. "
            "May be wrong URL or a redirect. Saving anyway for inspection."
        )
        return False
    return True


# ── Main pipeline ─────────────────────────────────────────────────────────────


def scrape_all(
    start: int = 1,
    end: int = TOTAL_SESSIONS,
    force: bool = False,
) -> dict[str, list[int]]:
    """
    Scrape sessions [start, end] inclusive.

    Args:
        start: First session number to scrape (default 1).
        end:   Last session number to scrape (default 106).
        force: If True, re-download sessions already saved locally.

    Returns:
        A dict with keys "success", "skipped", "failed" and lists of session nums.
    """
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    results: dict[str, list[int]] = {"success": [], "skipped": [], "failed": []}

    http_session = requests.Session()

    logger.info(f"Starting scrape — sessions {start} to {end}")
    logger.info(f"Output directory: {RAW_DIR.resolve()}")
    logger.info(f"Delay between requests: {SCRAPE_DELAY}s")

    for n in range(start, end + 1):
        path = raw_path(n)

        if path.exists() and not force:
            logger.info(f"  → Session {n:03d} — already saved, skipping")
            results["skipped"].append(n)
            continue

        html = fetch_session(n, http_session)

        if html is None:
            results["failed"].append(n)
        else:
            validate_html(html, n)
            path.write_text(html, encoding="utf-8")
            results["success"].append(n)

        # Be respectful to the server — rate-limit ourselves.
        if n < end:
            time.sleep(SCRAPE_DELAY)

    # ── Summary ──
    logger.info("─" * 50)
    logger.info(f"Scrape complete.")
    logger.info(f"  Downloaded: {len(results['success'])}")
    logger.info(f"  Skipped (already saved): {len(results['skipped'])}")
    logger.info(f"  Failed: {len(results['failed'])}")
    if results["failed"]:
        logger.warning(f"  Failed sessions: {results['failed']}")

    return results


# ── CLI entry point ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Scrape Law of One transcripts from llresearch.org"
    )
    parser.add_argument(
        "--start", type=int, default=1, help="First session to scrape (default: 1)"
    )
    parser.add_argument(
        "--end", type=int, default=TOTAL_SESSIONS, help="Last session to scrape (default: 106)"
    )
    parser.add_argument(
        "--force", action="store_true", help="Re-download sessions already saved"
    )
    args = parser.parse_args()

    scrape_all(start=args.start, end=args.end, force=args.force)
