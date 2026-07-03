# Quote Flow Test Checklist

Use this checklist to verify the current Ivory flow in the browser against the exact issues that were failing before.

## Goal

Confirm that:

- quote answers stay inside the transactional flow
- product questions can interrupt the quote without losing progress
- compact multi-field auto inputs are handled correctly
- `adjust` reopens the quote flow instead of falling into RAG
- no unexpected session reset happens during normal use

## Test Setup

1. Start the backend from `backend/`.
2. Start the frontend from `frontend/`.
3. Open the app in a clean browser tab.
4. If possible, use a fresh session:
   - click `New quote`, or
   - manually reset once before beginning.
5. Open backend logs so you can watch each `/chat` request while testing.

## Expected Healthy Backend Signals

These are normal:

- `Uvicorn running on http://127.0.0.1:8000`
- `Loaded 12 documents`
- `Split into 20 chunks`
- `POST /chat HTTP/1.1" 200 OK`

These are the key things to watch for:

- no traceback
- no server crash
- no repeated forced reset unless you explicitly triggered one

## Test 1: Mid-Quote Question Should Resume Quote

### Steps

1. Send: `I want a quote for auto insurance`
2. Expect immediately: `What year is the vehicle? (e.g. 2019)`
3. Confirm the app has actually entered quote mode before continuing:
   - `Mode` should show quote flow / transactional
   - the bot should not answer this first message with a generic insurance explanation
3. Send: `What does comprehensive coverage include?`
4. Expect:
   - a correct coverage explanation
   - then a resume prompt for the same quote flow
   - specifically it should still ask for vehicle year afterward

### Pass Criteria

- the answer mentions comprehensive coverage correctly
- the app does not restart the quote
- the next prompt still asks for `vehicle year`

### Fail Signs

- first message `I want a quote for auto insurance` gets answered like a normal FAQ instead of opening the quote flow
- quote flow disappears
- app answers the question but does not resume the quote
- app restarts from product selection

## Test 2: Bare Numeric Reply Must Not Go To RAG

This was one of the actual failures before.

### Steps

1. Start fresh.
2. Send: `I want a quote for auto insurance`
3. Expect: `What year is the vehicle? (e.g. 2019)`
4. Send: `2019`

### Pass Criteria

- next prompt is `What is the vehicle make? (e.g. Toyota)`
- backend log still shows `200 OK`
- the bot does not say it lacks context for `2019`

### Fail Signs

- bot says it does not know what `2019` means
- bot answers as if `2019` were a general question
- quote flow stops progressing

## Test 3: Normal Auto Quote End-To-End

### Steps

1. Start fresh.
2. Send messages one at a time:
   - `I want a quote for auto insurance`
   - `2019`
   - `Toyota`
   - `Camry`
   - `35`
   - `0`
   - `standard`

### Pass Criteria

- each answer advances to the next required field
- final result shows an estimated auto premium
- the bot asks you to `accept`, `adjust`, or `restart`

### Fail Signs

- any field answer gets treated like a product FAQ
- flow jumps backward
- final quote never appears

## Test 4: Compact Multi-Field Auto Reply

This covers the second real failure from your transcript.

### Steps

1. Start fresh.
2. Send: `I want a quote for auto insurance`
3. Send: `2019`
4. When asked for vehicle make, send:

```text
Toyota, Camry, 35, 0, standard
```

### Pass Criteria

- the assistant should finish the auto quote directly or move correctly to confirmation
- it should not answer with a generic knowledge-base explanation
- it should not ask for already-supplied fields again unless one value was invalid

### Fail Signs

- bot says it needs more context about Toyota Camry
- bot treats the whole line as a question
- bot stores the whole line as one field and breaks the flow

## Test 5: `adjust` Should Reopen Collection

This was another failure path in your transcript.

### Steps

1. Complete an auto quote until the assistant shows the estimate.
2. Send: `adjust`

### Pass Criteria

- the quote flow reopens
- the assistant asks again: `What year is the vehicle? (e.g. 2019)`
- it does not answer with `What would you like to adjust?` as a general RAG-style fallback

### Fail Signs

- bot asks whether you mean auto or life quote
- bot leaves the confirm flow incorrectly
- bot does not clear the old quote details

## Test 6: Product Switch Mid-Flow

### Steps

1. Start an auto quote.
2. Answer the first field with `2019`.
3. Send: `I want a quote for home insurance`

### Pass Criteria

- flow switches to home quote
- next prompt becomes: `Is the property a house, condo, or apartment?`
- old auto data should no longer drive the prompts

### Fail Signs

- app keeps asking auto questions
- mixed auto/home prompts appear

## Test 7: Session Stability

### Steps

1. Start a quote.
2. Progress through 2-3 turns.
3. Do not click reset.
4. Watch the UI and backend logs.

### Pass Criteria

- no `The session has been reset...` message appears on its own
- the same conversation continues across turns
- backend continues returning `200 OK`

### Fail Signs

- session reset banner appears without user action
- quote state disappears suddenly
- conversation returns to welcome state unexpectedly

## Quick Results Table

Fill this in while testing:

| Test | Result | Notes |
|---|---|---|
| Mid-quote question resumes flow | PASS / FAIL | |
| Numeric reply `2019` advances correctly | PASS / FAIL | |
| Full auto quote works | PASS / FAIL | |
| Compact multi-field input works | PASS / FAIL | |
| `adjust` reopens collection | PASS / FAIL | |
| Product switch mid-flow works | PASS / FAIL | |
| Session remains stable | PASS / FAIL | |

## If Something Fails

Capture:

1. the exact message you sent
2. the assistant reply
3. the backend log line around that request
4. whether the UI showed a reset banner
5. whether it was a fresh session or restored session

## Recommended Smoke-Test Sequence

If you only want one short run, test in this order:

1. `I want a quote for auto insurance`
2. Verify the response is exactly the year prompt before continuing
3. `What does comprehensive coverage include?`
4. `2019`
5. `Toyota, Camry, 35, 0, standard`
6. `adjust`

Expected outcome:

- question is answered
- quote resumes at year
- `2019` advances to make
- compact input completes the quote
- `adjust` restarts collection from the first field
