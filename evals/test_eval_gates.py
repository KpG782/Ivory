"""Pytest gate for the eval harness.

Runs the offline eval suites and asserts each one meets its quality gate, so a
regression in routing / retrieval / RAG-answer / conversation quality fails CI
just like a broken unit test would.

This lives under ``evals/`` (not ``tests/``) so it is opt-in and does not change
the functional-suite count. Run it explicitly:

    backend/.venv/bin/python -m pytest evals/test_eval_gates.py -q
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from harness import (  # noqa: E402
    eval_conversation,
    eval_rag_answer,
    eval_retrieval,
    eval_routing,
    eval_service_detection,
)

SUITES = [
    eval_routing,
    eval_service_detection,
    eval_retrieval,
    eval_rag_answer,
    eval_conversation,
]


@pytest.mark.parametrize("suite", SUITES, ids=lambda s: s.__name__)
def test_eval_suite_meets_gate(suite) -> None:
    res = suite()
    assert res.ok, (
        f"{res.name}: {res.score:.1%} < gate {res.gate:.0%}\n"
        + "\n".join(f"  ✗ {f}" for f in res.failures)
    )
