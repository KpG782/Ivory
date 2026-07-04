# Intake Flow Test Checklist

Use this checklist to verify the current Ivory flow in the browser against the exact issue classes that were failing before the flow was hardened.

## Goal

Confirm that:

- intake answers stay inside the transactional flow
- dental questions can interrupt the intake without losing progress
- compact multi-field inputs are handled correctly
- invalid values (out-of-range numbers, filler text) re-prompt without advancing
- `accept`, `adjust`, and `restart` all work after an estimate exists
- no unexpected session reset happens during normal use

## Test Setup

1. Start the backend from `backend/`.
2. Start the frontend from `frontend/`.
3. Open the app in a clean browser tab.
4. If possible, use a fresh session:
   - click `New chat`, or
   - manually reset once before beginning.
5. Open backend logs so you can watch each `/chat` request while testing.

## Expected Healthy Backend Signals

These are normal:

- `Uvicorn running on http://127.0.0.1:8000`
- `Loaded 12 documents`
- `Split into 54 chunks`
- `POST /chat HTTP/1.1" 200 OK`

These are the key things to watch for:

- no traceback
- no server crash
- no repeated forced reset unless you explicitly triggered one

## Test 1: Mid-Intake Question Should Resume Intake

### Steps

1. Send: `I'd like to book a cleaning`
2. Expect immediately: `What's the patient's full name? (e.g. Maria Santos)`
3. Confirm the app has actually entered intake mode before continuing:
   - the flow chip should show the cleaning intake / transactional mode
   - the bot should not answer this first message with a generic dental explanation
4. Send: `What should I do about a toothache?`
5. Expect:
   - a correct toothache answer from the knowledge base
   - then a resume line for the same intake, ending with:
     `Now, back to your cleaning visit intake — What's the patient's full name? (e.g. Maria Santos)`

### Pass Criteria

- the answer covers toothache first steps correctly
- the app does not restart the intake
- the next prompt still asks for the patient's full name
- a question that mentions a booking word (e.g. `How much does a whitening appointment cost?`) is also answered-then-resumed — it must not wipe progress or switch the service

### Fail Signs

- first message `I'd like to book a cleaning` gets answered like a normal FAQ instead of opening the intake flow
- intake flow disappears
- app answers the question but does not resume the intake
- app restarts from service selection

## Test 2: Bare Year Reply Must Not Go To RAG

This was one of the actual failures in the old vertical (a bare field value being misread as a new question).

### Steps

1. Start fresh.
2. Send: `I'd like to book a cleaning`
3. Send: `Maria Santos`
4. Send: `maria@example.com`
5. Expect: `What year was your last dental visit? (e.g. 2024)`
6. Send: `2024`

### Pass Criteria

- next prompt is `Do you have dental insurance, or are you paying out of pocket? (insured or self-pay)`
- backend log still shows `200 OK`
- the bot does not say it lacks context for `2024`

### Fail Signs

- bot says it does not know what `2024` means
- bot answers as if `2024` were a general question
- intake flow stops progressing

## Test 3: Normal Cleaning Intake End-To-End

### Steps

1. Start fresh.
2. Send messages one at a time:
   - `I'd like to book a cleaning`
   - `Maria Santos`
   - `maria@example.com`
   - `2024`
   - `insured`
   - `morning`

### Pass Criteria

- each answer advances to the next required field, in this order: name, email, last visit year, insurance status, preferred time
- final result shows an estimated cleaning cost range, for example:
  `Your estimated cleaning visit cost is $59.98–$88.20. This is an educational estimate, not a diagnosis or final price. Reply accept to confirm, adjust to change details, or restart to start over.`
  (the exact figures depend on the current calendar year — the recency factor uses years since the last visit)
- the VisitCard renders the range and the collected details

### Fail Signs

- any field answer gets treated like a dental FAQ
- flow jumps backward
- final estimate never appears

## Test 4: Compact Multi-Field Cleaning Reply

This covers the compact-input case: one message that fills every cleaning field at once. Comma-separated compact replies work for all three services; the same trick fills the emergency and cosmetic fields in order (e.g. `Ken Garcia, 555-201-7788, toothache, 7, insured`).

### Steps

1. Start fresh.
2. Send: `I'd like to book a cleaning`
3. When asked for the patient's name, send:

```text
Maria Santos, maria@example.com, 2024, insured, morning
```

### Pass Criteria

- the assistant should finish the cleaning intake directly and show the estimate range with the accept/adjust/restart prompt
- it should not answer with a generic knowledge-base explanation
- it should not ask for already-supplied fields again unless one value was invalid

### Fail Signs

- bot says it needs more context about Maria Santos
- bot treats the whole line as a question
- bot stores the whole line as one field and breaks the flow

## Test 5: Invalid Inputs Must Re-Prompt Without Advancing

Each invalid value must produce an error plus the same field prompt again, and the flow must stay on that field.

### Steps and Expected Replies

1. Cleaning flow, at the name prompt, send: `i like dogs`
   - Expect: `Please enter only the patient's full name. What's the patient's full name? (e.g. Maria Santos)`
2. Cleaning flow, at the last-visit-year prompt, send: `2031`
   - Expect: `Last dental visit year must be between 1901 and <current year>. What year was your last dental visit? (e.g. 2024)`
3. Emergency flow (`I need to book an emergency visit`), advance to the pain prompt (`On a scale of 0 to 10, how bad is the pain right now?`), then send: `-2`
   - Expect: `Please enter a pain level between 0 and 10. On a scale of 0 to 10, how bad is the pain right now?`

### Pass Criteria

- each invalid value is rejected with the exact error-plus-prompt reply
- sending the corrected value afterwards advances normally
- the rejected value never appears in the collected data

### Fail Signs

- an invalid value advances to the next field
- the bot answers the invalid value as a general question
- the flow leaves the intake

## Test 6: `adjust` Should Reopen Collection

### Steps

1. Complete a cleaning intake until the assistant shows the estimate range.
2. Send: `adjust`

### Pass Criteria

- the intake flow reopens with the same service
- the assistant asks again: `What's the patient's full name? (e.g. Maria Santos)`
- it does not answer with a general RAG-style fallback

### Fail Signs

- bot asks whether you mean a cleaning or a cosmetic consultation
- bot leaves the confirm step incorrectly
- bot does not clear the old intake details

## Test 7: `restart` Should Reset Service Selection

### Steps

1. Complete an intake until the assistant shows the estimate range.
2. Send: `restart`

### Pass Criteria

- the assistant replies: `The intake has been restarted. Which type of visit would you like to set up: a cleaning, an emergency visit, or a cosmetic consultation?`
- choosing a service (e.g. `emergency`) starts a fresh intake at the name prompt

### Fail Signs

- old collected data survives the restart
- the bot skips the service menu

## Test 8: Service Switch Mid-Flow

### Steps

1. Start a cleaning intake and answer the first two fields (`Maria Santos`, `maria@example.com`).
2. Send: `Actually, book an emergency visit instead`

### Pass Criteria

- flow switches to the emergency intake and starts over at:
  `What's the patient's full name? (e.g. Maria Santos)`
- after giving the name, the next prompt is emergency-specific:
  `What phone number can we reach you at? (e.g. 555-201-7788)`
- old cleaning data no longer drives the prompts

### Fail Signs

- app keeps asking cleaning questions
- mixed cleaning/emergency prompts appear

## Test 9: `accept` Fires The Front-Desk Actions Block

With the integration env vars unset (the default local setup), accepting runs every integration in dry-run mode — nothing touches the network.

### Steps

1. Complete a cleaning intake until the estimate range appears.
2. Send: `accept`

### Pass Criteria

- the reply confirms and contains a deterministic `Front desk actions:` block:

```text
Confirmed. I have finalized Routine exam & cleaning for Maria Santos.

Front desk actions:
- Airtable CRM: Airtable (demo mode): lead captured locally
- Cal.com booking: Cal.com (demo mode): booking request recorded locally
- Email confirmation: Resend (demo mode): confirmation email drafted locally

When you're ready for another visit, just say book a cleaning, book an emergency visit, or book a cosmetic consultation.
```

- for an emergency intake (phone contact, no email), the email line becomes:
  `- Email confirmation: No email on file for this visit (phone contact only) — the front desk will call instead.`
- after accepting, the collected answers and the estimate are cleared — the status chip returns to `Knowledge mode`, and the next intake starts from a clean slate
- backend logs show no outbound integration requests

### Fail Signs

- the block is missing or has fewer than three lines
- an integration attempts a real network call without keys
- the accept turn errors out

## Test 10: Session Stability

### Steps

1. Start an intake.
2. Progress through 2-3 turns.
3. Do not click reset.
4. Watch the UI and backend logs.

### Pass Criteria

- no `The intake has been restarted...` message appears on its own
- the same conversation continues across turns
- backend continues returning `200 OK`

### Fail Signs

- session reset banner appears without user action
- intake state disappears suddenly
- conversation returns to welcome state unexpectedly

## Quick Results Table

Fill this in while testing:

| Test | Result | Notes |
|---|---|---|
| Mid-intake question resumes flow | PASS / FAIL | |
| Bare year reply `2024` advances correctly | PASS / FAIL | |
| Full cleaning intake works | PASS / FAIL | |
| Compact multi-field input works | PASS / FAIL | |
| Invalid inputs re-prompt without advancing | PASS / FAIL | |
| `adjust` reopens collection | PASS / FAIL | |
| `restart` resets service selection | PASS / FAIL | |
| Service switch mid-flow works | PASS / FAIL | |
| `accept` shows the Front desk actions block | PASS / FAIL | |
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

1. `I'd like to book a cleaning`
2. Verify the response is exactly the name prompt before continuing
3. `What should I do about a toothache?`
4. `Maria Santos, maria@example.com, 2024, insured, morning`
5. `adjust`
6. `Maria Santos, maria@example.com, 2024, insured, morning`
7. `accept`

Expected outcome:

- question is answered, then the intake resumes at the name prompt
- compact input completes the intake and shows the estimate range
- `adjust` restarts collection from the first field
- the second compact input rebuilds the estimate
- `accept` prints the three-line `Front desk actions:` dry-run block
