# Next Backend Update Plan

## Goal

This plan focuses only on the **remaining backend work** needed to make the current setup safer for a live demo.

It is intentionally narrower than the earlier hardening plan.

This is the plan for what should happen **next**.

## Priority 1: Fix free-text acceptance

### Problem

The backend still accepts nonsense text for some free-text fields.

Confirmed example:

```text
location = "i like dogs"
```

Current result:

- stored as a valid location
- state advances

### Required fix

Tighten `_clean_text_value()` in:

- [collect_details.py](/C:/Users/kpg78/Downloads/TENEXT/ivory-chatbot/backend/nodes/collect_details.py)

### Suggested rule changes

For `location` specifically:

- require at least 2 alphabetic tokens, or one token with a minimum length threshold
- reject phrases starting with conversational fillers like:
  - `i like`
  - `i want`
  - `my dog`
- reject very generic short sentences that do not look like place names

### Success criteria

This should fail:

```text
i like dogs
```

This should pass:

```text
Austin
Makati
Quezon City
San Jose
```

## Priority 2: Reject invalid numeric values immediately

### Problem

Home `estimated_value = 0` still advances the flow.

### Required fix

Add immediate reasonableness checks during collection for fields like:

- `estimated_value`
- potentially `coverage_amount`

That means rejecting the value **before** advancing to the next field.

### Best place to implement

Option A:

- add field-level validators to [collect_details.py](/C:/Users/kpg78/Downloads/TENEXT/ivory-chatbot/backend/nodes/collect_details.py)

Option B:

- extend field specs with `min_value`

Recommended:

- use field-spec-driven validation

Example:

```python
{"name": "estimated_value", "type": "float", "min_value": 1}
```

### Success criteria

This should fail immediately:

```text
0
```

Expected response style:

- positive number required
- same field re-prompted
- state does not advance

## Priority 3: Improve fallback RAG quality

### Problem

When OpenRouter is unavailable, the current fallback answer is functional but not demo-clean.

### Required fix

Add a more direct fallback answer path for a small set of common questions.

Best candidate questions:

- comprehensive coverage
- products offered
- deductibles
- flood coverage
- beneficiary basics

### Best place to implement

- [rag.py](/C:/Users/kpg78/Downloads/TENEXT/ivory-chatbot/backend/nodes/rag.py)

### Suggested approach

If:

- retrieval succeeds
- LLM is unavailable

Then:

- produce a short answer synthesized from the top chunk instead of concatenating long chunk fragments

### Success criteria

Fallback answer should read like:

```text
Comprehensive coverage generally includes non-collision damage such as theft, vandalism, fire, and weather-related damage.
```

not like a pasted chunk fragment dump.

## Priority 4: Clean up interruption response formatting

### Problem

The resume behavior is structurally correct, but the final visible answer can still feel crowded.

### Required fix

Make the interruption response render as:

1. concise answer
2. blank line
3. clear resume prompt

### Best place to inspect

- [graph.py](/C:/Users/kpg78/Downloads/TENEXT/ivory-chatbot/backend/graph.py)
- frontend streaming/rendering in:
  - [useChat.ts](/C:/Users/kpg78/Downloads/TENEXT/ivory-chatbot/frontend/src/hooks/useChat.ts)
  - [MessageBubble.tsx](/C:/Users/kpg78/Downloads/TENEXT/ivory-chatbot/frontend/src/components/MessageBubble.tsx)

### Success criteria

The interruption answer should be clearly readable and should not look duplicated or mashed together.

## Priority 5: Add tests for the remaining failures

### New backend tests to add

- `location` rejects nonsense phrases like `i like dogs`
- `estimated_value = 0` is rejected immediately and does not advance
- fallback RAG returns a clean answer for common questions when LLM is unavailable

### Why this matters

The current suite passes, but it does not yet enforce the two most visible remaining demo failures.

## Recommended execution order

Do the next backend pass in this exact order:

1. tighten `location` validation
2. add immediate `estimated_value` minimum validation
3. add tests for both
4. improve fallback RAG answer shaping
5. clean up interruption formatting if still needed

## Definition of done for the next pass

The next backend pass is complete when all of these are true:

- `i like dogs` does not advance the home quote flow
- `0` does not advance home property value collection
- common KB questions still produce a usable answer when OpenRouter is unavailable
- interruption answers and resume prompts look clean in the UI

## Bottom line

The backend no longer has major orchestration failures.

The next work is narrower:

- stricter field validation
- better immediate numeric checks
- better demo-safe fallback RAG output
- better interruption-response polish

That is the shortest path to making the backend feel reliably correct in a live demo.
