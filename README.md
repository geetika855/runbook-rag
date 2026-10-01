# Runbook-RAG: Incident Response Assistant

An assistant that answers on-call questions using your team's own incident
runbooks. Ask "how did we fix the last inference latency spike?" and get a
grounded, step-by-step answer — with sources cited, not hallucinations.

Built as an AIOps learning project: retrieval-augmented generation (RAG) over
DevOps runbooks, packaged as a FastAPI service with Docker and CI.

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

1. **Ingest** — runbooks in `data/runbooks/` are split into sections, chunked
   with overlap, and embedded with `all-MiniLM-L6-v2` into a FAISS index
   (11 runbooks → 67 chunks).
2. **Retrieve** — a question is embedded and matched against the index with
   cosine similarity.
3. **Answer** — by default, an extractive answer is composed directly from the
   retrieved runbook sections (no LLM required), citing which runbook each
   step came from. Questions with no sufficiently relevant runbook are
   refused instead of answered. Optionally, `--llm ollama` synthesizes the
   answer with a local Ollama model.

## Setup

Requires Python 3.12+.

```bash
pip install -r requirements.txt

# Build the knowledge base from the runbooks (downloads the embedding model
# from Hugging Face on first run, ~90 MB)
python -m src.ingest
```

`requirements.txt` pins CPU-only PyTorch wheels, so this works on machines
without a GPU.

## Usage

### CLI

```bash
# Ask a question (extractive answer, grounded in runbooks)
python -m src.rag "pods are crashlooping after the latest deploy, what do I check first?"

# See the raw retrieved chunks and scores instead
python -m src.rag "EKS ran out of IP addresses" --retrieve-only

# Retrieve more/fewer chunks
python -m src.rag "tls certificate expiring" -k 6

# Optional: synthesize with a local Ollama model instead of extractive answering
python -m src.rag "queue backlog is growing" --llm ollama
```

### API

```bash
uvicorn src.api:app
```

| Method | Path        | Description                           |
| ------ | ----------- | ------------------------------------- |
| GET    | `/health`   | liveness probe + index stats          |
| GET    | `/runbooks` | list of indexed runbooks              |
| POST   | `/ask`      | ask a question, get a grounded answer |

```bash
curl -X POST localhost:8000/ask \
  -H 'Content-Type: application/json' \
  -d '{"question": "pods are crashlooping after the latest deploy"}'
```

The embedding model and FAISS index load once at startup and are shared
across requests.

### Docker

```bash
docker compose up --build
# API on http://localhost:8000
```

The image builds the FAISS index at build time, so the container starts
with zero setup. A `HEALTHCHECK` polls `/health`.

### Demo

```bash
./demo.sh
```

Runs ingestion, three CLI questions (two incidents + one refused
out-of-scope question), and the API end to end.

## Testing

```bash
python -m pytest tests/ -q
```

10 tests: retrieval quality (correct runbook retrieved for EKS, CrashLoop,
and TLS questions), out-of-scope refusal, citation presence, and API
endpoint behavior (health stats, runbook listing, `/ask` answers, input
validation).

CI (`.github/workflows/ci.yml`) runs the test suite and builds + smoke-tests
the Docker image on every push to `main`.

## Project layout

```
runbook-rag/
├── data/runbooks/      # incident runbooks (markdown) — the knowledge base
├── src/
│   ├── ingest.py       # chunk + embed runbooks → FAISS index
│   ├── rag.py          # retrieval + grounded answers (+ CLI)
│   └── api.py          # FastAPI service (GET /health, /runbooks, POST /ask)
├── tests/              # retrieval + API tests
├── demo.sh             # reproducible end-to-end demo
├── Dockerfile          # CPU image: builds index, serves API on :8000
├── docker-compose.yml
└── .github/workflows/ci.yml
```

## Tech stack

Python · FAISS · sentence-transformers · FastAPI · Uvicorn · Docker ·
pytest · GitHub Actions

## Why this exists

On-call engineers lose time hunting through wikis and Slack threads during
incidents. A RAG assistant over curated runbooks puts the team's own fixes
one question away — with sources cited, so every step is verifiable.
