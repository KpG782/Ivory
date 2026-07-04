# Ivory E2E Testing Guide

## Current Status

The repository can be tested end to end today with these caveats:

- The backend API is implemented and exposes `POST /chat`, `POST /reset`, and `GET /health`.
- The frontend is implemented, builds successfully, and talks to the backend over SSE.
- The backend virtual environment must be `backend/.venv` on Python 3.12.
- The intake flow works locally without an LLM because routing, field collection, validation, and visit estimation all have local deterministic logic.
- Dental-question answers can fall back to knowledge-base summaries if the OpenRouter call is unavailable.
- The front-desk integrations (Airtable, Cal.com, Resend) run in dry-run mode when their env keys are unset, so `accept` is safe to test offline.

## .env Implementation

The backend now loads `.env` automatically from either:

- `backend/.env`
- repo root `.env`

The frontend supports Next.js env files such as:

- `frontend/.env`
- `frontend/.env.local`

## Required Variables

Backend:

```env
OPENROUTER_API_KEY=your_key_here
# Optional
OPENROUTER_MODEL=meta-llama/llama-3.1-8b-instruct
CHROMA_PERSIST_DIR=./backend/vectorstore
# Optional front-desk integrations (unset = dry-run demo mode)
AIRTABLE_API_KEY=
AIRTABLE_BASE_ID=
AIRTABLE_TABLE_NAME=Leads
CALCOM_API_KEY=
CALCOM_EVENT_TYPE_ID=
CLINIC_TIMEZONE=UTC
RESEND_API_KEY=
RESEND_FROM=Ivory <onboarding@resend.dev>
```

Frontend:

```env
BACKEND_API_BASE_URL=http://localhost:8000
AUTH_USERNAME=your_demo_username
AUTH_PASSWORD=your_demo_password
```

If `BACKEND_API_BASE_URL` is not set, the Next.js proxy defaults to `http://127.0.0.1:8000`.

## Verified Checks

These checks were verified locally:

- `backend/.venv` is using Python 3.12.
- `pip install -r backend/requirements.txt` succeeds in that venv.
- Frontend `npm run typecheck` passes.
- Frontend `npm run build` passes.
- Backend `/health` returns `{"status":"ok"}`.
- Backend `/reset` works.
- Backend `/chat` streams SSE events.
- The cleaning intake flow completes successfully through confirmation.
- Mid-flow interruption works and resumes the intake flow after answering.
- `accept` renders the three-line "Front desk actions" dry-run block without network calls.
- The automated suite passes: `backend/.venv/bin/python -m pytest tests/ -q` → 56 passed.

## What Is Not Fully Verified

- Real browser-driven UI automation was not run.
- Live OpenRouter responses depend on a valid outbound network path and working API key.
- Live Airtable/Cal.com/Resend calls depend on real keys; the suite covers them with monkeypatched HTTP.
- The backend test suite covers integration behavior, but browser-driven UI automation is still limited.

## How To Run Locally

### 1. Backend

From the repo root:

```powershell
cd backend
.venv\Scripts\Activate.ps1
python -m uvicorn main:app --reload --port 8000
```

Quick backend checks:

```powershell
Invoke-RestMethod http://localhost:8000/health
Invoke-RestMethod http://localhost:8000/reset -Method Post -ContentType 'application/json' -Body '{"session_id":"demo"}'
```

### 2. Frontend

In a second terminal:

```powershell
cd frontend
npm run dev
```

Open:

```text
http://localhost:3000
```

## End-to-End Manual Test Script

Run these in the browser UI:

1. Ask `What dental services do you offer?`
2. Start `I'd like to book a cleaning`
3. Answer:
   `Maria Santos`
   `maria@example.com`
   `2024`
   `insured`
   `morning`
4. Confirm with `accept`
5. Start another intake and interrupt mid-flow with `What should I do about a toothache?`

Expected behavior:

- Messages stream in incrementally.
- The visit estimate appears after the last required field.
- `accept` finalizes the request and prints the `Front desk actions:` block (dry-run lines without keys).
- The interruption answer returns and then the intake prompt resumes.

## Practical Conclusion

Yes, you can test the app end to end now with:

- backend running from `backend/.venv`
- frontend running from `frontend`
- a valid `.env` file

For local intake-flow validation, the app is already usable even if OpenRouter is unavailable. For full intended behavior, you still need a working `OPENROUTER_API_KEY` and outbound network access.
