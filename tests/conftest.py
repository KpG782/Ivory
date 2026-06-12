"""Global pytest configuration.

Sets SESSIONS_BACKEND=memory before any module is imported so the
existing test suite stays hermetic — no SQLite file is created, and
reset_all() replaces the MemorySaver instance (effectively clearing
all sessions) exactly as before.

Tests that explicitly want the sqlite backend override this with
monkeypatch.setenv("SESSIONS_BACKEND", "sqlite").
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("SESSIONS_BACKEND", "memory")

ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


# ── Shared SSE helpers ────────────────────────────────────────────────────────

def _parse_sse_body(body: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for raw_event in body.strip().split("\n\n"):
        if not raw_event.strip():
            continue
        event_name = "message"
        data_lines: list[str] = []
        for line in raw_event.splitlines():
            if line.startswith("event:"):
                event_name = line.split(":", 1)[1].strip()
            elif line.startswith("data:"):
                data_lines.append(line.split(":", 1)[1].strip())
        payload = "\n".join(data_lines)
        events.append(
            {
                "event": event_name,
                "data": json.loads(payload) if payload else None,
            }
        )
    return events


def _post_chat(client: TestClient, session_id: str, message: str) -> list[dict[str, Any]]:
    response = client.post("/chat", json={"session_id": session_id, "message": message})
    assert response.status_code == 200
    return _parse_sse_body(response.text)


# ── Shared client fixture ─────────────────────────────────────────────────────

@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    import main
    import nodes.rag as rag
    from services.vectorstore import RetrievedChunk

    # Disable rate limiting so the test suite does not hit per-IP limits.
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "false")

    main.SESSION_STORE.clear()

    # Routing is deterministic (no LLM), so there is no classifier to stub. We
    # only stub the RAG LLM client + retrieval so tests are hermetic/offline.
    monkeypatch.setattr(rag, "_build_client_or_none", lambda: None)
    monkeypatch.setattr(
        rag,
        "search_knowledge_base",
        lambda *args, **kwargs: [
            RetrievedChunk(
                id="kb-1",
                score=0.99,
                source="02_auto_insurance.md",
                title="Auto Insurance",
                content=(
                    "Comprehensive coverage typically includes non-collision losses such as "
                    "theft, vandalism, fire, weather damage, and falling objects."
                ),
                metadata={"source": "02_auto_insurance.md", "title": "Auto Insurance"},
            )
        ],
    )

    with TestClient(main.app) as test_client:
        yield test_client

    main.SESSION_STORE.clear()
