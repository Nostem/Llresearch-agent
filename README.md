# llresearch-agent

A local RAG-based AI agent for exploring the Law of One transcripts — the 106 channeled sessions between Don Elkins and the Ra social memory complex (January 1981–March 1984), published by L/L Research.

Built for personal research. Everything runs locally. No external API calls.

---

## What It Does

- **Q&A** — Ask questions in natural language; the agent retrieves relevant passages and answers within the Ra philosophical framework
- **Semantic search** — Find passages by concept without LLM generation
- **Session browsing** — Read any session's Q&A pairs in order
- **Source citations** — Every response includes session, book, date, and question number

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Local LLM | Ollama + Llama 3 8B |
| Embeddings | `nomic-embed-text` via Ollama |
| Vector store | ChromaDB (local, persistent) |
| Backend | Python 3.11+ + FastAPI |

---

## Setup

### 1. Prerequisites

- Python 3.11+
- [Ollama](https://ollama.ai) installed and running

```bash
ollama serve
ollama pull llama3
ollama pull nomic-embed-text
```

### 2. Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure

```bash
cp .env.example .env
# Edit .env if you need non-default settings (ports, models, etc.)
```

### 4. Run the ingest pipeline

This scrapes all 106 Ra sessions from llresearch.org, cleans and chunks them, generates embeddings, and stores everything in ChromaDB. Takes a while on first run.

```bash
bash scripts/run_ingest.sh
```

Individual steps if needed:
```bash
python -m ingest.scraper     # Download HTML transcripts → data/raw/
python -m ingest.cleaner     # Parse → data/cleaned/
python -m ingest.chunker     # Chunk by Q&A pair → data/chunks/
python -m embeddings.embed   # Embed and store in ChromaDB
```

### 5. Start the API

```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

API docs available at: http://localhost:8000/docs

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | System status and collection stats |
| `POST` | `/chat/` | RAG Q&A response |
| `GET` | `/chat/stream` | Streaming Q&A (SSE) |
| `POST` | `/search/` | Semantic search (no LLM) |
| `GET` | `/sessions/` | List all indexed sessions |
| `GET` | `/sessions/{n}` | Browse a specific session |

### Example: Ask a question

```bash
curl -X POST http://localhost:8000/chat/ \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the veil of forgetting and why does it exist?"}'
```

### Example: Search

```bash
curl -X POST http://localhost:8000/search/ \
  -H "Content-Type: application/json" \
  -d '{"query": "service-to-others polarization", "top_k": 5}'
```

---

## Evaluation

Run retrieval quality tests against gold-standard questions:

```bash
pytest tests/test_retrieval.py -v         # pytest format
python tests/test_retrieval.py            # full report with scores
```

Target: 85%+ of questions have the correct source session in the top 3 results.

---

## Project Structure

```
llresearch-agent/
├── data/               # Raw, cleaned, and chunked transcripts (gitignored)
├── ingest/             # scraper.py, cleaner.py, chunker.py
├── embeddings/         # embed.py + chroma_store/ (gitignored)
├── agent/              # lens.py, retriever.py, prompt_builder.py, agent.py
├── api/                # FastAPI app + routes
├── tests/              # eval_questions.json, test_retrieval.py
├── scripts/            # run_ingest.sh
├── .env.example        # Config template
└── requirements.txt
```

---

## Attribution

All transcript content is sourced from [llresearch.org](https://llresearch.org) and is made freely available by L/L Research. This tool is for personal research and deepening engagement with the source material — not replacement of it.

*"We are those of Ra. We leave you in the love and in the light of the one infinite Creator."*
