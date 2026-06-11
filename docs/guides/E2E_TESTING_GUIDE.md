# Ivory E2E Testing Guide

## Current Status

The repository can be tested end to end today with these caveats:

- The backend API is implemented and exposes `POST /chat`, `POST /reset`, and `GET /health`.
- The frontend is implemented, builds successfully, and talks to the backend over SSE.
- The backend virtual environment must be `backend/.venv` on Python 3.12.
- Quote flow works locally without an LLM because routing, field collection, validation, and quote calculation all have local logic.
- Product-question answers can fall back to knowledge-base summaries if the OpenRouter call is unavailable.

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
```

Frontend:

```env
BACKEND_API_BASE_URL=http://localhost:8000
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
- Auto quote flow completes successfully through confirmation.
- Mid-flow interruption works and resumes the quote flow after answering.

## What Is Not Fully Verified

- Real browser-driven UI automation was not run.
- Live OpenRouter responses depend on a valid outbound network path and working API key.
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

1. Ask `What types of insurance do you offer?`
2. Start `I want a quote for auto insurance`
3. Answer:
   `2019`
   `Toyota`
   `Camry`
   `35`
   `0`
   `standard`
4. Confirm with `accept`
5. Start another quote and interrupt mid-flow with `What does comprehensive cover?`

Expected behavior:

- Messages stream in incrementally.
- The quote result appears after the last required field.
- `accept` finalizes the quote.
- The interruption answer returns and then the quote prompt resumes.

## Practical Conclusion

Yes, you can test the app end to end now with:

- backend running from `backend/.venv`
- frontend running from `frontend`
- a valid `.env` file

For local quote-flow validation, the app is already usable even if OpenRouter is unavailable. For full intended behavior, you still need a working `OPENROUTER_API_KEY` and outbound network access.
