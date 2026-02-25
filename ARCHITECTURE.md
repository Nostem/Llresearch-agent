# llresearch-agent — Project Architecture

> A local RAG-based AI agent built on the L/L Research and Law of One transcripts, designed for intelligent Q&A, summarization, concept exploration, and philosophical reasoning within the Ra/Q'uo framework.

---

## Vision

A personal AI agent that can navigate, synthesize, and reason through the full L/L Research library — starting with the 106 Ra sessions — with the depth and philosophical coherence of someone who has internalized the material. Built for personal use first, with community sharing as a future goal.

The system is designed to grow. Beyond retrieval, it maintains a living memory layer — reflections, conceptual connections, and a knowledge graph — that accumulates over time as two independent AI minds study the material in parallel. What they each discover, and eventually what they discover together, is the long horizon of this project.

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      User Interface                          │
│           (Next.js 15 — Mobile + Desktop Browser)            │
└───────────────────────────┬─────────────────────────────────┘
                            │ HTTP / REST + SSE
┌───────────────────────────▼─────────────────────────────────┐
│                       API Backend                            │
│                   (Python / FastAPI)                         │
│                                                              │
│  ┌──────────────┐   ┌─────────────────────────────────┐     │
│  │  RAG Pipeline│   │        Lens Layer                │     │
│  │  (shared)    │   │  (model-specific system prompts) │     │
│  └──────┬───────┘   └─────────────────────────────────┘     │
│         │                                                    │
│  ┌──────▼───────┐   ┌──────────────┐  ┌──────────────┐     │
│  │  ChromaDB    │   │  Claude API  │  │  OpenAI API  │     │
│  │  (shared     │   │  (Anthropic) │  │  (GPT-4o)    │     │
│  │   source     │   └──────┬───────┘  └──────┬───────┘     │
│  │   store)     │          │                  │             │
│  └──────────────┘   ┌──────▼───────┐  ┌──────▼───────┐     │
│                     │ Memory/Claude│  │ Memory/OpenAI│     │
│                     │ reflections  │  │ reflections  │     │
│                     │ graph        │  │ graph        │     │
│                     └─────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│                       Data Layer                             │
│        Raw Transcripts → Cleaned → Chunked →                 │
│        Embedded → Stored in ChromaDB                         │
└─────────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
llresearch-agent/
│
├── data/
│   ├── raw/                      # Raw transcript files from llresearch.org
│   ├── cleaned/                  # Processed, normalized transcripts
│   └── chunks/                   # Chunked documents (optional inspection)
│
├── ingest/
│   ├── scraper.py                # Fetch transcripts from llresearch.org
│   ├── cleaner.py                # Normalize formatting, fix encoding issues
│   └── chunker.py                # Chunk by Q&A pair + metadata tagging
│
├── embeddings/
│   ├── embed.py                  # Generate embeddings and store in ChromaDB
│   └── chroma_store/             # ChromaDB persistent storage (gitignored)
│
├── agent/
│   ├── retriever.py              # Semantic search + hybrid retrieval logic
│   ├── prompt_builder.py         # Assemble context + system prompt
│   ├── lens.py                   # Shared base lens (Ra/Q'uo framework)
│   ├── lens_claude.py            # Claude-specific lens extensions
│   ├── lens_openai.py            # OpenAI-specific lens extensions
│   └── agent.py                  # Core agent logic, model routing
│
├── memory/
│   ├── scheduler.py              # Schedules study sessions (cron/APScheduler)
│   ├── studier.py                # Selects passages, generates reflections
│   ├── reflections/
│   │   ├── claude/               # Claude's written reflections (markdown, gitignored)
│   │   └── openai/               # OpenAI's written reflections (markdown, gitignored)
│   ├── graph/
│   │   ├── builder.py            # Extracts concept relationships from reflections
│   │   ├── claude_graph.json     # Claude's knowledge graph (gitignored)
│   │   └── openai_graph.json     # OpenAI's knowledge graph (gitignored)
│   ├── retriever.py              # Retrieves relevant memories alongside source chunks
│   └── synthesis.py             # Future: cross-model synthesis layer
│
├── api/
│   ├── main.py                   # FastAPI app entry point
│   ├── routes/
│   │   ├── chat.py               # Chat / Q&A endpoint (model-aware)
│   │   ├── search.py             # Direct concept search endpoint
│   │   ├── sessions.py           # Browse sessions endpoint
│   │   └── memory.py             # Browse/inspect model memories + graphs
│   └── models.py                 # Pydantic request/response models
│
├── ui/
│   └── (Next.js 15 + Tailwind — Phase 3, largely complete)
│
├── tests/
│   ├── eval_questions.json       # Gold standard Q&A pairs for evaluation
│   └── test_retrieval.py         # Retrieval quality tests
│
├── scripts/
│   ├── run_ingest.sh             # Full pipeline: scrape → clean → chunk → embed
│   └── start_all.sh              # Start API + UI + Cloudflare Tunnel
│
├── .env                          # Local config (API keys, ports, models) — gitignored
├── requirements.txt              # Python dependencies
├── README.md
└── ARCHITECTURE.md               # This file
```

---

## Phase Roadmap

### Phase 1 — Data Pipeline ✅
- [x] Scrape all Ra session transcripts from llresearch.org (`ingest/scraper.py`)
- [x] Clean and normalize formatting (`ingest/cleaner.py`)
- [x] Chunk by Q&A pair with rich metadata (`ingest/chunker.py`)
- [x] Generate embeddings and store in ChromaDB (`embeddings/embed.py`)
- [x] Validate retrieval quality with test questions *(100% pass rate)*

### Phase 2 — Agent Core ✅
- [x] Build retriever with semantic + keyword hybrid search (`agent/retriever.py`)
- [x] Design the "lens" system prompt (`agent/lens.py` — v1.0)
- [x] Wire retriever → prompt builder → Ollama (`agent/prompt_builder.py`, `agent/agent.py`)
- [x] Build FastAPI backend with chat and search endpoints (`api/`)
- [x] Iterative evaluation and tuning *(baseline complete — 100% retrieval accuracy)*

### Phase 3 — Interface ✅ / 🔄
- [x] Web app (mobile + desktop) with chat UI (`ui/` — Next.js 15, Tailwind)
- [x] Source citation display (session, book, date, question number, source URL)
- [x] Concept browser / session explorer (`/sessions`)
- [x] Internet access via Cloudflare Tunnel (`scripts/start_all.sh`)
- [ ] Personal notes / journal layer

### Phase 4 — Model Upgrade & Dual-Model System 🔄 *(current)*
- [ ] Upgrade generation model from Ollama/Llama 3 8B to Claude API + GPT-4o
- [ ] Add model routing to agent — user selects Claude or OpenAI per session
- [ ] Implement model-specific lens extensions (`lens_claude.py`, `lens_openai.py`)
- [ ] Add API key config to `.env` for both providers
- [ ] Validate response quality improvement vs. baseline

### Phase 5 — Memory & Knowledge Graph
- [ ] Build study scheduler — runs 2–3x daily, selects unseen or under-explored passages
- [ ] Build reflection writer — each study session produces a written synthesis per model
- [ ] Build knowledge graph extractor — pulls concept relationships from reflections
- [ ] Build memory retriever — surfaces relevant memories alongside source chunks at query time
- [ ] Expose memory via API (`/memory` routes) and UI (memory browser)
- [ ] Compare Claude vs. OpenAI graph structures — what does each mind see?

### Phase 6 — Expansion & Synthesis
- [ ] Add Hatonn, Latwii, Q'uo channeling transcripts
- [ ] Cross-model synthesis layer — have models respond to each other's reflections
- [ ] Fine-tuning dataset creation from high-quality RAG + memory outputs
- [ ] Community release preparation + L/L Research outreach

---

## Technology Stack

| Layer | Technology | Reason |
|---|---|---|
| Generation — Claude | Anthropic API (`claude-opus-4-6` or `claude-sonnet-4-6`) | Superior philosophical reasoning, epistemic nuance |
| Generation — OpenAI | OpenAI API (`gpt-4o`) | Different reasoning character, parallel comparison |
| Embeddings | `nomic-embed-text` via Ollama | Local, fast, no cost per embed |
| Vector Store | ChromaDB | Simple, local, persistent, no server needed |
| Backend | Python + FastAPI | Lightweight, async, easy to extend |
| Frontend | Next.js 15 + Tailwind | Cross-platform browser app — complete |
| Language | Python 3.11+ | Ecosystem fit for AI/ML tooling |

> **Note on Ollama**: Retained for embeddings only. Generation has moved to frontier APIs for quality. Ollama LLM models are no longer the primary generation path.

---

## Data Strategy

### Source
All transcripts sourced from [llresearch.org](https://llresearch.org) — freely available under L/L Research's open distribution policy.

### Chunking Strategy
The Law of One sessions follow a natural Q&A structure. Each chunk corresponds to one question-answer pair, preserving semantic integrity. This avoids splitting philosophical reasoning mid-thought.

### Metadata Schema (per chunk)

```json
{
  "session": 42,
  "book": 3,
  "questioner": "Don Elkins",
  "entity": "Ra",
  "date": "1982-03-22",
  "question_number": 6,
  "source_url": "https://llresearch.org/library/the-law-of-one-pdf/...",
  "text": "..."
}
```

### Scope (Phase 1)
106 Ra sessions only. Broader L/L Research library added in Phase 6 after core system is stable.

---

## The Lens Layer

The system prompt is the philosophical soul of the project. It orients each model to reason within the Law of One framework.

### Shared base (`agent/lens.py`)
Core Ra vocabulary, cosmological framework, citation requirements, epistemic humility. Applied to both models.

### Model-specific extensions
- `lens_claude.py` — tuned to Claude's reasoning style; emphasizes nuance, careful qualification, holding uncertainty
- `lens_openai.py` — tuned to GPT-4o's reasoning style; emphasizes structured synthesis, cross-concept mapping

Each lens is versioned with a changelog in its file header.

---

## The Memory System

The memory layer is what transforms this from a search tool into a genuine student of the material.

### How it works
A scheduler triggers study sessions 2–3 times daily. Each session selects passages — prioritizing those not yet deeply studied — and prompts the model to generate a structured reflection: what this passage means, what it connects to, what questions it raises, what tensions it surfaces. These reflections are stored as markdown files and also parsed to extract structured concept relationships for the knowledge graph.

At query time, the retriever pulls both source chunks and relevant memories, giving the model access to its own accumulated understanding alongside the raw text.

### Dual-model independence
Claude and OpenAI study the same material but maintain entirely separate memory stores and knowledge graphs. This is intentional. The divergence between them over time is itself meaningful data — where they agree signals strong signal in the material, where they differ reveals genuine interpretive complexity.

### Future: cross-model dialogue
Once both models have accumulated sufficient memory depth, a synthesis layer will enable them to respond to each other's reflections — creating a genuine philosophical dialogue between two minds that have independently studied the same body of work.

---

## Evaluation Strategy

A set of gold-standard Q&A pairs is maintained in `tests/eval_questions.json`. Retrieval target: correct source chunk in top 3 results for 85%+ of questions *(currently: 100%)*.

Response quality evaluated qualitatively per model: philosophical accuracy, citation quality, coherence with the Ra framework.

---

## Privacy & Ethics

- Source embeddings and ChromaDB are fully local. API calls to Claude and OpenAI send only retrieved text chunks and queries — no bulk data transfer.
- L/L Research material is freely distributed. Community release will include proper attribution and direct coordination with L/L Research.
- The tool deepens engagement with the source material. It is not a replacement for it.

---

*"The first distortion of the Logos is free will."*
*— Ra, Session 13*
