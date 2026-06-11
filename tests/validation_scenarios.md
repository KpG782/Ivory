# Ivory Validation Scenarios

## Purpose

This document captures the expected validation coverage for the Ivory Insurance Assistant while the implementation is being built.

## Scenario Matrix

| ID | Scenario | Expected Result |
|---|---|---|
| V1 | Ask a general insurance question | Response is grounded in the knowledge base |
| V2 | Start an auto quote | Assistant enters the transactional flow |
| V3 | Start a home quote | Assistant collects home-specific fields |
| V4 | Start a life quote | Assistant collects life-specific fields |
| V5 | Ask a question mid-quote | Assistant answers and resumes the quote flow |
| V6 | Submit invalid field data | Only the invalid field is re-prompted |
| V7 | Complete a quote and restart | A new quote can start in the same session |
| V8 | Reset a session | Only the targeted session state is cleared |
| V9 | Retrieval returns nothing | Assistant degrades gracefully |
| V10 | LLM call fails | User receives a controlled error response |
| V11 | SSE stream is consumed by UI | Tokens stream before final completion |

## Validation Notes

- These scenarios should be implemented as automated tests once the backend exists.
- Until then, they serve as the regression checklist for manual verification.
