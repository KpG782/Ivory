"""Proof-of-durability test for SqliteSaver checkpointer.

Verifies that session state (mode, messages, quote progress) survives
across two separate checkpointer + compiled-graph instances pointing at the
same SQLite file — simulating a process restart.

Hermetic: no LLM calls, no network, uses tmp_path for the db file.
SESSIONS_BACKEND is forced to "sqlite" for these tests so the real
SqliteSaver code path runs (overriding the conftest default of "memory").
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def test_session_state_survives_graph_rebuild(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """State written by graph-1 is readable by a fresh graph-2 on the same db."""
    db_file = str(tmp_path / "test_sessions.db")

    # Force sqlite backend and point it at the temp file.
    monkeypatch.setenv("SESSIONS_BACKEND", "sqlite")
    monkeypatch.setenv("SESSIONS_DB_PATH", db_file)

    # Stub out LLM / vectorstore so the test is offline.
    import nodes.rag as rag
    from services.vectorstore import RetrievedChunk

    monkeypatch.setattr(rag, "_build_client_or_none", lambda: None)
    monkeypatch.setattr(
        rag,
        "search_knowledge_base",
        lambda *a, **kw: [
            RetrievedChunk(
                id="kb-1",
                score=0.99,
                source="02_auto_insurance.md",
                title="Auto Insurance",
                content="Auto insurance covers your vehicle.",
                metadata={},
            )
        ],
    )

    import graph

    # ── Graph 1: send "I want a quote for auto insurance" ────────────────────
    graph.reset_all()
    try:
        graph.run_graph("durable-session", "I want a quote for auto insurance")

        # ── Simulate restart: rebuild with the same db file ──────────────────
        graph.reset_all()
        state = graph.get_session_state("durable-session")
        assert state is not None, "No checkpoint found — state was not persisted"

        # mode and quote progress must survive the rebuild
        assert state["mode"] == "transactional", f"mode lost, got: {state.get('mode')!r}"
        assert state["insurance_type"] == "auto", f"insurance_type lost, got: {state.get('insurance_type')!r}"
        assert len(state.get("messages", [])) >= 2, "messages not persisted"
    finally:
        # Restore memory backend so subsequent tests get a clean checkpointer.
        monkeypatch.setenv("SESSIONS_BACKEND", "memory")
        graph.reset_all()


def test_second_turn_uses_persisted_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A second turn picks up where the first left off (field collection continues)."""
    db_file = str(tmp_path / "test_sessions2.db")

    monkeypatch.setenv("SESSIONS_BACKEND", "sqlite")
    monkeypatch.setenv("SESSIONS_DB_PATH", db_file)

    import nodes.rag as rag
    from services.vectorstore import RetrievedChunk

    monkeypatch.setattr(rag, "_build_client_or_none", lambda: None)
    monkeypatch.setattr(
        rag,
        "search_knowledge_base",
        lambda *a, **kw: [
            RetrievedChunk(
                id="kb-1", score=0.99, source="x.md", title="X", content="X", metadata={}
            )
        ],
    )

    import graph

    graph.reset_all()
    try:
        # Turn 1 on graph-1
        graph.run_graph("multi-turn-session", "I want a quote for auto insurance")

        # Simulate restart before turn 2
        graph.reset_all()

        # Turn 2 on a fresh graph — vehicle year answer
        result2 = graph.run_graph("multi-turn-session", "2019")

        # The second turn should have stored vehicle_year
        assert result2["collected_data"].get("vehicle_year") == 2019, (
            f"vehicle_year not stored: {result2.get('collected_data')}"
        )
        assert result2["current_field"] == "vehicle_make"
    finally:
        monkeypatch.setenv("SESSIONS_BACKEND", "memory")
        graph.reset_all()
