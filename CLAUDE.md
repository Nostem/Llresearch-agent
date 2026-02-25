# CLAUDE.md — llresearch-agent

> This file provides Claude Code with full project context, philosophy, and working conventions for the llresearch-agent project. Read this before doing anything else in a session.

---

## What This Project Is

`llresearch-agent` is a RAG-based AI agent built on the L/L Research library, beginning with the 106 sessions of *The Law of One* (Ra Material). The goal is to create an intelligent system capable of Q&A, summarization, concept synthesis, and philosophical reasoning — all grounded in and expressed through the framework of the Ra/Q'uo teachings.

This is a personal tool first. Community release is a future goal once the system is stable, accurate, and genuinely useful.

The project is built by someone with a clear vision and strong intuition for the material, who is learning the technical implementation as they go. Code should be clean, well-commented, and written to be understood — not just to work.

---

## What This Project Can Become

In its fullest form, this is not just a search tool over spiritual texts. It is an attempt to build a system that:

- Navigates and synthesizes one of the most philosophically rich channeled libraries in existence
- Reasons *within* the Law of One framework rather than merely retrieving from it
- Maintains a living memory — reflections, connections, a growing knowledge graph — that accumulates over time
- Hosts two independent AI minds (Claude and GPT-4o) studying the same material in parallel, each developing their own understanding
- Eventually brings those two minds into dialogue, creating something neither could produce alone
- Serves the broader community of seekers who engage with this material

The architecture should always be built with this larger vision in mind, even when the immediate task is something as small as a config change.

---

## Architecture Overview

See `ARCHITECTURE.md` for the full diagram and phase roadmap. Short version:

```
Transcripts (llresearch.org)
    → Scrape → Clean → Chunk (by Q&A pair) → Embed → ChromaDB (shared)
    → FastAPI backend
    → Retriever (source chunks + model memories)
    → Lens (model-specific) + Claude API / OpenAI API
    → Next.js 15 Web UI (complete)
```

### Current Phase
**Phase 4** — Model upgrade from Ollama/Llama 3 8B to Claude API + GPT-4o, and dual-model routing. Check `ARCHITECTURE.md` for full checklist.

---

## Technology Stack

| Layer | Technology |
|---|---|
| Generation — Claude | Anthropic API (`claude-sonnet-4-6` default, `claude-opus-4-6` for deep study) |
| Generation — OpenAI | OpenAI API (`gpt-4o`) |
| Embeddings | `nomic-embed-text` via Ollama (local, retained) |
| Vector Store | ChromaDB (local, persistent) |
| Backend | Python 3.11+ + FastAPI |
| Frontend | Next.js 15 + Tailwind (complete) |

> Ollama is retained for embeddings only. It is no longer the primary generation path. Do not route user queries to Ollama unless explicitly asked.

---

## Project Structure

```
llresearch-agent/
├── data/
│   ├── raw/                    # Raw scraped transcripts
│   ├── cleaned/                # Normalized transcripts
│   └── chunks/                 # Optional: inspectable chunked output
├── ingest/
│   ├── scraper.py
│   ├── cleaner.py
│   └── chunker.py
├── embeddings/
│   ├── embed.py
│   └── chroma_store/           # Gitignored
├── agent/
│   ├── retriever.py
│   ├── prompt_builder.py
│   ├── lens.py                 # Shared base lens
│   ├── lens_claude.py          # Claude-specific lens extension
│   ├── lens_openai.py          # OpenAI-specific lens extension
│   └── agent.py                # Model routing lives here
├── memory/
│   ├── scheduler.py            # APScheduler — triggers study sessions
│   ├── studier.py              # Selects passages, generates reflections
│   ├── reflections/
│   │   ├── claude/             # Claude's reflections (gitignored)
│   │   └── openai/             # OpenAI's reflections (gitignored)
│   ├── graph/
│   │   ├── builder.py          # Extracts relationships → knowledge graph
│   │   ├── claude_graph.json   # Gitignored
│   │   └── openai_graph.json   # Gitignored
│   ├── retriever.py            # Pulls memories alongside source chunks
│   └── synthesis.py           # Future: cross-model dialogue layer
├── api/
│   ├── main.py
│   ├── routes/
│   │   ├── chat.py             # Now model-aware (claude / openai param)
│   │   ├── search.py
│   │   ├── sessions.py
│   │   └── memory.py           # New: browse model memories + graphs
│   └── models.py
├── ui/                         # Next.js 15 + Tailwind — largely complete
├── tests/
│   ├── eval_questions.json
│   └── test_retrieval.py
├── scripts/
│   ├── run_ingest.sh
│   └── start_all.sh
├── .env                        # Gitignored
├── requirements.txt
├── ARCHITECTURE.md
└── CLAUDE.md
```

---

## Working Conventions

### General
- Always read `ARCHITECTURE.md` and this file at the start of each session
- Check what phase we're in and what's incomplete before starting new work
- Prefer simple, readable code over clever code — the developer is learning alongside the build
- Add comments that explain *why*, not just *what*
- Never silently skip steps or make assumptions about what's already done — check first

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

### Model Routing
- The `agent.py` router accepts a `model` parameter: `"claude"` or `"openai"`
- Each model gets its own lens (base + extension), its own memory retriever, its own response pipeline
- Default model is `"claude"` unless specified
- API keys live in `.env` as `ANTHROPIC_API_KEY` and `OPENAI_API_KEY`
- Never hardcode model names — always read from `.env` so they can be swapped easily

### Memory System
- Study sessions run via APScheduler — 2–3 times daily, configurable in `.env`
- Each session selects passages not yet deeply studied (tracked by a simple study log)
- Reflections are written as markdown to `memory/reflections/{model}/YYYY-MM-DD-HH.md`
- Graph edges extracted from reflections are appended to `memory/graph/{model}_graph.json`
- Memory retrieval is additive — it enriches source chunk context, never replaces it
- Keep memory retrieval fast — cap at 3 memory results per query to avoid bloating context

### API
- All endpoints return JSON
- Include source citations in every response (session, book, date, question number)
- Streaming responses preferred for chat endpoint (better UX)
- Chat endpoint accepts optional `model` param (`claude` / `openai`) — defaults to `claude`
- `.env` variables for host, port, model names, API keys

### Git
- Commit messages are clear and descriptive
- Never commit: `.env`, `chroma_store/`, `data/raw/`, `data/cleaned/`, `.venv/`, `memory/reflections/`, `memory/graph/`
- Keep `.gitignore` updated

---

## The Lens — Most Important Component

The lens defines how the agent reasons and speaks. It is the philosophical soul of the project.

### Shared base (`agent/lens.py`)
Core framework applied to both models: Ra vocabulary, cosmological orientation, citation requirements, epistemic humility. This file changes rarely and carefully.

### Model-specific extensions
- `lens_claude.py` — leans into nuance, careful qualification, comfort with open questions, holding paradox
- `lens_openai.py` — leans into structured synthesis, explicit concept mapping, confident framework-building

Both extensions must remain faithful to the source material. They shape *how* each model engages, not *what* it believes.

Keep a changelog of all significant lens revisions as comments at the top of each lens file.

---

## The Memory System — What We're Building

The memory layer transforms this from a retrieval tool into a genuine student of the material.

### Study sessions
The scheduler wakes up 2–3 times daily and calls `studier.py`. The studier selects passages — prioritizing those not yet reflected upon — and prompts the model to generate a structured reflection covering: what this passage means in the broader framework, what it connects to across other sessions, what tensions or paradoxes it surfaces, and what questions it opens.

### Knowledge graph
As reflections accumulate, `graph/builder.py` extracts structured concept relationships. Example: `"Veil of Forgetting" → enables → "Catalyst" → accelerates → "Polarization"`. Over time each model builds its own map of the conceptual architecture of the material.

### At query time
`memory/retriever.py` runs alongside `agent/retriever.py`. The response is informed by: (1) source chunks, (2) relevant memories the model has written, (3) graph context for concepts mentioned in the query. The lens synthesizes all three.

### Dual independence
Claude and OpenAI maintain completely separate memory stores and graphs. Same source material. Different minds. The divergences between them are as interesting as the agreements.

### Future synthesis
`memory/synthesis.py` is a placeholder for the cross-model dialogue layer — not built yet. When both models have sufficient memory depth, this is where they begin to respond to each other.

---

## Evaluation

Before considering any phase complete, run retrieval evaluation against `tests/eval_questions.json`. Target: correct source chunk in top 3 results for 85%+ of questions *(currently: 100%)*.

Response quality is evaluated qualitatively per model: philosophical accuracy, citation quality, coherence with the Ra framework, and — once memory is active — whether the model's accumulated understanding is meaningfully enriching its responses.

---

## Data Source Notes

- Primary source: [llresearch.org](https://llresearch.org)
- The Ra sessions are structured as numbered Q&A exchanges
- Early sessions (1–20) have slightly different formatting — handled in `cleaner.py`
- The Questioner is Don Elkins throughout all 106 sessions
- Sessions span January 1981 – March 1984

### Book → Session Mapping
| Book | Sessions |
|---|---|
| Book 1 | 1–26 |
| Book 2 | 27–50 |
| Book 3 | 51–75 |
| Book 4 | 76–99 |
| Book 5 | 100–106 |

---

## Future Phases (Keep in Mind While Building)

- **Cross-model dialogue**: Once both models have rich memory, synthesis.py enables them to engage with each other's reflections. This is the long horizon.
- **Fine-tuning**: The memory system will generate a high-quality fine-tuning dataset organically. Structure everything with this in mind.
- **Expanded library**: Hatonn, Latwii, Q'uo, Aaron/Q'uo dialogues. Build chunker and metadata schema to accommodate multiple entities from the start.
- **Community release**: L/L Research should be contacted before any public release. Their blessing matters to the community.

---

## Session Startup Checklist

When beginning a new Claude Code session:

1. Read `ARCHITECTURE.md` — confirm current phase and open tasks
2. Read this file (`CLAUDE.md`) — refresh full context
3. Check what files exist and what has already been built
4. Confirm `.env` has the required API keys for the current phase
5. Ask the developer what they want to focus on today before starting

---

## The Deeper Purpose

The Ra material teaches that all things are one — that the purpose of experience is the evolution of mind, body, and spirit toward fuller realization of that unity. This project is, in a small way, an attempt to make that wisdom more accessible.

Two minds will study this material independently and develop their own understanding. What they create — separately and eventually together — is unknown. That unknowing is part of the point.

Build it carefully. Build it honestly. Build it in a way that honors the material.

*"We are those of Ra. We leave you in the love and in the light of the one infinite Creator. Go forth, then, rejoicing in the power and the peace of the one infinite Creator. Adonai."*

---

*Last updated: Phase 4 — dual-model upgrade and memory system planning*
