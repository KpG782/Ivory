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

The frontend does not need a local env file for normal development if the backend runs on `http://127.0.0.1:8000`.

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

- Ask a product question:
  - Example: `What does comprehensive coverage include?`
- Start a quote:
  - Example: `I need a quote for auto insurance`
- Continue answering the requested fields one by one
- Watch the right-side state panel:
  - `Mode`
  - `Insurance Type`
  - `Current Step`
  - `Next Field`
- Once a quote is generated, the quote card fills in and `Review Quote` becomes available

### Confirmation flow

Use `/quote-confirmation` only after the backend reaches confirm state.

- `Accept & Buy Now` sends `accept`
- `Adjust Coverage` sends `adjust`
- If the backend is not ready, the page stays guarded and tells you to continue on the dashboard

## 4. Manual end-to-end test

### Test A: conversational mode

In the UI, send:

```text
What types of insurance do you offer?
```

Expected:

- assistant responds with product information
- session mode stays conversational unless the backend switches into quote flow

### Test B: auto quote flow

In the UI, send these one at a time:

```text
I need a quote for auto insurance
2019
Toyota
Camry
35
0
standard
```

Expected:

- backend moves into transactional mode
- the assistant asks for the next missing field each turn
- a quote summary appears after the required details are collected
- `Review Quote` becomes enabled

### Test C: confirm or adjust

After the quote is ready:

1. Open `/quote-confirmation`
2. Click `Accept & Buy Now`

Or:

1. Open `/quote-confirmation`
2. Click `Adjust Coverage`

Expected:

- the action is sent back into the same backend session
- the assistant either confirms or returns to an adjustment flow

### Test D: switch intent mid-quote

Start a quote, then ask:

```text
What does comprehensive coverage cover?
```

Expected:

- the assistant answers the product question
- the quote context is preserved
- the flow resumes instead of restarting from scratch

## 5. Important notes

- The backend is the source of truth for flow state.
- The frontend should only unlock confirmation when the backend session says:
  - `mode = transactional`
  - `quote_step = confirm`
  - `has_quote_result = true`
- If OpenRouter is unavailable, some quote logic can still work because the app has local flow and quote handling.
- Live product-answer quality depends on your `OPENROUTER_API_KEY` and network access.

## 6. Useful commands

Frontend checks:

```powershell
cd frontend
npm run typecheck
npm run build
```

Backend tests:

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

That usually means the backend has not reached quote confirmation state yet. Continue the quote in the main dashboard until a quote is generated.
