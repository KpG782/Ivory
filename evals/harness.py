"""Offline evaluation harness for the Ivory dental front-desk agent.

Why this exists: the 56 functional tests in ``tests/`` prove specific behaviors
with a stubbed LLM. This harness measures *aggregate quality* across many
realistic and adversarial inputs — the numbers you watch while iterating:

- routing accuracy       (router.decide — the deterministic control-flow brain)
- service detection      (detect_service — intake entry point)
- retrieval recall@k     (search_knowledge_base — does RAG find the right doc)
- RAG answer rubric      (the produced answer is on-topic and leak-free)
- conversation pass-rate (multi-turn guardrail / robustness scenarios)

Everything runs offline and deterministically. The LLM is intentionally absent,
so RAG answers exercise the formatted-fallback path; the retrieval and routing
evals are full-fidelity because the LLM never steers control flow.

Run:  backend/.venv/bin/python evals/run_evals.py
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

# Force offline, deterministic embeddings and no rate limiting.
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")

DATASETS = Path(__file__).resolve().parent / "datasets"


def load_jsonl(name: str) -> list[dict[str, Any]]:
    path = DATASETS / name
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


@dataclass
class SuiteResult:
    name: str
    total: int
    passed: int
    gate: float
    failures: list[str] = field(default_factory=list)

    @property
    def score(self) -> float:
        return self.passed / self.total if self.total else 1.0

    @property
    def ok(self) -> bool:
        return self.score >= self.gate


# --------------------------------------------------------------------------- #
# State fixtures for the routing eval (mirror real ChatState shapes).
# --------------------------------------------------------------------------- #
def _routing_state(kind: str) -> dict[str, Any]:
    base = {"mode": "conversational", "intake_step": "identify", "current_field": None,
            "service_type": None, "visit_estimate": None}
    if kind == "idle":
        return base
    if kind == "identify":
        return {**base, "mode": "transactional", "intake_step": "identify"}
    if kind == "collect_year":
        return {**base, "mode": "transactional", "intake_step": "collect",
                "current_field": "last_visit_year", "service_type": "cleaning"}
    if kind == "collect_name":
        return {**base, "mode": "transactional", "intake_step": "collect",
                "current_field": "patient_name", "service_type": "cleaning"}
    if kind == "confirm":
        return {**base, "mode": "transactional", "intake_step": "confirm",
                "service_type": "cleaning", "visit_estimate": {"summary": "x", "estimate_low": 1, "estimate_high": 2}}
    raise ValueError(f"unknown routing state {kind!r}")


def eval_routing() -> SuiteResult:
    from nodes.router import decide

    rows = load_jsonl("routing.jsonl")
    passed, failures = 0, []
    for row in rows:
        got = decide(_routing_state(row["state"]), row["message"])
        if got == row["expected"]:
            passed += 1
        else:
            failures.append(f"[{row['state']}] {row['message']!r} → {got} (want {row['expected']}) <{row.get('tag')}>")
    return SuiteResult("routing", len(rows), passed, gate=0.95, failures=failures)


def eval_service_detection() -> SuiteResult:
    from nodes.identify_service import detect_service

    rows = load_jsonl("service_detection.jsonl")
    passed, failures = 0, []
    for row in rows:
        got = detect_service(row["message"])
        if got == row["expected"]:
            passed += 1
        else:
            failures.append(f"{row['message']!r} → {got} (want {row['expected']}) <{row.get('tag')}>")
    return SuiteResult("service_detection", len(rows), passed, gate=0.90, failures=failures)


def eval_retrieval(top_k: int = 3) -> SuiteResult:
    from services.vectorstore import search_knowledge_base

    persist = tempfile.mkdtemp(prefix="ivory-eval-kb-")
    rows = load_jsonl("retrieval.jsonl")
    passed, failures = 0, []
    for row in rows:
        hits = search_knowledge_base(row["query"], top_k=top_k, persist_dir=persist)
        sources = [h.source for h in hits]
        if any(exp in sources for exp in row["expected_sources"]):
            passed += 1
        else:
            failures.append(f"{row['query']!r} → {sources} (want any of {row['expected_sources']}) <{row.get('tag')}>")
    return SuiteResult(f"retrieval@{top_k}", len(rows), passed, gate=0.85, failures=failures)


def eval_rag_answer() -> SuiteResult:
    from nodes.rag import rag_answer

    persist = tempfile.mkdtemp(prefix="ivory-eval-rag-")
    rows = load_jsonl("rag_answer.jsonl")
    passed, failures = 0, []
    for row in rows:
        state = {"messages": [{"role": "user", "content": row["query"]}], "mode": "conversational"}
        out = rag_answer(state, persist_dir=persist)
        answer = out["messages"][-1]["content"].lower()
        inc = row.get("must_include_any", [])
        exc = row.get("must_not_include", [])
        ok_inc = (not inc) or any(term.lower() in answer for term in inc)
        ok_exc = all(term.lower() not in answer for term in exc)
        if ok_inc and ok_exc:
            passed += 1
        else:
            reason = "missing-keyword" if not ok_inc else "leaked-forbidden"
            failures.append(f"{row['query']!r} → {reason}: {answer[:90]!r} <{row.get('tag')}>")
    return SuiteResult("rag_answer", len(rows), passed, gate=0.85, failures=failures)


def eval_conversation() -> SuiteResult:
    from fastapi.testclient import TestClient
    import main
    import nodes.rag as rag
    from services.vectorstore import RetrievedChunk

    # Stub the LLM (absent) but keep real retrieval so knowledge turns work.
    rag._build_client_or_none = lambda: None
    persist = tempfile.mkdtemp(prefix="ivory-eval-conv-")
    _orig_search = rag.search_knowledge_base
    rag.search_knowledge_base = lambda q, **k: _orig_search(q, **{**k, "persist_dir": persist})
    for var in ("AIRTABLE_API_KEY", "CALCOM_API_KEY", "RESEND_API_KEY"):
        os.environ.pop(var, None)

    client = TestClient(main.app)
    rows = load_jsonl("conversation.jsonl")
    passed, failures = 0, []

    def final_message(sse: str) -> tuple[str, dict[str, Any]]:
        msg, session = "", {}
        for block in sse.strip().split("\n\n"):
            data_lines = [ln.split(":", 1)[1].strip() for ln in block.splitlines() if ln.startswith("data:")]
            if not data_lines:
                continue
            payload = json.loads("\n".join(data_lines))
            if isinstance(payload, dict) and "message" in payload:
                msg = payload.get("message", "")
                session = payload.get("session", {}) or {}
        return msg, session

    for row in rows:
        sid = f"eval-{row['name']}"
        ok, why = True, ""
        for turn in row["turns"]:
            resp = client.post("/chat", json={"session_id": sid, "message": turn["say"]})
            if resp.status_code != 200:
                ok, why = False, f"HTTP {resp.status_code}"
                break
            msg, _ = final_message(resp.text)
            low = msg.lower()
            if "expect_contains" in turn and turn["expect_contains"].lower() not in low:
                ok, why = False, f"turn {turn['say']!r}: missing {turn['expect_contains']!r} in {msg[:70]!r}"
                break
            if "expect_not_contains" in turn and turn["expect_not_contains"].lower() in low:
                ok, why = False, f"turn {turn['say']!r}: leaked {turn['expect_not_contains']!r}"
                break
            if "expect_state" in turn:
                sess = main.SESSION_STORE.get(sid, {})
                es = turn["expect_state"]
                cd = sess.get("collected_data", {})
                checks = {
                    "service_type": lambda v: sess.get("service_type") == v,
                    "current_field": lambda v: sess.get("current_field") == v,
                    "collected_has": lambda v: v in cd,
                    "collected_empty": lambda v: (cd == {}) == v,
                    "has_estimate": lambda v: (sess.get("visit_estimate") is not None) == v,
                }
                for key, want in es.items():
                    if not checks[key](want):
                        ok, why = False, f"turn {turn['say']!r}: state {key}={want} not met (got {sess.get(key) if key in sess else cd})"
                        break
                if not ok:
                    break
        if ok:
            passed += 1
        else:
            failures.append(f"{row['name']} <{row.get('tag')}>: {why}")

    rag.search_knowledge_base = _orig_search
    return SuiteResult("conversation", len(rows), passed, gate=1.0, failures=failures)


ALL_SUITES: list[Callable[[], SuiteResult]] = [
    eval_routing,
    eval_service_detection,
    eval_retrieval,
    eval_rag_answer,
    eval_conversation,
]


def run_all(verbose: bool = True) -> list[SuiteResult]:
    results = []
    for suite in ALL_SUITES:
        res = suite()
        results.append(res)
        if verbose:
            _print_suite(res)
    return results


def _print_suite(res: SuiteResult) -> None:
    mark = "PASS" if res.ok else "FAIL"
    print(f"\n[{mark}] {res.name:18s} {res.passed}/{res.total} = {res.score:6.1%}  (gate {res.gate:.0%})")
    if res.failures:
        for f in res.failures:
            print(f"       ✗ {f}")
