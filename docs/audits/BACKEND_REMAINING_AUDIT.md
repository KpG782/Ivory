# Backend Remaining Audit

## Purpose

This audit captures the **remaining backend issues** after the recent hardening pass.

It is based on:

- the current code
- the current automated test suite
- a direct local replay of the failing sequence:
  - `I want a quote`
  - `home`
  - `house`
  - `What does comprehensive coverage include?`
  - `i like dogs`
  - `0`

## Current status

The backend is in much better shape than before, but it is **not fully hardened yet**.

The good news:

- quote start works
- product routing works
- home flow progression works
- interruption resume works
- validation exists
- automated backend suite passes

The bad news:

- off-topic text is still accepted for some free-text fields
- `0` for home `estimated_value` still advances one step before final validation catches it
- RAG remains operationally unstable when the LLM is unavailable
- the interruption response formatting can still look messy in the UI

## What I verified directly

### 1. Quote flow progression

Confirmed working:

```text
I want a quote
home
house
```

Result:

- mode switched to transactional
- product became `home`
- flow advanced to `location`

This is good.

### 2. Mid-flow interruption and resume

Confirmed working structurally:

```text
What does comprehensive coverage include?
```

Result:

- quote state remained intact
- flow resumed to:
  - `Which city or location is the property in?`

So the orchestration is correct.

### 3. Off-topic handling

Confirmed still broken for free-text collection:

```text
i like dogs
```

Current result:

- accepted as `location`
- flow advanced to `estimated_value`

This is a real transactional integrity bug.

### 4. Numeric reasonableness for home property value

Confirmed still weak at field-entry time:

```text
0
```

Current result:

- accepted as `estimated_value`
- flow advanced to `year_built`

This means the value is only blocked later at final validation, not at the point of entry.

That is acceptable for some data, but for a field like home property value it is too permissive for a live demo.

### 5. RAG behavior

The backend did not return the earlier weak message:

- `I do not have enough knowledge-base context...`

Instead, under my local restricted environment, it returned a fallback answer built from retrieved knowledge-base chunks and then resumed the quote prompt.

So the current RAG issue is not “empty retrieval.”

It is more accurately:

- **environment-dependent answer quality**
- plus a less polished fallback response when the LLM call fails

## What is definitely still broken

### 1. Free-text field validation is too permissive

Problem fields:

- `location`
- potentially `vehicle_make`
- potentially `vehicle_model`

Current issue:

- nonsense text can still be stored if it is short and alphabetic

### 2. Immediate numeric reasonableness checks are incomplete

Problem field:

- `estimated_value`

Current issue:

- `0` passes field-entry coercion
- rejection only happens later during final quote validation

### 3. RAG fallback is still too rough for a demo

When OpenRouter is unavailable, the fallback answer:

- may be too verbose
- may not be user-friendly enough
- may not directly answer the question cleanly

### 4. Resume formatting still needs polish

The backend currently appends:

- RAG answer
- then a resume sentence

That is structurally correct, but can still look messy in the UI if tokenization or rendering compresses formatting badly.

## What is not actually broken

These things were re-checked and are not the current blocker:

- product routing
- product selection from `I want a quote` then `home`
- quote mode entry
- resume after interruption
- confirm/restart structure

So the current problem is **not orchestration shape**.

The current problem is **validation strictness and response polish**.

## Root-cause summary

### Off-topic input bug

Root cause:

- `_clean_text_value()` in [collect_details.py](/C:/Users/kpg78/Downloads/TENEXT/ivory-chatbot/backend/nodes/collect_details.py) blocks explicit policy-question phrases, but still allows generic nonsense text like `i like dogs`

### Property value bug

Root cause:

- `float` coercion accepts `0`
- reasonableness is deferred to final validation in [quote_calculator.py](/C:/Users/kpg78/Downloads/TENEXT/ivory-chatbot/backend/services/quote_calculator.py)
- this means the workflow advances before rejecting it

### RAG instability

Root cause:

- retrieval exists
- but final answer quality depends on:
  - OpenRouter availability
  - embedding/model environment
  - fallback answer formatting

## Severity

### Critical for live demo

- off-topic string acceptance
- `0` advancing home quote flow

### Important but less severe

- RAG fallback quality
- interruption response formatting polish

## Current backend recommendation

The backend is close, but it still needs one more targeted hardening pass before it is truly demo-safe.

If fixing only the highest-signal items, do these first:

1. reject nonsense free-text values like `i like dogs`
2. reject `estimated_value <= 0` immediately at collection time
3. improve fallback RAG answers for common KB questions
4. clean up interruption/resume response formatting
