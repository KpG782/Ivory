# Ivory — Evaluation Harness

The functional suite in [`tests/`](../tests) proves *specific* behaviors with a
stubbed LLM. This harness measures **aggregate quality** across many realistic
and adversarial inputs — the numbers you watch while iterating on prompts and
routing. It is how we answer "does the agent actually work right now?" with a
score instead of a vibe.

Everything runs **offline and deterministically**. The LLM is intentionally
absent, so RAG answers exercise the formatted-fallback path; routing, service
detection, and retrieval are full-fidelity because the LLM never steers control
flow in this architecture.

## Run it

```bash
backend/.venv/bin/python evals/run_evals.py          # scorecard + exit code
backend/.venv/bin/python -m pytest evals/test_eval_gates.py -q   # as a CI gate
```

## Suites

| Suite | What it measures | Gate | Source |
|-------|------------------|------|--------|
| `routing` | `router.decide` picks the right route across states & phrasings | 95% | `datasets/routing.jsonl` |
| `service_detection` | `detect_service` maps utterances to cleaning/emergency/cosmetic | 90% | `datasets/service_detection.jsonl` |
| `retrieval@3` | `search_knowledge_base` returns the owning doc in the top 3 | 85% | `datasets/retrieval.jsonl` |
| `rag_answer` | the produced answer is on-topic and free of preamble leakage | 85% | `datasets/rag_answer.jsonl` |
| `conversation` | multi-turn guardrail / robustness scenarios end-to-end | 100% | `datasets/conversation.jsonl` |

Datasets are JSONL — one labeled case per line — so adding coverage is a
one-line append. Gates are set per suite in `harness.py`.

## The loop-engineering method (how these were tuned)

The harness exists to drive an eval → diagnose → fix → re-run loop. The current
numbers came from exactly that:

1. **Baseline** exposed three real quality gaps the 56 unit tests missed:
   - retrieval missed the emergency / clinic-hours / pediatric docs under the
     offline hash-embedding fallback (85%);
   - the fallback had no direct answer for "what happens during a cleaning" (83%);
   - a bare **"I have a dental emergency"** opener was answered as a knowledge
     question instead of triaging the patient into an emergency intake.
2. **Fixes** (each surgical, no invariant weakened):
   - a deterministic topic-affinity reranker in `services/vectorstore.py`;
   - a curated cleaning fallback answer in `nodes/rag.py`;
   - a router rule that triages emergency declarations and service-seeking
     openers into intake (`nodes/router.py`), locked with new routing cases.
3. **Re-run** → 100% across 104 cases, with the 56 functional tests still green.

Each fix was paired with a new labeled case so the improvement can't silently
regress. That pairing — never fix a failure without adding the case that proves
it — is the whole method.

## What is *not* covered offline

Live LLM answer quality (fluency, faithfulness, tone) needs an
`OPENROUTER_API_KEY`. The `rag_answer` suite is written so it also runs against a
real model: point the harness at a configured environment and the same rubric
grades live generations. The `RAG_SYSTEM_PROMPT` in `nodes/rag.py` is hardened
for grounding, no-medical-advice, and instruction-integrity (prompt-injection
resistance); those properties are best verified against a live model.
