# Backend Deployment With Docker Hub And Easypanel

This is the cleanest deployment path for the current Ivory backend.

## Recommended Setup

- Frontend on Vercel
- Backend on your own server through Easypanel
- Backend image stored on Docker Hub under your `kpg782` account

That setup is compatible with the current frontend because the Next proxy routes already read `BACKEND_API_BASE_URL`.

## What You Need

- Docker Hub account with permission to push images
- Easypanel running on your server
- `OPENROUTER_API_KEY`
- a public backend URL such as `https://ivory-api.yourdomain.com`

## Backend Image

The repo now includes:

- `backend/Dockerfile`
- `backend/.dockerignore`
- `docker-compose.backend.yml`

Build context should be the `backend/` folder.

The Dockerfile is tuned for the current backend behavior:

- single-process `uvicorn` to avoid in-memory session inconsistency
- healthcheck built in
- persistent paths for Chroma and Hugging Face caches
- only the runtime backend files are copied into the image
- `langgraph` is required by the backend runtime because the orchestrator now uses a compiled `StateGraph`
- no extra `curl` package just for health checks

## Build And Push To Docker Hub

From the repo root:

```bash
cd backend
docker build -t kpg782/ivory-backend:latest .
docker push kpg782/ivory-backend:latest
```

If you want a versioned tag too:

```bash
docker build -t kpg782/ivory-backend:v1 -t kpg782/ivory-backend:latest .
docker push kpg782/ivory-backend:v1
docker push kpg782/ivory-backend:latest
```

## Optional Compose Run On Your Own Server

If you want to run the backend directly with Docker Compose outside Easypanel:

```bash
docker compose -f docker-compose.backend.yml up -d
```

That compose file is intentionally backend-only and optimized for the current app.

## Easypanel Service Setup

Create a new app/service in Easypanel using an existing Docker image:

- Image: `kpg782/ivory-backend:latest`
- Container port: `8000`
- Public HTTP port: expose through Easypanel's domain/proxy

### Required Environment Variables

- `OPENROUTER_API_KEY`

Optional:

- `OPENROUTER_MODEL`
- `CHROMA_PERSIST_DIR=/data/vectorstore`
- `HF_TOKEN`
- `PORT=8000`

Optional front-desk integrations (leave unset for safe dry-run demo mode — `accept` then reports "demo mode" lines and never touches the network):

- `AIRTABLE_API_KEY`, `AIRTABLE_BASE_ID`, `AIRTABLE_TABLE_NAME` (default `Leads`)
- `CALCOM_API_KEY`, `CALCOM_EVENT_TYPE_ID`, `CLINIC_TIMEZONE` (default `UTC`)
- `RESEND_API_KEY`, `RESEND_FROM` (default `Ivory <onboarding@resend.dev>`)

## Persistent Volume

The backend writes its Chroma data to `CHROMA_PERSIST_DIR`.

Recommended volume mount:

- mount a persistent volume to `/data`

Why:

- the knowledge-base index can persist across restarts
- startup is faster after the first run
- you avoid rebuilding the vector store every container restart

## Health Checks

Use:

- `GET /health`

Optional debug check:

- `GET /debug`

`/debug` is useful before demo day because it shows:

- whether the KB loaded
- whether retrieval works
- whether OpenRouter is reachable

## Vercel Frontend Configuration

In your Vercel project, set:

- `BACKEND_API_BASE_URL=https://your-backend-domain`

Example:

```text
BACKEND_API_BASE_URL=https://ivory-api.example.com
```

The frontend proxy routes will then forward:

- `/api/chat` -> `https://your-backend-domain/chat`
- `/api/reset` -> `https://your-backend-domain/reset`

## Important Deployment Notes

### 1. Session state is in memory

The current backend keeps conversation state in the in-process LangGraph checkpointer (`MemorySaver`).

That means:

- active sessions are lost if the container restarts
- this is acceptable for a take-home/demo
- do not scale to multiple replicas unless you swap in a shared/persistent checkpointer

For now, use one backend instance and one `uvicorn` worker.

### 2. First startup may be slower

The backend loads embeddings and ensures the knowledge base index on startup.

That means first boot can take longer than a simple FastAPI app.

### 3. Hugging Face model download

If the sentence-transformer model is not cached yet, the container may download it on first run.

Using `HF_TOKEN` is optional but can reduce rate-limit friction.

## Manual Smoke Test After Deployment

Run these checks in order:

1. Open `https://your-backend-domain/health`
2. Open `https://your-backend-domain/debug`
3. Confirm `knowledge_base.ok=true`
4. Confirm `llm.api_key_present=true`
5. Open the Vercel frontend
6. Ask `What dental services do you offer?`
7. Ask `I'd like to book an appointment`
8. Complete one `cleaning` intake path and `accept` it (expect the "Front desk actions" dry-run block without integration keys)

## Recommended Final Architecture

```text
User
  │
  ▼
Vercel Next.js frontend
  │
  │ BACKEND_API_BASE_URL
  ▼
Easypanel reverse proxy
  │
  ▼
Docker container: kpg782/ivory-backend
  │
  ├─ FastAPI app
  ├─ in-memory LangGraph checkpointer (sessions)
  └─ Chroma persist dir mounted at /data/vectorstore
```

## Is This Setup Viable

Yes.

For your current repo, this is the most practical deployment setup:

- simple
- cheap
- easy to explain
- consistent with the current backend and frontend code
