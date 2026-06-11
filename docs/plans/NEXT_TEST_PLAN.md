# Next Test Plan

## Purpose

This plan updates the manual and automated test priorities based on the current state of the Ivory repo.

It is meant to answer:

- what is already covered
- what should still be manually checked
- what should be the next automation target

## Current baseline

Already covered automatically in backend tests:

- conversational RAG baseline
- quote start
- product selection
- auto quote happy path
- home quote happy path
- life quote happy path
- mid-flow interruption and resume
- invalid numeric values
- invalid enum values
- invalid boolean values
- future-year validation
- negative accident validation
- adjust behavior
- restart behavior
- product switching mid-flow

Current result:

- `25 passed`

## Updated minimal manual test plan

Run these in fresh sessions unless noted.

### Test 1: Conversational RAG baseline

Input:

`What does comprehensive coverage include?`

Expected:

- grounded answer about non-collision damage
- no quote flow starts
- session remains conversational

### Test 2: Start quote flow

Input:

`I want a quote`

Expected:

- transactional mode starts
- assistant asks for `auto`, `home`, or `life`
- no RAG-style explanatory answer appears

### Test 3: Product selection advances

Inputs:

```text
I want a quote
home
```

Expected:

- insurance type becomes `home`
- assistant asks the first real home field
- no generic home-policy explanation appears

### Test 4: Mid-flow knowledge interruption and resume

Inputs:

```text
I want a quote
home
house
What does comprehensive coverage include?
```

Expected:

- assistant answers the knowledge question
- quote state remains intact
- assistant resumes the exact pending field afterward

### Test 5: Off-topic input during quote

Inputs:

```text
I want a quote
home
house
i like dogs
```

Expected:

- input is rejected or redirected
- same field is re-prompted
- state does not advance

### Test 6: Invalid reasonableness check

Inputs:

```text
I want a quote
auto
2035
Toyota
Camry
35
0
standard
```

Expected:

- year is rejected before quote generation
- assistant returns to `vehicle_year`
- no quote is generated

### Test 7: Complete one full quote

Pick one product and complete it fully.

Expected:

- clean step progression
- quote generated
- confirm, adjust, or restart path works

### Test 8: Reset or restart

Expected:

- state clears
- no stale product or pending field leaks into the next run

## Best low-credit live demo set

If you want the highest-signal low-token demo, do this:

1. `What does comprehensive coverage include?`
2. `I want a quote`
3. `home`
4. valid first field answer
5. ask a product question mid-flow
6. send one invalid answer
7. continue with valid answer
8. finish the quote

This still demonstrates:

- RAG
- quote start
- product routing
- interruption handling
- validation
- full workflow

## Next automation targets

If continuing test work, the best next steps are:

### Priority 1: frontend/session edge cases

- refresh page mid-session
- reset while streaming
- stop generation while streaming
- stale local storage recovery
- confirmation route entered too early

### Priority 2: retrieval quality assertions

- product overview question
- exclusions question
- deductible question
- beneficiary question
- claims scenario question

### Priority 3: stricter free-text validation

If needed later:

- add more guardrails for `location`
- add more guardrails for `vehicle_make`
- add more guardrails for `vehicle_model`

## Practical next recommendation

For the current repo, the backend invalid-value coverage is now in a good place for the assessment.

The next real quality gain would come from:

- browser/manual validation of those same cases
- or frontend automation around session synchronization

That is the next most useful test layer, not another large backend rewrite.
