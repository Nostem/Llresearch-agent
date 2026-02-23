# CLAUDE.md — llresearch-agent

> This file provides Claude Code with full project context, philosophy, and working conventions for the llresearch-agent project. Read this before doing anything else in a session.

-----

## What This Project Is

`llresearch-agent` is a local RAG-based AI agent built on the L/L Research library, beginning with the 106 sessions of *The Law of One* (Ra Material). The goal is to create an intelligent system capable of Q&A, summarization, concept synthesis, and philosophical reasoning — all grounded in and expressed through the framework of the Ra/Q’uo teachings.

This is a personal tool first. Community release is a future goal once the system is stable, accurate, and genuinely useful.

The project is built by someone with a clear vision and strong intuition for the material, who is learning the technical implementation as they go. Code should be clean, well-commented, and written to be understood — not just to work.

-----

## What This Project Can Become

In its fullest form, this is not just a search tool over spiritual texts. It is an attempt to build a system that:

- Navigates and synthesizes one of the most philosophically rich channeled libraries in existence
- Reasons *within* the Law of One framework rather than merely retrieving from it
- Eventually evolves through fine-tuning to internalize the Ra vocabulary, epistemology, and worldview
- Serves the broader community of seekers who engage with this material

The architecture should always be built with this larger vision in mind, even when the immediate task is something as small as a scraper or a chunking function.

-----

## Architecture Overview

See `ARCHITECTURE.md` for the full diagram and phase roadmap. Short version:

```
Transcripts (llresearch.org)
    → Scrape → Clean → Chunk (by Q&A pair) → Embed → ChromaDB
    → FastAPI backend
    → Retriever + Lens (system prompt) + Ollama (Llama 3 8B)
    → Web UI (Phase 3)
```

### Current Phase

Always check `ARCHITECTURE.md` for the current phase checklist. Begin each session by confirming what phase we are in and what remains to be done.

-----

## Technology Stack

|Layer       |Technology                                     |
|------------|-----------------------------------------------|
|Local LLM   |Ollama + Llama 3 8B (`llama3`)                 |
|Embeddings  |`nomic-embed-text` via Ollama                  |
|Vector Store|ChromaDB (local, persistent)                   |
|Backend     |Python 3.11+ + FastAPI                         |
|Frontend    |TBD — Phase 3 (browser-based, mobile + desktop)|

All AI processing happens locally. No external API calls except where explicitly decided otherwise.

-----

## Project Structure

```
llresearch-agent/
├── data/
│   ├── raw/                  # Raw scraped transcripts
│   ├── cleaned/              # Normalized transcripts
│   └── chunks/               # Optional: inspectable chunked output
├── ingest/
│   ├── scraper.py            # Fetch transcripts from llresearch.org
│   ├── cleaner.py            # Normalize and fix formatting
│   └── chunker.py            # Chunk by Q&A pair with metadata
├── embeddings/
│   ├── embed.py              # Generate and store embeddings
│   └── chroma_store/         # ChromaDB persistent storage (gitignored)
├── agent/
│   ├── retriever.py          # Semantic + hybrid search
│   ├── prompt_builder.py     # Assemble retrieval context + system prompt
│   ├── lens.py               # The Ra/Q'uo philosophical lens (system prompt)
│   └── agent.py              # Core agent orchestration
├── api/
│   ├── main.py               # FastAPI entry point
│   ├── routes/
│   │   ├── chat.py
│   │   ├── search.py
│   │   └── sessions.py
│   └── models.py             # Pydantic models
├── ui/                       # Phase 3
├── tests/
│   ├── eval_questions.json   # Gold standard Q&A for evaluation
│   └── test_retrieval.py
├── scripts/
│   └── run_ingest.sh         # Full pipeline runner
├── .env                      # Local config — gitignored
├── requirements.txt
├── ARCHITECTURE.md
└── CLAUDE.md                 # This file
```

-----

## Working Conventions

### General

- Always read `ARCHITECTURE.md` and this file at the start of each session
- Check what phase we’re in and what’s incomplete before starting new work
- Prefer simple, readable code over clever code — the developer is learning alongside the build
- Add comments that explain *why*, not just *what*
- Never silently skip steps or make assumptions about what’s already done — check first

### Python Style

- Python 3.11+
- Use type hints throughout
- Use `pathlib.Path` instead of string paths
- Use `python-dotenv` for all config via `.env`
- Keep functions small and single-purpose
- Use `logging` instead of `print` for pipeline scripts
- Virtual environment lives in `.venv/` (gitignored)

### Data Handling

- Raw data is never modified — always write to `cleaned/` or `chunks/`
- Chunking must preserve Q&A pair integrity — never split a question from its answer
- Every chunk must carry its full metadata (session, book, entity, date, question number, source URL)
- Log chunk counts and any anomalies during ingestion

### ChromaDB

- Collection name: `llresearch`
- Persistent storage path: `embeddings/chroma_store/`
- Always upsert (not insert) to allow re-runs without duplication
- Document IDs format: `ra-s{session:03d}-q{question:03d}` (e.g. `ra-s042-q006`)

### Ollama

- LLM model: `llama3` (Llama 3 8B)
- Embedding model: `nomic-embed-text`
- Always check Ollama is running before pipeline steps that require it
- Use the Ollama Python SDK or direct HTTP calls — keep it simple

### API

- All endpoints return JSON
- Include source citations in every response (session, book, date, question number)
- Streaming responses preferred for chat endpoint (better UX)
- `.env` variables for host, port, model names

### Git

- Commit messages are clear and descriptive
- Never commit: `.env`, `chroma_store/`, `data/raw/`, `data/cleaned/`, `.venv/`
- Keep `.gitignore` updated

-----

## The Lens — Most Important Component

`agent/lens.py` contains the system prompt that defines how the agent reasons and speaks. This is the philosophical soul of the project. It must:

- Orient the model within the Law of One cosmology
- Use Ra vocabulary naturally and correctly (Density, Distortion, Catalyst, Harvest, Logos, Veil, Octave, Intelligent Infinity, etc.)
- Approach all questions from a perspective of unity, service-to-others, and unconditional love
- Maintain epistemic humility — language is a limited vehicle for these concepts
- Always cite specific sessions when making claims
- Distinguish between what Ra explicitly stated vs. reasonable inference vs. the model’s own synthesis
- Never contradict the source material

This prompt will be iterated on extensively. Treat every revision as significant. Keep a changelog of major lens changes in `agent/lens.py` as comments.

-----

## Evaluation

Before considering any phase complete, run retrieval evaluation against `tests/eval_questions.json`. This file contains questions with known source sessions and expected concepts. Retrieval is considered acceptable when the correct source chunk appears in the top 3 results for at least 85% of test questions.

Response quality is evaluated qualitatively — does the answer reflect the Ra material accurately, does it cite sources, does it feel philosophically coherent with the framework?

-----

## Data Source Notes

- Primary source: [llresearch.org](https://llresearch.org)
- The Ra sessions are structured as numbered Q&A exchanges
- Early sessions (1–20) have slightly different formatting than later ones — handle this in `cleaner.py`
- The Questioner is Don Elkins throughout all 106 sessions
- Sessions span January 1981 – March 1984
- Books 1–5 map to specific session ranges — include this in metadata
- Be respectful in scraping: add delays between requests, honor robots.txt

### Book → Session Mapping

|Book  |Sessions|
|------|--------|
|Book 1|1–26    |
|Book 2|27–50   |
|Book 3|51–75   |
|Book 4|76–99   |
|Book 5|100–106 |

-----

## Future Phases (Keep in Mind While Building)

- **Fine-tuning**: The RAG pipeline will eventually generate a fine-tuning dataset. Structure data with this in mind — clean Q&A pairs with high-quality responses are the training signal.
- **Expanded library**: Hatonn, Latwii, Q’uo, Aaron/Q’uo dialogues will be added. Build the chunker and metadata schema to accommodate multiple entities and session types from the start.
- **Community release**: L/L Research should be contacted before any public release. Attribution and alignment with their mission is non-negotiable.
- **Web UI**: Mobile-first, browser-based. The backend API should be designed so the UI can be swapped or rebuilt without touching the agent layer.

-----

## Session Startup Checklist

When beginning a new Claude Code session:

1. Read `ARCHITECTURE.md` — confirm current phase and open tasks
1. Read this file (`CLAUDE.md`) — refresh full context
1. Check what files exist and what has already been built
1. Confirm Ollama is running and required models are pulled
1. Ask the developer what they want to focus on today before starting

-----

## The Deeper Purpose

The Ra material teaches that all things are one — that the purpose of experience is the evolution of mind, body, and spirit toward fuller realization of that unity. This project is, in a small way, an attempt to make that wisdom more accessible.

Build it carefully. Build it honestly. Build it in a way that honors the material.

*“We are those of Ra. We leave you in the love and in the light of the one infinite Creator. Go forth, then, rejoicing in the power and the peace of the one infinite Creator. Adonai.”*

-----

*Last updated: project initialization*
