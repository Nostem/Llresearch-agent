"""
test_retrieval.py — Retrieval quality evaluation against gold-standard Q&A pairs

Evaluates whether the correct source sessions appear in the top-k
retrieved results for each evaluation question.

Acceptance threshold: 85% of questions must have the correct session
in the top 3 results (as defined in eval_questions.json).

Run with:
    pytest tests/test_retrieval.py -v

Or for a full eval report:
    python tests/test_retrieval.py
"""

import json
import logging
import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv

# When run directly as `python tests/test_retrieval.py`, Python sets sys.path[0]
# to the tests/ directory, which means `from agent.retriever import ...` fails.
# This ensures the project root is always on the path.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

load_dotenv()

logger = logging.getLogger(__name__)

EVAL_FILE = Path("tests/eval_questions.json")
TOP_K_EVAL = 5       # Retrieve this many results per question
PASS_THRESHOLD = 0.85  # 85% of questions must pass


def load_eval_questions() -> list[dict]:
    """Load gold-standard evaluation questions."""
    if not EVAL_FILE.exists():
        raise FileNotFoundError(f"Eval questions file not found: {EVAL_FILE}")
    return json.loads(EVAL_FILE.read_text())


def retrieval_hits_expected(
    results: list[dict],
    expected_sessions: list[int],
    top_k: int = 3,
) -> bool:
    """
    Return True if any of the expected sessions appear in the top_k results.

    We check the top 3 results — a well-tuned retriever should put at least
    one ground-truth session in the top 3 for 85%+ of questions.
    """
    retrieved_sessions = {r["session"] for r in results[:top_k]}
    return bool(retrieved_sessions & set(expected_sessions))


# ── pytest tests ───────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def retriever():
    """Import retriever only when actually running tests — avoids ChromaDB errors
    if the collection doesn't exist yet (e.g. during CI without data)."""
    try:
        from agent.retriever import semantic_search
        return semantic_search
    except Exception as e:
        pytest.skip(f"Retriever not available (collection may not be built yet): {e}")


@pytest.fixture(scope="module")
def eval_questions():
    return load_eval_questions()


@pytest.mark.parametrize("question_data", load_eval_questions() if EVAL_FILE.exists() else [])
def test_retrieval_hits_expected_session(question_data, retriever):
    """
    For each eval question, verify the correct session appears in top 3 results.
    """
    question = question_data["question"]
    expected_sessions = question_data["expected_sessions"]
    eval_id = question_data["id"]

    results = retriever(query=question, top_k=TOP_K_EVAL)

    hit = retrieval_hits_expected(results, expected_sessions, top_k=3)

    retrieved_sessions = [r["session"] for r in results[:3]]
    assert hit, (
        f"\n[{eval_id}] MISS — Question: {question!r}\n"
        f"  Expected sessions: {expected_sessions}\n"
        f"  Retrieved sessions (top 3): {retrieved_sessions}\n"
        f"  Notes: {question_data.get('notes', '')}"
    )


# ── Standalone evaluation report ──────────────────────────────────────────────


def run_full_eval() -> dict:
    """
    Run the full evaluation and return a summary report.
    Prints pass/fail per question and overall score.
    """
    from agent.retriever import semantic_search

    questions = load_eval_questions()
    results_summary = []
    passes = 0

    print(f"\n{'─' * 60}")
    print(f"Retrieval Evaluation — {len(questions)} questions, top-3 hit rate")
    print(f"{'─' * 60}\n")

    for q in questions:
        results = semantic_search(query=q["question"], top_k=TOP_K_EVAL)
        hit = retrieval_hits_expected(results, q["expected_sessions"], top_k=3)
        retrieved_sessions = [r["session"] for r in results[:3]]

        status = "PASS" if hit else "FAIL"
        if hit:
            passes += 1

        print(
            f"[{status}] {q['id']}: {q['question'][:60]!r}\n"
            f"       Expected: {q['expected_sessions']}  |  "
            f"Got top-3: {retrieved_sessions}\n"
        )

        results_summary.append(
            {
                "id": q["id"],
                "question": q["question"],
                "pass": hit,
                "expected_sessions": q["expected_sessions"],
                "retrieved_sessions": retrieved_sessions,
            }
        )

    score = passes / len(questions)
    threshold_met = score >= PASS_THRESHOLD

    print(f"{'─' * 60}")
    print(
        f"Score: {passes}/{len(questions)} = {score:.0%}  "
        f"(threshold: {PASS_THRESHOLD:.0%})  —  "
        f"{'PASS' if threshold_met else 'FAIL'}"
    )
    print(f"{'─' * 60}\n")

    return {
        "score": score,
        "passes": passes,
        "total": len(questions),
        "threshold_met": threshold_met,
        "results": results_summary,
    }


if __name__ == "__main__":
    run_full_eval()
