#!/usr/bin/env bash
# Reproducible demo of runbook-rag: ingestion -> CLI Q&A -> API.
# Run from the repo root after `pip install -r requirements.txt`.
set -euo pipefail

echo "=== 1. Building the FAISS index from data/runbooks/ ==="
python -m src.ingest

echo
echo "=== 2. Incident question (CLI, extractive answer) ==="
python -m src.rag "pods are crashlooping after the latest deploy, what do I check first?"

echo
echo "=== 3. Another incident: EKS IP exhaustion ==="
python -m src.rag "EKS cluster ran out of IP addresses, pods stuck in ContainerCreating"

echo
echo "=== 4. Out-of-scope question is refused, not hallucinated ==="
python -m src.rag "how do I bake sourdough bread?"

echo
echo "=== 5. API ==="
uvicorn src.api:app --port 8000 &
API_PID=$!
trap 'kill $API_PID' EXIT
for i in $(seq 1 24); do
  if curl -sf http://localhost:8000/health >/dev/null; then break; fi
  sleep 5
done
curl -s http://localhost:8000/health; echo
curl -s -X POST http://localhost:8000/ask \
  -H 'Content-Type: application/json' \
  -d '{"question": "TLS certificate expiring soon, what is the renewal process?"}' | head -c 600; echo
kill $API_PID
trap - EXIT

echo
echo "Demo complete."
