# Ivory Application Audit

## Purpose

This audit summarizes the current state of the Ivory application after the recent orchestration, retrieval, and UI cleanup work.

It focuses on:

- what is clearly working now
- what has been improved
- what still needs to be checked or hardened
- what should be tested before treating the system as reliable

## Current verdict

The application is in a much better state than before.

The main first-order orchestration bugs are largely addressed:

- product selection is more deterministic
- mid-flow RAG interruption can resume quote collection
- constrained fields reject obvious garbage values
- the UI is cleaner and more aligned to backend state

But the system should still be treated as **partially hardened, not fully hardened**.

The main remaining risks are in:

- second-order validation quality
- per-step state integrity
- restart and adjustment semantics
- retrieval consistency
- UI/backend synchronization under edge cases

## What is clearly working now

### 1. Basic backend contract

Confirmed endpoints:

- `GET /health`
- `POST /chat`
- `POST /reset`

The backend streams SSE and returns a session snapshot in `message_complete`.

Relevant files:

- [main.py](/C:/Users/kpg78/Downloads/TENEXT/ivory-chatbot/backend/main.py)
- [graph.py](/C:/Users/kpg78/Downloads/TENEXT/ivory-chatbot/backend/graph.py)

### 2. Graph orchestration shape

The current LangGraph-style orchestration logic is straightforward and understandable:

- route by intent
- answer RAG questions
- identify product
- collect fields
- validate and quote
- confirm, adjust, or restart

Relevant files:

- [graph.py](/C:/Users/kpg78/Downloads/TENEXT/ivory-chatbot/backend/graph.py)
- [router.py](/C:/Users/kpg78/Downloads/TENEXT/ivory-chatbot/backend/nodes/router.py)
- [identify_product.py](/C:/Users/kpg78/Downloads/TENEXT/ivory-chatbot/backend/nodes/identify_product.py)
- [collect_details.py](/C:/Users/kpg78/Downloads/TENEXT/ivory-chatbot/backend/nodes/collect_details.py)
- [validate_quote.py](/C:/Users/kpg78/Downloads/TENEXT/ivory-chatbot/backend/nodes/validate_quote.py)
- [confirm.py](/C:/Users/kpg78/Downloads/TENEXT/ivory-chatbot/backend/nodes/confirm.py)

### 3. Mid-flow question handling

This is one of the most important assignment requirements, and the current graph does support it:

- if the user asks a question during transactional mode
- the message is routed to RAG
- the quote step is preserved
- the assistant appends a resume prompt for the pending quote field

This is implemented directly in:

- [graph.py](/C:/Users/kpg78/Downloads/TENEXT/ivory-chatbot/backend/graph.py)

### 4. Deterministic field ordering

Each product has an explicit ordered field schema in:

- [collect_details.py](/C:/Users/kpg78/Downloads/TENEXT/ivory-chatbot/backend/nodes/collect_details.py)

That is a real improvement because the quote flow no longer depends on free-form inference for every step.

### 5. Quote computation is deterministic

The quote math is not LLM-driven.

That is correct for this assignment.

Relevant file:

- [quote_calculator.py](/C:/Users/kpg78/Downloads/TENEXT/ivory-chatbot/backend/services/quote_calculator.py)

### 6. Frontend is now backend-driven in the important places

The frontend reads backend session state and uses it to decide whether confirmation is available.

Relevant files:

- [useChat.ts](/C:/Users/kpg78/Downloads/TENEXT/ivory-chatbot/frontend/src/hooks/useChat.ts)
- [App.tsx](/C:/Users/kpg78/Downloads/TENEXT/ivory-chatbot/frontend/src/App.tsx)
- [QuoteConfirmationPage.tsx](/C:/Users/kpg78/Downloads/TENEXT/ivory-chatbot/frontend/src/QuoteConfirmationPage.tsx)

## What has been improved well

### 1. Product routing no longer relies purely on the LLM

That was the right fix.

Quote mode should not depend on a small model correctly guessing bare product inputs like `home` or `life`.

### 2. Resume-after-RAG behavior is explicit

That directly supports the assignment requirement for graceful transitions.

### 3. Constrained-field validation exists at input time

Examples:

- home `property_type`
- life `health_status`
- life `term_years`
- all `coverage_level` fields

This prevents many obvious bad inputs from entering quote state.

### 4. Retrieval quality was improved recently

The retrieval layer now reranks results so obvious product-overview questions are less likely to surface weak chunks first.

Relevant file:

- [vectorstore.py](/C:/Users/kpg78/Downloads/TENEXT/ivory-chatbot/backend/services/vectorstore.py)

## What still looks incomplete or risky

These are the main things that still need careful checking.

### 1. Validation is stronger for typed fields than for semantic free-text fields

Current validation is good for:

- ints
- floats
- bools
- constrained enums

But it is still relatively weak for free-text fields such as:

- `vehicle_make`
- `vehicle_model`
- `location`

Right now, a user can still enter many irrelevant strings and they may be accepted because they are valid strings.

That may be acceptable for a demo, but it is still a reliability gap.

### 2. Only some products and paths are tested

The current integration tests cover:

- `/health`
- `/reset`
- one conversational question
- auto quote flow
- one mid-flow interruption path

That is useful, but not enough to claim broad reliability.

Still missing strong automated checks for:

- home quote flow
- life quote flow
- invalid field handling for each product
- restart behavior
- adjust behavior
- confirm misuse
- cross-product switching

Relevant file:

- [test_backend_integration.py](/C:/Users/kpg78/Downloads/TENEXT/ivory-chatbot/tests/test_backend_integration.py)

### 3. Confirmation semantics are functional but simple

The confirm node handles:

- `accept`
- `adjust`
- `restart`

But the behavior is still basic.

Examples:

- `adjust` clears the quote and reopens collection, but it does not let the user target a specific field explicitly
- `accept` switches mode back to conversational but leaves previous product context in memory
- confirm logic depends on lightweight phrase matching in the router

Relevant files:

- [confirm.py](/C:/Users/kpg78/Downloads/TENEXT/ivory-chatbot/backend/nodes/confirm.py)
- [router.py](/C:/Users/kpg78/Downloads/TENEXT/ivory-chatbot/backend/nodes/router.py)

### 4. UI state is mostly aligned, but some paths still rely on local optimistic state

The frontend stores:

- session id
- last session snapshot
- last quote result

That is reasonable for UX, but it means the client can temporarily display assumed state after local reset or new-session creation before the backend confirms anything.

This is not catastrophic, but it is worth knowing.

Relevant file:

- [useChat.ts](/C:/Users/kpg78/Downloads/TENEXT/ivory-chatbot/frontend/src/hooks/useChat.ts)

### 5. Retrieval still depends on environment quality

Two practical issues remain:

- OpenRouter failures push the app into fallback answer mode
- sentence-transformer model loading may try to reach Hugging Face and emit warnings if the model is not cached

So retrieval is improved, but not yet fully robust operationally.

### 6. RAG source visibility is minimal

The backend defines a `RagAnswer` shape with sources, but the current state path does not expose rich source metadata in the frontend.

That is not required for the assignment, but it limits debuggability.

## Actual code-level observations

### Strengths

- field schemas are explicit per product
- validation and quote calculation are separated
- graph transitions are readable
- confirmation gating exists in the UI
- the chat flow can resume after a product question interruption

### Weak points

- no deep semantic validation for open text fields
- no comprehensive test matrix yet
- retrieval still has fallback dependency paths
- no explicit audit log or invariant checks for state corruption
- no targeted field-edit flow during quote adjustment

## Recommended next checks

These are the highest-value checks to run next.

### Priority 1: field-by-field validation audit

For each product, test:

- valid input advances exactly one step
- empty input is rejected
- invalid numeric input is rejected
- invalid enum input is rejected
- off-topic text does not silently pollute the field

### Priority 2: resume behavior at every stage

Test interruption and resumption at:

- identify step
- first collection step
- middle collection step
- just before validation
- confirm step

### Priority 3: restart and adjustment semantics

Test:

- restart during identify
- restart during collect
- restart during confirm
- adjust after quote generation
- switching from auto to home mid-flow

### Priority 4: retrieval checks

Test at least:

- product overview questions
- exclusions questions
- deductible questions
- claims examples
- beneficiary / underwriting questions

### Priority 5: UI/backend synchronization

Check:

- reset while sending
- stop generation during stream
- refresh browser mid-session
- open confirmation page without valid backend confirm state

## Recommended test matrix

### A. Product selection

- `I want a quote`
- `auto`
- `home`
- `life`

Expected:

- product is identified correctly
- first required field is asked immediately

### B. Field validation

For each product:

- valid value advances
- invalid value re-prompts
- blank input re-prompts
- unrelated text does not corrupt state

### C. Mid-flow interruption

At each stage:

- ask a product or policy question
- verify answer is returned
- verify exact original quote step resumes

### D. Restart behavior

- restart same product
- switch product mid-flow
- reset session fully

### E. Confirmation

- cannot confirm early
- can confirm after quote exists
- can adjust and re-enter collection cleanly

### F. Retrieval

- product overview
- exclusions
- claims process
- coverage level differences
- deductibles

## Suggested engineering priorities

### 1. Expand automated backend tests

The single highest-leverage next step is more backend integration coverage.

Best targets:

- home flow
- life flow
- invalid inputs across all products
- confirm / adjust / restart flows
- cross-product switching

### 2. Harden semantic validation for free-text fields

Not everything needs to be strict, but some guardrails would help for:

- obviously nonsense text
- accidental off-topic answers
- malformed location data

### 3. Add a minimal state-invariant checklist

Examples:

- transactional mode should never lose `collected_data` after RAG interruption
- invalid field input should never advance `quote_step`
- confirm should never succeed without `quote_result`

### 4. Keep the UI narrow and backend-led

This is already moving in the right direction.

Do not reintroduce decorative flows that are not backed by actual backend state.

## Bottom line

The application is no longer in the “obvious flow break” stage.

The major first-order fixes are in place.

But it should still be described as:

> Functionally coherent and demoable, with the main routing and interruption behaviors working, but still needing deeper validation, broader automated coverage, and stronger state-hardening across all products.

That is the honest and technically accurate position for the current repo.
