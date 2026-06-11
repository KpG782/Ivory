# Ivory Hardening Plan

## Purpose

This plan turns the current audit into a practical hardening roadmap for the Ivory application.

The goal is not to redesign the whole system.

The goal is to make the current setup:

- more reliable
- easier to demo
- easier to test
- safer against state drift and weak validation

## Current status

The application is already in a workable state:

- backend endpoints exist and respond
- SSE chat flow works
- transactional quote flow works for the main auto path
- interruption and resume behavior exists
- frontend is cleaner and more backend-driven

What remains is the second-order reliability layer:

- broader test coverage
- stronger validation
- restart and adjust correctness
- retrieval consistency
- clearer operational setup

## Plan summary

The best order is:

1. harden backend behavior first
2. expand automated coverage
3. tighten retrieval and operational setup
4. only then polish the UI further

That keeps the system honest: the frontend should sit on top of reliable backend behavior, not compensate for it.

## Phase 1: Backend state integrity

### Goal

Make sure quote flow progression is deterministic and does not drift under interruptions, invalid input, restart, or adjustment.

### Tasks

- review all state transitions in:
  - [graph.py](/C:/Users/kpg78/Downloads/TENEXT/ivory-chatbot/backend/graph.py)
  - [router.py](/C:/Users/kpg78/Downloads/TENEXT/ivory-chatbot/backend/nodes/router.py)
  - [identify_product.py](/C:/Users/kpg78/Downloads/TENEXT/ivory-chatbot/backend/nodes/identify_product.py)
  - [collect_details.py](/C:/Users/kpg78/Downloads/TENEXT/ivory-chatbot/backend/nodes/collect_details.py)
  - [validate_quote.py](/C:/Users/kpg78/Downloads/TENEXT/ivory-chatbot/backend/nodes/validate_quote.py)
  - [confirm.py](/C:/Users/kpg78/Downloads/TENEXT/ivory-chatbot/backend/nodes/confirm.py)
- define and enforce simple invariants:
  - transactional mode should preserve `collected_data` unless reset or restart
  - invalid input should not advance `quote_step`
  - confirm should never succeed without a `quote_result`
  - `current_field` should always match the next missing required field during collect
- review `adjust` behavior and decide whether it should:
  - reopen from the first missing field
  - reopen from a chosen field
  - clear all collected data or preserve previous answers

### Success criteria

- no hidden step-skips
- no invalid state transitions
- no confirmation without a computed quote
- restart behavior is explicit and consistent

## Phase 2: Validation hardening

### Goal

Reduce bad data entering quote state.

### Tasks

- keep the current typed validation for:
  - ints
  - floats
  - bools
  - constrained enums
- add stronger handling for open-text fields:
  - `vehicle_make`
  - `vehicle_model`
  - `location`
- decide on lightweight guardrails for free-text fields, such as:
  - rejecting obviously empty or punctuation-only values
  - rejecting clearly off-topic answers during collection
  - normalizing common formatting issues
- verify validation in:
  - [collect_details.py](/C:/Users/kpg78/Downloads/TENEXT/ivory-chatbot/backend/nodes/collect_details.py)
  - [quote_calculator.py](/C:/Users/kpg78/Downloads/TENEXT/ivory-chatbot/backend/services/quote_calculator.py)

### Success criteria

- invalid numeric values are blocked
- invalid enum values are blocked
- blank answers are blocked
- obviously irrelevant text is less likely to be stored as a quote field

## Phase 3: Expand backend automated tests

### Goal

Prove behavior across all major paths, not just the happy-path auto flow.

### Tasks

- expand [test_backend_integration.py](/C:/Users/kpg78/Downloads/TENEXT/ivory-chatbot/tests/test_backend_integration.py) to cover:
  - home quote flow
  - life quote flow
  - invalid field handling per product
  - restart during identify
  - restart during collect
  - restart during confirm
  - adjust after quote generation
  - mid-flow interruption at multiple steps
  - early confirm rejection
  - cross-product switching
- add retrieval-focused tests with stable stubs where needed
- keep tests deterministic by stubbing LLM dependency when appropriate

### Suggested priority order

1. home happy path
2. life happy path
3. invalid input matrix
4. confirm / adjust / restart
5. multi-step interruption tests

### Success criteria

- happy paths exist for auto, home, and life
- invalid input behavior is explicitly tested
- restart and adjust logic are covered
- interruption/resume is covered beyond one single example

## Phase 4: Retrieval and knowledge quality

### Goal

Make RAG answers more consistently relevant and less dependent on luck in ranking.

### Tasks

- keep refining retrieval in:
  - [vectorstore.py](/C:/Users/kpg78/Downloads/TENEXT/ivory-chatbot/backend/services/vectorstore.py)
- test common user questions such as:
  - product overview
  - coverage differences
  - exclusions
  - deductibles
  - claim examples
  - life beneficiary questions
- continue improving the knowledge base with focused docs, not bulk filler
- keep the rebuild path documented in:
  - [KNOWLEDGE_BASE_SETUP.md](/C:/Users/kpg78/Downloads/TENEXT/ivory-chatbot/docs/guides/KNOWLEDGE_BASE_SETUP.md)

### Success criteria

- product overview questions return the correct products consistently
- common insurance questions map to relevant docs
- fallback answers are still useful if the LLM is unavailable

## Phase 5: Frontend/backend synchronization

### Goal

Ensure the UI reflects backend truth under resets, refreshes, interruptions, and confirmation gating.

### Tasks

- verify state handling in:
  - [useChat.ts](/C:/Users/kpg78/Downloads/TENEXT/ivory-chatbot/frontend/src/hooks/useChat.ts)
- test:
  - reset while streaming
  - stop generation while streaming
  - refresh browser mid-session
  - open `/quote-confirmation` before confirm state
  - session persistence after local reload
- keep confirmation unlock logic strictly backend-driven

### Success criteria

- frontend does not expose confirmation early
- reset and new session behave predictably
- browser reload does not create misleading quote state

## Phase 6: Operational setup and demo readiness

### Goal

Make local setup repeatable and demo-friendly.

### Tasks

- keep `.env` loading stable for backend
- document expected startup flow in:
  - [LOCAL_RUN_INSTRUCTIONS.md](/C:/Users/kpg78/Downloads/TENEXT/ivory-chatbot/docs/guides/LOCAL_RUN_INSTRUCTIONS.md)
- keep KB rebuild documented in:
  - [KNOWLEDGE_BASE_SETUP.md](/C:/Users/kpg78/Downloads/TENEXT/ivory-chatbot/docs/guides/KNOWLEDGE_BASE_SETUP.md)
- decide whether to add:
  - `HF_TOKEN` guidance for embedding downloads
  - a startup warmup step
  - clearer logs for retrieval fallback vs full model path

### Success criteria

- a new machine can be set up without guesswork
- the backend starts cleanly
- the frontend connects without env confusion
- the knowledge base can be rebuilt on demand

## Recommended implementation order

If doing this in a practical engineering sequence, use this order:

### Stage 1

- expand backend tests first
- add missing home and life flow coverage
- add invalid input coverage

### Stage 2

- harden state semantics
- tighten confirm / restart / adjust behavior

### Stage 3

- improve validation for weak free-text fields
- improve retrieval consistency

### Stage 4

- audit frontend synchronization under edge cases
- polish minor UX issues only after backend behavior is stable

## Recommended deliverables

By the end of hardening, the repo should ideally have:

- broader backend integration coverage
- cleaner validation behavior
- clear restart / adjust semantics
- stable retrieval for common questions
- concise local run documentation
- a reliable demo path for all three products

## Minimal completion checklist

The setup can be considered properly hardened for this project when all of the following are true:

- auto, home, and life quote paths all work end to end
- invalid inputs do not silently corrupt state
- mid-flow RAG interruption resumes correctly at multiple steps
- confirm, adjust, and restart are deterministic
- product overview and common policy questions retrieve sensible answers
- frontend never gets ahead of backend truth
- local setup and KB rebuild are documented and repeatable

## Bottom line

The right strategy is not to add more UI complexity right now.

The right strategy is:

- verify the backend thoroughly
- harden the workflow semantics
- improve retrieval quality
- keep the frontend narrow and honest

That is the fastest path to a submission or demo that feels reliable instead of merely functional.
