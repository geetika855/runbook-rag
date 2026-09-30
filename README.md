# Runbook-RAG: Incident Response Assistant

An AI-powered assistant that answers on-call questions using your team's own
incident runbooks. Ask it "how did we fix the last inference latency spike?"
and get a grounded, step-by-step answer — with sources, not hallucinations.

Built as an AIOps learning project: retrieval-augmented generation (RAG) over
real DevOps runbooks, packaged as a FastAPI service with Docker and CI.

## How it works

```
incident question
      │
      ▼
┌─────────────┐    ┌──────────────┐    ┌──────────────────┐
│  Embedder   │───▶│  FAISS index │───▶│ Grounded answer  │──▶ runbook steps
│ (MiniLM)    │    │  (runbooks)  │    │ (extractive +    │    + cited sources
└─────────────┘    └──────────────┘    │ optional Ollama) │
                                       └──────────────────┘
```

1. **Ingest** — runbooks in `data/runbooks/` are chunked and embedded.
2. **Retrieve** — a question is embedded and matched against the FAISS index.
3. **Answer** — by default, an extractive answer is composed directly from the
   retrieved runbook sections (no LLM required), citing which runbook each
   step came from. Optionally, `--llm ollama` can synthesize with a local
   Ollama model instead.

## Quickstart

```bash
pip install -r requirements.txt

# 1. Build the knowledge base from runbooks
python -m src.ingest

# 2. Ask a question from the CLI
python -m src.rag "pods are crashlooping after the latest deploy, what do I check first?"

# 3. Or run the API
uvicorn src.api:app
```

API endpoints:

| Method | Path        | Description                              |
| ------ | ----------- | ---------------------------------------- |
| GET    | `/health`   | liveness probe + index stats             |
| GET    | `/runbooks` | list of indexed runbooks                 |
| POST   | `/ask`      | ask a question, get a grounded answer    |

```bash
curl -X POST localhost:8000/ask \
  -H 'Content-Type: application/json' \
  -d '{"question": "pods are crashlooping after the latest deploy"}'

# Or run the whole thing in Docker
docker compose up --build

## Project layout

```
runbook-rag/
├── data/runbooks/      # incident runbooks (markdown) — the knowledge base
├── src/
│   ├── ingest.py       # chunk + embed runbooks → FAISS index
│   ├── rag.py          # retrieval + grounded answers (+ CLI)
│   └── api.py          # FastAPI service (GET /health, /runbooks, POST /ask)
├── tests/              # retrieval + API tests
├── Dockerfile          # CPU image: builds index, serves API on :8000
└── docker-compose.yml
```

## Tech stack

Python · FAISS · sentence-transformers · FastAPI · Uvicorn · Docker ·
pytest

## Why this exists

On-call engineers lose time hunting through wikis and Slack threads during
incidents. A RAG assistant over curated runbooks puts the team's own fixes
one question away — with sources cited, so every step is verifiable.
