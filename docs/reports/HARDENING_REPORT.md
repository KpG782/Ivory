# Ivory Hardening Report

## Scope

This report summarizes the hardening work completed after the backend and frontend audit.

The main goal of this pass was to move the project from:

- mostly working on the happy path

to:

- better state integrity
- wider automated backend coverage
- cleaner confirmation behavior
- improved retrieval behavior for common insurance questions

## What was completed

### 1. Backend workflow hardening

The backend flow was tightened in these areas:

- explicit product switching mid-flow now resets the quote flow to the newly requested product instead of trying to store the new request as a field value
- confirmation `adjust` flow now reopens collection cleanly from the first field instead of falling into an inconsistent validate state
- free-text collection fields now reject obvious off-topic policy questions and malformed text input more aggressively
- string validation was strengthened for key fields such as:
  - `vehicle_make`
  - `vehicle_model`
  - `location`
- deprecated FastAPI startup event usage was replaced with lifespan startup initialization

Relevant files:

- [graph.py](/C:/Users/kpg78/Downloads/TENEXT/ivory-chatbot/backend/graph.py)
- [router.py](/C:/Users/kpg78/Downloads/TENEXT/ivory-chatbot/backend/nodes/router.py)
- [confirm.py](/C:/Users/kpg78/Downloads/TENEXT/ivory-chatbot/backend/nodes/confirm.py)
- [collect_details.py](/C:/Users/kpg78/Downloads/TENEXT/ivory-chatbot/backend/nodes/collect_details.py)
- [identify_product.py](/C:/Users/kpg78/Downloads/TENEXT/ivory-chatbot/backend/nodes/identify_product.py)
- [quote_calculator.py](/C:/Users/kpg78/Downloads/TENEXT/ivory-chatbot/backend/services/quote_calculator.py)
- [main.py](/C:/Users/kpg78/Downloads/TENEXT/ivory-chatbot/backend/main.py)

### 2. Retrieval hardening

The retrieval layer was improved so product-overview questions are less likely to rank weak or unrelated chunks above the actual overview docs.

This was done by adding reranking on top of base vector retrieval.

Relevant file:

- [vectorstore.py](/C:/Users/kpg78/Downloads/TENEXT/ivory-chatbot/backend/services/vectorstore.py)

### 3. Knowledge base expansion

The knowledge base was expanded with more useful policy content, including:

- coverage levels and deductibles
- home exclusions and add-ons
- life underwriting and beneficiaries
- discounts and eligibility
- scenario-based claim examples

Relevant folder:

- [knowledge_base](/C:/Users/kpg78/Downloads/TENEXT/ivory-chatbot/backend/knowledge_base)

### 4. Test coverage expansion

The backend integration suite was expanded significantly.

It now covers:

- health
- reset
- conversational SSE flow
- auto quote happy path
- home quote happy path
- life quote happy path
- mid-flow interruption and resume
- invalid numeric input
- invalid enum input
- off-topic string input rejection
- adjust behavior
- restart during confirm
- cross-product switching mid-flow

Relevant file:

- [test_backend_integration.py](/C:/Users/kpg78/Downloads/TENEXT/ivory-chatbot/tests/test_backend_integration.py)

## Verification results

### Backend

Executed:

```powershell
backend\.venv\Scripts\python.exe -m pytest -q
```

Result:

- `19 passed`

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

## State of the system now

The application is in a materially better place now.

### Stronger now

- deterministic product switching
- cleaner adjust behavior
- better input guardrails
- broader product-path coverage
- better retrieval ranking for common product questions
- cleaner backend startup path

### Still intentionally simple

- quote adjustment still restarts collection for the same product instead of supporting targeted field editing
- free-text semantic validation is still lightweight, not production-grade
- RAG still depends on environment quality for full LLM-backed answers
- the frontend remains intentionally narrow and does not attempt to simulate unsupported backend flows

## Remaining minor issues

These are not blockers for local use or demo flow, but they still exist:

### 1. Pytest cache warning

Pytest still emits a cache-permission warning in this workspace:

- `.pytest_cache` access issue

This does not block test execution.

### 2. Environment-dependent model behavior

For full RAG quality:

- the embedding model should be cached successfully
- OpenRouter should be reachable with a valid API key

If those are blocked, the app still works, but answers may fall back more often.

## Practical conclusion

This hardening pass did not try to turn Ivory into a production insurance platform.

It did make the current assessment setup much more reliable.

The repo now has:

- better orchestration behavior
- better test coverage
- better retrieval quality
- cleaner startup behavior
- a more honest frontend/backend contract

## Recommended next step

If you want one more engineering step after this, the best next move is:

- add one more focused test pass for browser/session edge cases on the frontend

But for backend flow integrity, this repo is now in a much stronger state than before.
