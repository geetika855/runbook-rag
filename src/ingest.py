"""Runbook ingestion: chunk markdown runbooks, embed, and persist a FAISS index.

Usage:
    python -m src.ingest

Reads every ``*.md`` file in ``data/runbooks/`` (except ``_TEMPLATE.md``),
splits each runbook into sections, embeds the sections with a
sentence-transformer model, and stores them in a FAISS index for
cosine-similarity retrieval. Chunk metadata (source file, runbook title,
section heading) is persisted alongside the index so answers can cite
their sources.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

RUNBOOKS_DIR = Path("data/runbooks")
INDEX_DIR = Path("data/index")
INDEX_FILE = INDEX_DIR / "faiss.index"
METADATA_FILE = INDEX_DIR / "metadata.json"

EMBEDDING_MODEL = "all-MiniLM-L6-v2"
# Local model cache (used when the HuggingFace Hub is unreachable, e.g.
# behind an egress proxy). Falls back to the Hub name when absent.
LOCAL_MODELS_DIR = Path.home() / "workspace" / "models"


def resolve_model_name() -> str:
    local = LOCAL_MODELS_DIR / EMBEDDING_MODEL
    if local.is_dir():
        return str(local)
    return EMBEDDING_MODEL
# Target chunk size in words; sections longer than this are split on
# paragraph boundaries with a small overlap to preserve context.
MAX_WORDS_PER_CHUNK = 400
CHUNK_OVERLAP_WORDS = 50


def _split_long_section(title: str, section: str, text: str) -> list[dict]:
    """Split an over-long section into overlapping word-window chunks."""
    words = text.split()
    chunks: list[dict] = []
    step = MAX_WORDS_PER_CHUNK - CHUNK_OVERLAP_WORDS
    for start in range(0, len(words), step):
        piece = " ".join(words[start : start + MAX_WORDS_PER_CHUNK])
        chunks.append({"title": title, "section": section, "text": piece})
        if start + MAX_WORDS_PER_CHUNK >= len(words):
            break
    return chunks


def chunk_runbook(path: Path) -> list[dict]:
    """Split one runbook markdown file into titled, sectioned chunks.

    Each chunk carries the runbook title and its ``##`` section heading so
    retrieved passages are self-describing even out of context.
    """
    raw = path.read_text(encoding="utf-8")
    title_match = re.search(r"^#\s+(.+)$", raw, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else path.stem

    # Split on "## " headings; text before the first heading becomes "Overview".
    parts = re.split(r"^##\s+(.+)$", raw, flags=re.MULTILINE)
    # parts = [preamble, heading1, body1, heading2, body2, ...]
    sections: list[tuple[str, str]] = []
    preamble = parts[0].strip()
    # Drop the "# title" line from the preamble to avoid duplication.
    preamble = re.sub(r"^#\s+.+$", "", preamble, flags=re.MULTILINE).strip()
    if preamble:
        sections.append(("Overview", preamble))
    for i in range(1, len(parts), 2):
        heading = parts[i].strip()
        body = parts[i + 1].strip() if i + 1 < len(parts) else ""
        if body:
            sections.append((heading, body))

    chunks: list[dict] = []
    for section, body in sections:
        if len(body.split()) > MAX_WORDS_PER_CHUNK:
            chunks.extend(_split_long_section(title, section, body))
        else:
            chunks.append({"title": title, "section": section, "text": body})
    for chunk in chunks:
        chunk["source"] = path.name
    return chunks


def build_index(chunks: list[dict], model_name: str | None = None):
    """Embed chunk texts and build a cosine-similarity FAISS index."""
    model_name = model_name or resolve_model_name()
    print(f"Loading embedding model '{model_name}' ...")
    model = SentenceTransformer(model_name)
    texts = [f"{c['title']} — {c['section']}\n{c['text']}" for c in chunks]
    print(f"Embedding {len(texts)} chunks ...")
    embeddings = model.encode(texts, show_progress_bar=True, normalize_embeddings=True)
    embeddings = np.asarray(embeddings, dtype=np.float32)

    # IndexFlatIP over L2-normalized vectors == cosine similarity.
    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(embeddings)
    return index


def main() -> None:
    runbook_files = sorted(
        p for p in RUNBOOKS_DIR.glob("*.md") if p.name != "_TEMPLATE.md"
    )
    if not runbook_files:
        raise SystemExit(f"No runbooks found in {RUNBOOKS_DIR}/")

    all_chunks: list[dict] = []
    for path in runbook_files:
        chunks = chunk_runbook(path)
        print(f"  {path.name}: {len(chunks)} chunks")
        all_chunks.extend(chunks)
    print(f"Total: {len(all_chunks)} chunks from {len(runbook_files)} runbooks")

    index = build_index(all_chunks)

    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(INDEX_FILE))
    METADATA_FILE.write_text(
        json.dumps(all_chunks, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"Index written to {INDEX_FILE} ({index.ntotal} vectors)")
    print(f"Metadata written to {METADATA_FILE}")


if __name__ == "__main__":
    main()
