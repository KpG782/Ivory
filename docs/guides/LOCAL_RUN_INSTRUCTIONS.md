# Ivory Local Run Instructions

## What runs where

- Backend: FastAPI app in `backend/`
- Frontend: Next.js app in `frontend/`
- Frontend API routes proxy to the backend:
  - `POST /api/chat`
  - `POST /api/reset`
- Default backend target from the frontend proxy: `http://127.0.0.1:8000`

## Prerequisites

- Python `3.12`
- Node.js `20.9+`
- Backend virtual environment already created at `backend/.venv`
- A valid `.env` file with your OpenRouter key if you want live LLM responses

## Environment setup

The backend loads `.env` automatically from either:

- repo root `.env`
- `backend/.env`

Minimum backend env:

```env
OPENROUTER_API_KEY=your_key_here
```

Optional backend env:

```env
OPENROUTER_MODEL=meta-llama/llama-3.1-8b-instruct
CHROMA_PERSIST_DIR=./backend/vectorstore
```

Optional front-desk integration env (leave unset for dry-run demo mode — no network calls on `accept`):

```env
AIRTABLE_API_KEY=
AIRTABLE_BASE_ID=
AIRTABLE_TABLE_NAME=Leads
CALCOM_API_KEY=
CALCOM_EVENT_TYPE_ID=
CLINIC_TIMEZONE=UTC
RESEND_API_KEY=
RESEND_FROM=Ivory <onboarding@resend.dev>
```

The frontend does not need a local env file for normal development if the backend runs on `http://127.0.0.1:8000`, but the login screen requires credentials in `frontend/.env.local`:

```env
AUTH_USERNAME=your_demo_username
AUTH_PASSWORD=your_demo_password
```

Only set this if your backend runs somewhere else:

```env
BACKEND_API_BASE_URL=http://127.0.0.1:8000
```

## 1. Start the backend

Open terminal 1 from the repo root:

```powershell
cd backend
.venv\Scripts\Activate.ps1
python -m uvicorn main:app --reload --port 8000
```

Expected backend URL:

```text
http://127.0.0.1:8000
```

Quick backend check:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

Expected response:

```json
{"status":"ok"}
```

## 2. Start the frontend

Open terminal 2 from the repo root:

```powershell
cd frontend
npm run dev
```

Open:

```text
http://localhost:3000
```

## 3. How the flow works

### Dashboard flow

Use the main page at `/`.

- Ask a dental question:
  - Example: `What does a routine cleaning include?`
- Start an intake:
  - Example: `I'd like to book a cleaning`
- Continue answering the requested fields one by one
- Watch the header chips:
  - flow chip: `cleaning intake · collect` (service + step)
  - status chip: `Knowledge mode` / `Collecting details` / `Estimate ready`
- Once an estimate is generated, the visit card fills in with the cost range and collected details

### Confirmation flow

Use `/visit-confirmation` only after the backend reaches confirm state.

- `Accept & Book Visit` sends `accept`
- `Adjust Details` sends `adjust`
- `Call the Clinic` is a `tel:` link to the front desk
- If the backend is not ready, the page stays guarded and tells you to continue on the dashboard

## 4. Manual end-to-end test

### Test A: conversational mode

In the UI, send:

```text
What dental services do you offer?
```

Expected:

- assistant responds with the three services (cleanings, emergency visits, cosmetic consultations)
- session mode stays conversational unless the backend switches into an intake flow

### Test B: cleaning intake flow

In the UI, send these one at a time:

```text
I'd like to book a cleaning
Maria Santos
maria@example.com
2024
insured
morning
```

Expected:

- backend moves into transactional mode
- the assistant asks for the next missing field each turn
- an estimate range appears after the required details are collected
- the visit card and `/visit-confirmation` become usable

### Test C: confirm or adjust

After the estimate is ready:

1. Open `/visit-confirmation`
2. Click `Accept & Book Visit`

Or:

1. Open `/visit-confirmation`
2. Click `Adjust Details`

Expected:

- the action is sent back into the same backend session
- `accept` prints the "Front desk actions" block (dry-run lines without integration keys); `adjust` returns to the first intake field

### Test D: switch intent mid-intake

Start an intake, then ask:

```text
What should I do about a toothache?
```

Expected:

- the assistant answers the dental question
- the intake context is preserved
- the flow resumes instead of restarting from scratch

## 5. Important notes

- The backend is the source of truth for flow state.
- The frontend should only unlock confirmation when the backend session says:
  - `mode = transactional`
  - `intake_step = confirm`
  - `has_visit_estimate = true`
- If OpenRouter is unavailable, the intake flow still works because routing, field collection, validation, and estimation are all local deterministic logic.
- Live dental-answer quality depends on your `OPENROUTER_API_KEY` and network access.
- Without integration keys, `accept` runs Airtable/Cal.com/Resend in dry-run mode and never touches the network.

## 6. Useful commands

Frontend checks:

```powershell
cd frontend
npm run typecheck
npm run build
```

Backend tests (56 tests):

```powershell
cd ..
backend\.venv\Scripts\python.exe -m pytest -q
```

## 7. If something fails

### Backend not reachable from frontend

Check:

- backend server is running on port `8000`
- frontend is running on port `3000`
- `BACKEND_API_BASE_URL` is correct if you changed the backend host or port

### OpenRouter not being used

Check:

- `.env` exists in repo root or `backend/.env`
- `OPENROUTER_API_KEY` is valid
- restart the backend after changing `.env`

### Confirmation page says it is not ready

That usually means the backend has not reached the confirm step yet. Continue the intake in the main dashboard until an estimate is generated.
