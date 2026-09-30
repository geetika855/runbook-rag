# CPU-only image for the runbook-RAG API.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Bake the FAISS index into the image so the service starts with zero setup.
RUN python -m src.ingest

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s \
  CMD python -c "import urllib.request, json; \
    h = json.load(urllib.request.urlopen('http://localhost:8000/health')); \
    assert h['status'] == 'ok'" || exit 1

CMD ["uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "8000"]
