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
┌─────────────┐    ┌──────────────┐    ┌─────────────┐
│  Embedder   │───▶│  FAISS index │───▶│     LLM     │──▶ grounded answer
│ (MiniLM)    │    │  (runbooks)  │    │  (Q&A chain)│    + cited sources
└─────────────┘    └──────────────┘    └─────────────┘
```

1. **Ingest** — runbooks in `data/runbooks/` are chunked and embedded.
2. **Retrieve** — a question is embedded and matched against the FAISS index.
3. **Answer** — an LLM answers using only the retrieved runbook chunks, citing
   which runbook each step came from.

## Quickstart

```bash
pip install -r requirements.txt

# 1. Build the knowledge base from runbooks
python -m src.ingest

# 2. Ask a question from the CLI
python -m src.rag "pods are crashlooping after the latest deploy, what do I check first?"

# 3. Or run the API
uvicorn src.api:app --reload
```

## Project layout

```
runbook-rag/
├── data/runbooks/      # incident runbooks (markdown) — the knowledge base
├── src/
│   ├── ingest.py       # chunk + embed runbooks → FAISS index
│   ├── rag.py          # retrieval + LLM answer chain (+ CLI)
│   └── api.py          # FastAPI service wrapper
├── tests/              # retrieval quality tests
├── Dockerfile
└── .github/workflows/ # CI: lint + tests
```

## Tech stack

Python · LangChain · FAISS · sentence-transformers · FastAPI · Docker ·
GitHub Actions

## Why this exists

On-call engineers lose time hunting through wikis and Slack threads during
incidents. A RAG assistant over curated runbooks cuts mean time to resolution
by putting the team's own fixes one question away.
