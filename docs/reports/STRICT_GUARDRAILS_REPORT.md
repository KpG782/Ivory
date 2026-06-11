# Strict Guardrails Report

## Scope

This report summarizes the final backend strictness pass focused on:

- stronger field guardrails
- immediate invalid-value rejection
- cleaner fallback RAG answers
- updated automated coverage for those behaviors

## What was changed

### 1. Immediate numeric guardrails

The collection layer now supports immediate minimum-value checks through field specs.

This was added in:

- [collect_details.py](/C:/Users/kpg78/Downloads/TENEXT/ivory-chatbot/backend/nodes/collect_details.py)

Relevant fields now have stricter entry-time rules:

- `accidents_last_5yr` must be `>= 0`
- `estimated_value` must be `>= 1`
- `coverage_amount` must be `>= 1`

This means invalid values are now rejected **before** the workflow advances.

### 2. Stronger free-text guardrails

String fields now have more structure-aware validation.

Examples:

- `vehicle_make` and `vehicle_model` now require a minimum text length
- `location` now rejects more obviously invalid entries

The `location` field specifically now blocks things like:

- conversational phrases
- pet/random text such as `i like dogs`
- overly long multi-token filler text

### 3. Cleaner fallback RAG behavior

When the LLM is unavailable, fallback answers are now more direct and demo-safe.

Instead of dumping chunk fragments, the backend now tries to produce short direct answers for common questions such as:

- comprehensive coverage
- products offered
- deductibles
- flood coverage
- beneficiaries

This was updated in:

- [rag.py](/C:/Users/kpg78/Downloads/TENEXT/ivory-chatbot/backend/nodes/rag.py)

### 4. Automated test coverage was expanded again

The backend suite now explicitly covers the remaining visible failure cases:

- nonsense location input rejection
- policy-question rejection inside string-field collection
- zero property value rejection at entry time
- clean fallback RAG answer without the LLM

Relevant file:

- [test_backend_integration.py](/C:/Users/kpg78/Downloads/TENEXT/ivory-chatbot/tests/test_backend_integration.py)

## What is now verified

### Quote-flow strictness

Verified:

- `i like dogs` no longer advances the home quote flow as a location
- `0` no longer advances home property value collection
- negative accident count no longer advances auto collection
- invalid boolean input no longer advances life collection
- invalid enum input no longer advances collection

### RAG fallback quality

Verified:

- `What does comprehensive coverage include?`
  now returns a direct fallback answer when the LLM is unavailable
- the fallback no longer uses the older verbose `based on the knowledge base ...` fragment style

### End-to-end integrity

The previously working flows remain intact:

- quote start
- product selection
- auto quote happy path
- home quote happy path
- life quote happy path
- mid-flow interruption and resume
- adjust
- restart
- product switching

## Verification results

### Backend

Executed:

```powershell
backend\.venv\Scripts\python.exe -m pytest -q
```

Result:

- `28 passed`

### Frontend

Executed:

```powershell
cd frontend
npm run typecheck
npm run build
```

Results:

- typecheck passed
- build passed

## Practical impact

This pass fixed the most visible remaining demo-breakers:

- invalid location text no longer silently pollutes state
- zero-value home property amounts no longer move the flow forward
- fallback RAG answers are cleaner when OpenRouter is unavailable

That makes the backend materially stricter and safer for live demo use.

## Remaining non-blocker

The only recurring issue still visible in verification is:

- pytest cache permission warning in this workspace

That does not block tests or runtime behavior.

## Final state

At this point the backend is no longer mainly limited by orchestration correctness.

The major flow bugs, validation leaks, and fallback-answer rough edges addressed in this pass are now covered by tests and working as intended.
