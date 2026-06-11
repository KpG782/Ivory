# Knowledge Base Setup

## What was added

The Ivory knowledge base now includes additional high-value documents for:

- auto coverage levels and deductibles
- home exclusions, limits, and add-ons
- life underwriting and beneficiary basics
- discounts, eligibility, and quote readiness
- scenario-based claims examples

These additions are meant to improve retrieval quality for the kinds of questions users actually ask during the demo.

## Current knowledge base size

At the time of this update:

- documents: `12`
- chunks: `20`

The current vector backend is Chroma and it persists under:

`backend/vectorstore`

## How the knowledge base works

The backend loads markdown files from:

`backend/knowledge_base`

When the app needs retrieval, it chunks those markdown files, embeds them, and stores them in the configured vector index.

The retrieval system is implemented in:

- [vectorstore.py](/C:/Users/kpg78/Downloads/TENEXT/ivory-chatbot/backend/services/vectorstore.py)

## Important setup note

The app can build the knowledge index automatically during use, but if you add or update knowledge base files, it is better to rebuild the index before testing.

## Rebuild command

From the repo root:

```powershell
cd backend
.venv\Scripts\Activate.ps1
python rebuild_knowledge_base.py
```

Expected output is a short report with:

- document count
- chunk count
- backend type
- persist directory

## Run the backend after rebuilding

```powershell
cd backend
.venv\Scripts\Activate.ps1
python -m uvicorn main:app --reload --port 8000
```

## Run the frontend

In a second terminal:

```powershell
cd frontend
npm run dev
```

Open:

`http://localhost:3000`

## Recommended manual tests for the new knowledge

Try these prompts:

### Auto

- `What is the difference between basic, standard, and comprehensive auto coverage?`
- `Does comprehensive cover theft or hail damage?`
- `What is a deductible in auto insurance?`

### Home

- `Does home insurance cover flood damage?`
- `Are expensive items fully covered under personal property coverage?`
- `What does a home insurance deductible mean?`

### Life

- `What is a beneficiary in life insurance?`
- `Why does smoker status affect life insurance pricing?`
- `What happens if a life insurance policy lapses?`

### Mixed demo questions

- `Do you offer bundling discounts?`
- `What do I need before starting an auto quote?`
- `If hail damages my parked car, is that collision or comprehensive?`

## About embeddings and network access

The preferred embedding model is:

`sentence-transformers/all-MiniLM-L6-v2`

If that model is not already available locally, the sentence-transformer stack may try to reach Hugging Face to resolve model files.

If network access is blocked or unavailable:

- the app can still fall back to a local hash-based embedding path
- retrieval still works, but quality may be weaker than with the real embedding model

So for best RAG quality, let the embedding model download and cache successfully at least once.

## Best practice when adding more documents

Add documents that are:

- factual
- short to medium length
- clearly titled
- focused on one policy topic

Avoid:

- duplicate policy statements
- long marketing copy
- vague general insurance filler

Good next additions would be:

- auto liability limit examples
- home personal property sub-limit examples
- life policy term-length comparison guidance
- cancellation and renewal rules
- quote disclaimer and estimate-vs-final-offer guidance
