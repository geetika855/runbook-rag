"""API tests for the runbook-RAG FastAPI service."""

import os

os.environ.setdefault("NO_PROXY", "localhost,127.0.0.1")
os.environ.setdefault("HF_HUB_OFFLINE", "1")

from fastapi.testclient import TestClient  # noqa: E402

from src.api import app  # noqa: E402


def get_client():
    return TestClient(app)


def test_health_reports_index_stats():
    with get_client() as client:
        r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["runbooks"] == 11
    assert body["chunks"] == 67


def test_runbooks_lists_all_files():
    with get_client() as client:
        r = client.get("/runbooks")
    assert r.status_code == 200
    files = {entry["file"] for entry in r.json()}
    assert "eks-no-ip-available.md" in files
    assert "pods-crashlooping-after-deploy.md" in files
    assert len(files) == 11


def test_ask_returns_grounded_answer():
    with get_client() as client:
        r = client.post(
            "/ask",
            json={"question": "EKS cluster ran out of IP addresses, pods stuck in ContainerCreating"},
        )
    assert r.status_code == 200
    body = r.json()
    assert "eks-no-ip-available.md" in body["sources"]
    assert "[source: eks-no-ip-available.md]" in body["answer"]
    assert all(m["source"] == "eks-no-ip-available.md" for m in body["matches"])
    assert all(0.0 <= m["score"] <= 1.0 for m in body["matches"])


def test_ask_refuses_out_of_scope():
    with get_client() as client:
        r = client.post("/ask", json={"question": "How do I bake sourdough bread?"})
    assert r.status_code == 200
    body = r.json()
    assert "don't have a runbook" in body["answer"]
    assert body["sources"] == []


def test_ask_validates_input():
    with get_client() as client:
        assert client.post("/ask", json={"question": "ab"}).status_code == 422
        assert client.post("/ask", json={"question": "x" * 2001}).status_code == 422
        assert client.post("/ask", json={"question": "valid?", "k": 99}).status_code == 422
