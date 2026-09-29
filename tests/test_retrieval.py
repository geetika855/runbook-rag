"""Retrieval-quality tests: the right runbook must win for known questions,
and out-of-scope questions must be refused instead of hallucinated."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("HF_HUB_OFFLINE", "1")

from src.rag import extractive_answer, retrieve


def test_eks_ip_question_retrieves_eks_runbook():
    results = retrieve("EKS says no IP addresses available when scheduling pods", k=4)
    assert results, "no chunks retrieved"
    assert results[0]["source"] == "eks-no-ip-available.md"
    assert results[0]["score"] > 0.5


def test_crashloop_question_retrieves_crashloop_runbook():
    results = retrieve("pods stuck in CrashLoopBackOff after a deploy", k=4)
    assert results, "no chunks retrieved"
    assert results[0]["source"] == "pods-crashlooping-after-deploy.md"


def test_tls_question_retrieves_tls_runbook():
    results = retrieve("our TLS certificate expired, how do I renew it?", k=4)
    assert results, "no chunks retrieved"
    assert results[0]["source"] == "tls-certificate-expiry.md"


def test_out_of_scope_question_is_refused():
    answer = extractive_answer("how do I bake sourdough bread?")
    assert "don't have a runbook" in answer


def test_answer_cites_sources():
    answer = extractive_answer("queue backlog is growing, consumer lag increasing")
    assert "[source:" in answer
    assert "queue-backlog-consumer-lag.md" in answer
