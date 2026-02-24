"""
prompt_builder.py — Assemble the final prompt from retrieval context + lens

Takes retrieved chunks and the user's question and produces:
  1. A system prompt (lens + context instructions)
  2. A user message with the query and the retrieved evidence

The context is formatted so the LLM knows exactly where each piece of
information came from, making citation discipline easier to maintain.
"""

from agent.lens import get_system_prompt


def format_context_block(chunks: list[dict]) -> str:
    """
    Format retrieved chunks as a readable context block for the prompt.

    Each chunk is presented with its source citation clearly labeled
    so the LLM can reference it naturally in the response.

    Example output:
        [Source: Session 6, Question 14 | Book 1 | 1981-04-15]
        Questioner: ...
        Ra: I am Ra. ...

        [Source: Session 17, Question 2 | Book 1 | 1981-11-02]
        ...
    """
    if not chunks:
        return "No relevant passages were retrieved for this query."

    blocks = []
    for chunk in chunks:
        session = chunk.get("session", "?")
        q_num = chunk.get("question_number", "?")
        book = chunk.get("book", "?")
        date = chunk.get("date", "unknown")
        text = chunk.get("text", "").strip()

        header = f"[Source: Session {session}, Question {q_num} | Book {book} | {date}]"
        blocks.append(f"{header}\n{text}")

    return "\n\n---\n\n".join(blocks)


def build_prompt(
    query: str,
    chunks: list[dict],
) -> tuple[str, str]:
    """
    Build the system prompt and user message for a RAG query.

    Args:
        query:  The user's question.
        chunks: Retrieved chunks from the retriever (ordered by relevance).

    Returns:
        Tuple of (system_prompt, user_message) strings.
        Pass these directly to the Ollama chat completion call.
    """
    system_prompt = get_system_prompt()

    context = format_context_block(chunks)

    # The user message combines the retrieved evidence with the question.
    # The LLM is instructed to reason from the context and cite its sources.
    user_message = f"""The following passages have been retrieved from the Law of One sessions as relevant to your question. Use them as your primary evidence. Cite specific sessions when making claims.

---

{context}

---

Question: {query}

Please answer based on the retrieved passages above. If the passages don't fully address the question, say so clearly and offer what synthesis you can from what is provided. Always cite the session source for specific claims."""

    return system_prompt, user_message


def build_search_prompt(query: str, chunks: list[dict]) -> str:
    """
    Build a simpler prompt for the /search endpoint — just formats
    results without full LLM reasoning. Returns a formatted string
    suitable for direct display.
    """
    if not chunks:
        return f"No relevant passages found for: '{query}'"

    lines = [f"Search results for: **{query}**\n"]
    for i, chunk in enumerate(chunks, start=1):
        session = chunk.get("session", "?")
        q_num = chunk.get("question_number", "?")
        book = chunk.get("book", "?")
        date = chunk.get("date", "?")
        dist = chunk.get("distance")
        dist_str = f" (similarity: {1 - dist:.2f})" if dist is not None else ""

        lines.append(
            f"**{i}. Session {session}, Q{q_num} | Book {book} | {date}**{dist_str}"
        )
        # Show a truncated preview of the chunk
        text = chunk.get("text", "")
        preview = text[:300] + "..." if len(text) > 300 else text
        lines.append(preview)
        lines.append("")

    return "\n".join(lines)
