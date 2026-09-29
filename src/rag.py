"""RAG question answering over the runbook index.

Usage:
    python -m src.rag "your incident question here"
"""

import sys


def answer(question: str) -> str:
    # Day 3: implement retrieval + LLM answer chain here.
    raise NotImplementedError("Day 3: build the RAG chain")


def main() -> None:
    if len(sys.argv) < 2:
        print('Usage: python -m src.rag "your incident question"')
        raise SystemExit(1)
    print(answer(" ".join(sys.argv[1:])))


if __name__ == "__main__":
    main()
