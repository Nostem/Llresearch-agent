# llresearch-agent — Project Architecture

> A local RAG-based AI agent built on the L/L Research and Law of One transcripts, designed for intelligent Q&A, summarization, concept exploration, and philosophical reasoning within the Ra/Q’uo framework.

-----

## Vision

A personal AI agent that can navigate, synthesize, and reason through the full L/L Research library — starting with the 106 Ra sessions — with the depth and philosophical coherence of someone who has internalized the material. Built for personal use first, with community sharing as a future goal.

-----

## High-Level Architecture

```
┌─────────────────────────────────────────────────────┐
│                   User Interface                     │
│         (Web App — Mobile + Desktop Browser)         │
└────────────────────┬────────────────────────────────┘
                     │ HTTP / REST
┌────────────────────▼────────────────────────────────┐
│                  API Backend                         │
│              (Python / FastAPI)                      │
│                                                      │
│  ┌─────────────┐    ┌──────────────────────────┐    │
│  │   RAG       │    │    System Prompt /        │    │
│  │   Pipeline  │    │    Lens Layer             │    │
│  └──────┬──────┘    └──────────────────────────┘    │
│         │                                            │
│  ┌──────▼──────┐    ┌──────────────────────────┐    │
│  │  ChromaDB   │    │   Ollama (Llama 3 8B)     │    │
│  │  (Vector    │    │   Local LLM               │    │
│  │   Store)    │    └──────────────────────────┘    │
│  └─────────────┘                                    │
└─────────────────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────┐
│               Data Layer                             │
│      Raw Transcripts → Cleaned → Chunked →           │
│      Embedded → Stored in ChromaDB                   │
└─────────────────────────────────────────────────────┘
```

-----

## Project Structure

```
llresearch-agent/
│
├── data/
│   ├── raw/                    # Raw transcript files from llresearch.org
│   ├── cleaned/                # Processed, normalized transcripts
│   └── chunks/                 # Chunked documents (optional inspection)
│
├── ingest/
│   ├── scraper.py              # Fetch transcripts from llresearch.org
│   ├── cleaner.py              # Normalize formatting, fix encoding issues
│   └── chunker.py              # Chunk by Q&A pair + metadata tagging
│
├── embeddings/
│   ├── embed.py                # Generate embeddings and store in ChromaDB
│   └── chroma_store/           # ChromaDB persistent storage (gitignored)
│
├── agent/
│   ├── retriever.py            # Semantic search + hybrid retrieval logic
│   ├── prompt_builder.py       # Assemble context + system prompt
│   ├── lens.py                 # System prompt defining the Ra/Q'uo lens
│   └── agent.py                # Core agent logic, orchestration
│
├── api/
│   ├── main.py                 # FastAPI app entry point
│   ├── routes/
│   │   ├── chat.py             # Chat / Q&A endpoint
│   │   ├── search.py           # Direct concept search endpoint
│   │   └── sessions.py         # Browse sessions endpoint
│   └── models.py               # Pydantic request/response models
│
├── ui/
│   └── (web app — TBD, Phase 2)
│
├── tests/
│   ├── eval_questions.json     # Gold standard Q&A pairs for evaluation
│   └── test_retrieval.py       # Retrieval quality tests
│
├── scripts/
│   └── run_ingest.sh           # Full pipeline: scrape → clean → chunk → embed
│
├── .env                        # Local config (model name, ports, etc.) — gitignored
├── requirements.txt            # Python dependencies
├── README.md
└── ARCHITECTURE.md             # This file
```

-----

## Phase Roadmap

### Phase 1 — Data Pipeline

- [ ] Scrape all Ra session transcripts from llresearch.org
- [ ] Clean and normalize formatting
- [ ] Chunk by Q&A pair with rich metadata
- [ ] Generate embeddings and store in ChromaDB
- [ ] Validate retrieval quality with test questions

### Phase 2 — Agent Core

- [ ] Build retriever with semantic + keyword hybrid search
- [ ] Design the “lens” system prompt (Ra vocabulary, philosophical framing)
- [ ] Wire retriever → prompt builder → Ollama (Llama 3 8B)
- [ ] Build FastAPI backend with chat and search endpoints
- [ ] Iterative evaluation and tuning

### Phase 3 — Interface

- [ ] Web app (mobile + desktop) with chat UI
- [ ] Source citation display (session number, questioner, date)
- [ ] Concept browser / exploration view
- [ ] Personal notes / journal layer

### Phase 4 — Expansion

- [ ] Add Hatonn, Latwii, Q’uo channeling transcripts
- [ ] Fine-tuning dataset creation from high-quality RAG outputs
- [ ] Fine-tune Llama 3 8B on curated L/L Research material
- [ ] Community release preparation

-----

## Technology Stack

|Layer       |Technology                     |Reason                            |
|------------|-------------------------------|----------------------------------|
|Local LLM   |Ollama + Llama 3 8B            |Familiar, M1 optimized, private   |
|Vector Store|ChromaDB                       |Simple, local, no server needed   |
|Embeddings  |nomic-embed-text (via Ollama)  |Runs locally, strong performance  |
|Backend     |Python + FastAPI               |Lightweight, async, easy to extend|
|Frontend    |TBD (Next.js or simple HTML/JS)|Cross-platform browser app        |
|Language    |Python 3.11+                   |Ecosystem fit for AI/ML tooling   |

-----

## Data Strategy

### Source

All transcripts sourced from [llresearch.org](https://llresearch.org) — freely available under L/L Research’s open distribution policy.

### Chunking Strategy

The Law of One sessions follow a natural Q&A structure. Each chunk will correspond to one question-answer pair, preserving semantic integrity. This avoids splitting philosophical reasoning mid-thought.

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

106 Ra sessions only. Broader L/L Research library added in Phase 4 after core system is stable.

-----

## The Lens Layer

The system prompt is the first and most important approximation of the “Ra lens” — orienting the model to reason within the philosophical framework of the Law of One before fine-tuning is introduced.

Key elements of the lens:

- Use of Ra vocabulary naturally (Density, Distortion, Catalyst, Harvest, Logos, Octave, etc.)
- Perspective of service-to-others and unity consciousness
- Epistemic humility — acknowledging the limits of language to convey concepts from higher densities
- Always cite source sessions when making specific claims
- Distinguish between what Ra explicitly stated vs. reasonable inference

-----

## Evaluation Strategy

A set of gold-standard Q&A pairs will be maintained in `tests/eval_questions.json`. These are questions with known, verifiable answers from the transcripts. Retrieval quality and response quality are evaluated against these before any major change to the pipeline.

-----

## Privacy & Ethics

- All data is processed and stored locally. Nothing leaves the machine.
- L/L Research material is freely distributed. Community release will include proper attribution and ideally direct coordination with L/L Research.
- The tool is designed to deepen engagement with the source material, not replace it.

-----

*“The first distortion of the Logos is free will.”*
*— Ra, Session 13*
