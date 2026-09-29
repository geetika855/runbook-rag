"""Runbook ingestion: chunk markdown runbooks, embed, and persist a FAISS index.

Usage:
    python -m src.ingest
"""

RUNBOOKS_DIR = "data/runbooks"
INDEX_DIR = "data/index"


def main() -> None:
    # Day 2: implement chunking + embeddings + FAISS persistence here.
    raise NotImplementedError("Day 2: build the ingestion pipeline")


if __name__ == "__main__":
    main()
