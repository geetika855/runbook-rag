"""FastAPI service for the runbook-RAG assistant.

Endpoints:
    GET  /health    - liveness probe + index statistics
    GET  /runbooks  - list of indexed runbooks
    POST /ask       - ask an incident question, get a grounded answer
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from pydantic import BaseModel, Field

from src.rag import (
    DEFAULT_K,
    MIN_SCORE,
    extractive_answer,
    get_components,
    retrieve,
)


class AskRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=2000)
    k: int = Field(default=DEFAULT_K, ge=1, le=10)


class Match(BaseModel):
    source: str
    title: str
    section: str
    score: float


class AskResponse(BaseModel):
    answer: str
    sources: list[str]
    matches: list[Match]


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load the embedding model + FAISS index once at startup and reuse them
    # for every request instead of reloading per query.
    _, chunks, _ = get_components()
    app.state.chunks = chunks
    yield


app = FastAPI(title="Runbook-RAG", version="0.1.0", lifespan=lifespan)


@app.get("/health")
def health():
    chunks = app.state.chunks
    return {
        "status": "ok",
        "runbooks": len({c["source"] for c in chunks}),
        "chunks": len(chunks),
    }


@app.get("/runbooks")
def list_runbooks():
    seen: dict[str, str] = {}
    for chunk in app.state.chunks:
        seen.setdefault(chunk["source"], chunk["title"])
    return [{"file": f, "title": t} for f, t in sorted(seen.items())]


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest):
    results = retrieve(req.question, k=req.k)
    relevant = [r for r in results if r["score"] >= MIN_SCORE]
    answer = extractive_answer(req.question, k=req.k, results=results)
    return AskResponse(
        answer=answer,
        sources=sorted({r["source"] for r in relevant}),
        matches=[
            Match(
                source=r["source"],
                title=r["title"],
                section=r["section"],
                score=round(r["score"], 3),
            )
            for r in relevant
        ],
    )
