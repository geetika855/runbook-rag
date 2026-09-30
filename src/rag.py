"""RAG question answering over the runbook index.

Usage:
    python -m src.rag "your incident question here"
    python -m src.rag --retrieve-only "your question"   # show raw matches
    python -m src.rag --llm ollama "your question"      # use local Ollama LLM

The default answer mode is extractive: it composes a grounded answer from
the retrieved runbook sections and cites its sources. Pass ``--llm ollama``
to have a local LLM synthesize the answer instead (requires Ollama running
with a pulled model, e.g. ``ollama pull llama3.2``). Either way the model
only sees retrieved context — it cannot answer from outside the runbooks.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from src.ingest import INDEX_FILE, METADATA_FILE, EMBEDDING_MODEL, resolve_model_name

# Cosine-similarity floor below which we admit we have no relevant runbook.
MIN_SCORE = 0.25
DEFAULT_K = 4
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2"

SYSTEM_PROMPT = """\
You are an on-call assistant answering from the team's runbooks.
Rules:
- Answer ONLY using the runbook excerpts in <context>. Do not use outside knowledge.
- If the excerpts do not cover the question, say so plainly and suggest what to check next.
- Structure the answer: likely cause, diagnosis steps, fix steps.
- Cite sources as [source: filename.md] after the claims they support.
- Keep it concise and operational: commands first, explanation second.
"""


def load_index():
    """Load the FAISS index, chunk metadata, and embedding model."""
    if not INDEX_FILE.exists():
        raise SystemExit(
            f"Index not found at {INDEX_FILE}. Run 'python -m src.ingest' first."
        )
    index = faiss.read_index(str(INDEX_FILE))
    chunks = json.loads(METADATA_FILE.read_text(encoding="utf-8"))
    model = SentenceTransformer(resolve_model_name())
    return index, chunks, model


_components = None


def get_components():
    """Load index/chunks/model once per process and reuse them."""
    global _components
    if _components is None:
        _components = load_index()
    return _components


def retrieve(question: str, k: int = DEFAULT_K):
    """Return the top-k runbook chunks for a question, each with a score."""
    index, chunks, model = get_components()
    query_vec = model.encode([question], normalize_embeddings=True).astype(np.float32)
    scores, ids = index.search(query_vec, k)
    results = []
    for score, idx in zip(scores[0], ids[0]):
        if idx == -1:
            continue
        chunk = dict(chunks[int(idx)])
        chunk["score"] = float(score)
        results.append(chunk)
    return results


def _cite(chunk: dict) -> str:
    return f"[source: {chunk['source']}]"


def extractive_answer(
    question: str, k: int = DEFAULT_K, results: list | None = None
) -> str:
    """Compose a grounded answer directly from retrieved runbook sections."""
    if results is None:
        results = retrieve(question, k=k)
    relevant = [r for r in results if r["score"] >= MIN_SCORE]
    if not relevant:
        return (
            "I don't have a runbook covering this yet. "
            "No retrieved section was relevant enough to answer from.\n\n"
            "What to do next: check the closest runbooks manually, or add a "
            "new runbook to data/runbooks/ and re-run ingestion."
        )

    lines = [f"Based on {len(relevant)} runbook section(s):\n"]
    for r in relevant:
        header = f"### {r['title']} — {r['section']} {_cite(r)}"
        lines.append(header)
        lines.append(r["text"].strip())
        lines.append("")
    sources = sorted({r["source"] for r in relevant})
    lines.append("Sources: " + ", ".join(sources))
    return "\n".join(lines).strip()


def ollama_answer(question: str, k: int = DEFAULT_K) -> str:
    """Synthesize an answer with a local Ollama model over retrieved context."""
    results = retrieve(question, k=k)
    relevant = [r for r in results if r["score"] >= MIN_SCORE]
    if not relevant:
        return "I don't have a runbook covering this yet."

    context = "\n\n".join(
        f"[{r['source']} :: {r['section']}]\n{r['text']}" for r in relevant
    )
    prompt = f"{SYSTEM_PROMPT}\n<context>\n{context}\n</context>\n\nQuestion: {question}\nAnswer:"
    payload = json.dumps(
        {"model": OLLAMA_MODEL, "prompt": prompt, "stream": False}
    ).encode()
    req = urllib.request.Request(
        OLLAMA_URL, data=payload, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read())["response"].strip()
    except OSError as exc:
        return (
            f"Could not reach Ollama at {OLLAMA_URL} ({exc}). "
            "Is 'ollama serve' running? Falling back to extractive answer:\n\n"
            + extractive_answer(question, k=k)
        )


def answer(question: str, llm: str | None = None, k: int = DEFAULT_K) -> str:
    if llm == "ollama":
        return ollama_answer(question, k=k)
    return extractive_answer(question, k=k)


def main() -> None:
    parser = argparse.ArgumentParser(description="Ask the runbook assistant.")
    parser.add_argument("question", nargs="*", help="Incident question to answer")
    parser.add_argument(
        "--retrieve-only", action="store_true", help="Show raw retrieved chunks"
    )
    parser.add_argument("--llm", choices=["ollama"], help="LLM backend for synthesis")
    parser.add_argument("-k", type=int, default=DEFAULT_K, help="Chunks to retrieve")
    args = parser.parse_args()

    if not args.question:
        parser.print_help()
        raise SystemExit(1)
    question = " ".join(args.question)

    if args.retrieve_only:
        for r in retrieve(question, k=args.k):
            print(f"--- score={r['score']:.3f} | {r['source']} :: {r['section']}")
            print(r["text"][:500].strip() + "\n")
        return
    print(answer(question, llm=args.llm, k=args.k))


if __name__ == "__main__":
    main()
