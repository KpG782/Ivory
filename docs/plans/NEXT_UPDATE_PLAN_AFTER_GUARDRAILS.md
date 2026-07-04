> **Historical (insurance vertical).** This plan predates the dental conversion (see docs/specs/DENTAL_VERTICAL_SPEC.md). Kept for history; file paths and examples reference the retired insurance vertical.

# Next Update Plan After Guardrails

## Purpose

This plan covers what still makes sense to improve after the backend guardrails were tightened.

The major workflow-integrity bug is no longer the top priority.

The next steps are smaller and more focused.

## Priority 1: Browser-level validation checks

The backend behavior is now stronger than the browser-level verification.

Next useful checks:

- confirm that invalid field messages display clearly in the UI
- confirm that the same pending field remains visible after rejection
- confirm that session snapshot stays aligned during invalid-entry loops

Best targets:

- invalid location
- invalid property value
- invalid year built
- interruption plus resume

## Priority 2: Cleanup of message presentation

The backend responses are now correct, but some rejection messages still read as:

- validation error
- then prompt repeated inline

That is fine functionally, but could be polished for demo readability.

Possible improvement:

- format validation replies as:
  - one short error sentence
  - one clear re-prompt sentence

## Priority 3: Optional stronger realism heuristics

Current guardrails are now much better, but still lightweight.

Optional next improvements:

- slightly smarter location heuristics
- more realistic home-value thresholds by market band
- stronger vehicle make/model heuristics if needed

These are optional, not urgent.

## Priority 4: Retrieval polish

RAG fallback is now cleaner, but it still depends on environment quality for the best answers.

Good next steps:

- test a small manual list of top insurance questions
- verify answer quality with your real OpenRouter-enabled environment
- tune fallback wording only if any common question still looks weak

## Priority 5: Demo runbook refinement

Now that the backend is stricter, the best next practical document would be:

- a final demo script
- expected visible outputs
- a short “if this fails, check this” troubleshooting section

## Bottom line

The next work should no longer be large backend refactors.

The next work should be:

- UI verification
- response polish
- final demo preparedness
