# Ivory Validation Scenarios

## Purpose

This document captures the validation coverage for the Ivory Dental Front Desk assistant. Every scenario below is implemented as an automated test in `test_backend_integration.py`; the matrix doubles as the regression checklist for manual verification in the browser.

## Scenario Matrix

| ID | Scenario | Expected Result |
|---|---|---|
| V1 | Ask a general dental question | Response is grounded in the knowledge base |
| V2 | Start a cleaning intake | Assistant enters the transactional flow and asks for the patient name |
| V3 | Start an emergency intake | Assistant collects emergency-specific fields (phone, issue, pain level) |
| V4 | Start a cosmetic intake | Assistant collects cosmetic-specific fields (treatment, budget, timeline) |
| V5 | Ask a question mid-intake | Assistant answers and re-asks the exact pending field |
| V6 | Submit invalid field data | Only the invalid field is re-prompted; the flow never advances |
| V7 | Complete an intake and restart | A new intake can start in the same session |
| V8 | Reset a session | Only the targeted session state is cleared |
| V9 | Retrieval returns nothing | Assistant degrades gracefully |
| V10 | LLM call fails or is unconfigured | User receives a clean deterministic fallback answer |
| V11 | SSE stream is consumed by UI | Tokens stream before final completion |
| V12 | Accept an estimate (unconfigured) | "Front desk actions" block shows three dry-run lines; no network is touched |
| V13 | Accept an estimate (configured) | Airtable lead, Cal.com booking, and Resend email payloads are posted |
| V14 | One integration fails on accept | That line reports an error; the other integrations and the accept turn still succeed |
| V15 | Emergency accept (phone contact only) | Email confirmation is skipped, never errored |

## Validation Notes

- Estimates are deterministic: identical inputs always produce identical `visit_estimate` payloads.
- Bare field replies (e.g. `2024`) stay in the transactional branch and are never re-routed to RAG.
- Compact multi-field replies (`Maria Santos, maria@example.com, 2024, insured, morning`) fill several fields in one turn.
- The free-text guard rejects conversational fillers (`i like dogs` is never accepted as a patient name).
- Integrations fire only on an explicit `accept` — never earlier.
