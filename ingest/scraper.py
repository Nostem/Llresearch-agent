"""
scraper.py — Fetch Law of One session transcripts from llresearch.org

Targets the HTML transcript pages for all 106 Ra sessions.
Saves rendered HTML to data/raw/ for downstream cleaning.

URL pattern:
    https://www.llresearch.org/channeling/ra-contact/{n}

NOTE: llresearch.org loads transcript content via JavaScript, so we use
Playwright (a headless browser) instead of plain requests. This ensures
the full rendered page — including the actual transcript text — is saved.

The scraper:
  - Renders each page fully before saving (waits for JS content to load)
  - Respects rate limits (configurable delay between requests)
  - Saves rendered HTML per session for reproducible re-processing
  - Skips sessions already downloaded (idempotent)
  - Logs counts and any failed sessions

Setup (one-time):
    pip install playwright
    playwright install chromium

Run directly:
    python -m ingest.scraper
"""

import logging
import time
from pathlib import Path

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import os

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────

BASE_URL = "https://www.llresearch.org/channeling/ra-contact/{n}"
TOTAL_SESSIONS = 106
RAW_DIR = Path("data/raw")
SCRAPE_DELAY = float(os.getenv("SCRAPE_DELAY", "2.0"))

# Max time (ms) to wait for the transcript content to appear on the page.
# The site loads content via JS — we wait for "Ra:" to appear in the DOM.
CONTENT_TIMEOUT_MS = 30_000


# ── Helpers ───────────────────────────────────────────────────────────────────


def session_url(n: int) -> str:
    """Return the URL for session n (1-indexed)."""
    return BASE_URL.format(n=n)


def raw_path(n: int) -> Path:
    """Return the local path where session n's rendered HTML should be saved."""
    return RAW_DIR / f"session-{n:03d}.html"


def validate_html(html: str, session_n: int) -> bool:
    """
    Quick sanity check that the rendered page contains transcript content.
    The Ra sessions always contain "I am Ra" in the body text.
    Returns False if the page seems empty or wrong.
    """
    if "I am Ra" not in html:
        logger.warning(
            f"  ? Session {session_n:03d} — 'I am Ra' not found in rendered HTML. "
            "Page may not have loaded correctly. Saving anyway for inspection."
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
    Scrape sessions [start, end] inclusive using a headless Chromium browser.

    Args:
        start: First session number to scrape (default 1).
        end:   Last session number to scrape (default 106).
        force: If True, re-download sessions already saved locally.

    Returns:
        A dict with keys "success", "skipped", "failed" and lists of session nums.
    """
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    results: dict[str, list[int]] = {"success": [], "skipped": [], "failed": []}

    logger.info(f"Starting scrape — sessions {start} to {end}")
    logger.info(f"Output directory: {RAW_DIR.resolve()}")
    logger.info(f"Delay between requests: {SCRAPE_DELAY}s")
    logger.info("Using Playwright headless Chromium for JavaScript rendering")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        )
        page = context.new_page()

        for n in range(start, end + 1):
            path = raw_path(n)

            if path.exists() and not force:
                logger.info(f"  → Session {n:03d} — already saved, skipping")
                results["skipped"].append(n)
                continue

            url = session_url(n)
            try:
                # Navigate to the page and wait for full network activity to settle.
                # Then additionally wait for "I am Ra" to appear in the DOM,
                # confirming the transcript content has actually rendered.
                page.goto(url, timeout=CONTENT_TIMEOUT_MS, wait_until="domcontentloaded")

                # Wait for the transcript text to appear — this is the signal that
                # the JavaScript has finished loading the actual content.
                page.wait_for_function(
                    "document.body.innerText.includes('I am Ra')",
                    timeout=CONTENT_TIMEOUT_MS,
                )

                html = page.content()
                validate_html(html, n)
                path.write_text(html, encoding="utf-8")
                results["success"].append(n)
                logger.info(f"  ✓ Session {n:03d} — rendered and saved ({url})")

            except PlaywrightTimeoutError:
                logger.warning(
                    f"  ✗ Session {n:03d} — timed out waiting for content ({url})"
                )
                results["failed"].append(n)

            except Exception as e:
                logger.warning(f"  ✗ Session {n:03d} — {e}")
                results["failed"].append(n)

            # Be respectful to the server — rate-limit ourselves.
            if n < end:
                time.sleep(SCRAPE_DELAY)

        browser.close()

    # ── Summary ──
    logger.info("─" * 50)
    logger.info("Scrape complete.")
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
        description="Scrape Law of One transcripts from llresearch.org (Playwright)"
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
