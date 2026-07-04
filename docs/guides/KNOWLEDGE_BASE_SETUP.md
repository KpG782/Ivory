# Knowledge Base Setup

## What was added

The Ivory knowledge base is a set of 12 dental documents for:

- the clinic overview and FAQ (hours, parking, cancellation policy, new patients)
- the three services: routine checkups and cleanings, dental emergencies, cosmetic dentistry
- pricing, visit estimates, insurance, and payment options
- health education: tooth decay, gum disease, children's dentistry, oral cancer screening
- aftercare scenarios (post-extraction, post-whitening, sensitivity)

Health content is grounded in public-domain NIDCR and CDC pages — never ADA/MouthHealthy content — and every document ends with a `Sources:` line. Clinic-specific facts (fees, hours, policies) are fictional demo content for Ivory Dental Studio. These documents are meant to cover the kinds of questions patients actually ask during the demo.

## Current knowledge base size

At the time of this update:

- documents: `12`
- chunks: `54`

The current vector backend is Chroma and it persists under:

`backend/vectorstore`

## How the knowledge base works

The backend loads markdown files from:

`backend/knowledge_base`

When the app needs retrieval, it chunks those markdown files, embeds them, and stores them in the configured vector index.

The retrieval system is implemented in:

- `backend/services/vectorstore.py`

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

## Recommended manual tests for the knowledge

Try these prompts:

### Cleanings

- `What happens during a routine dental checkup?`
- `How often should I get a cleaning?`
- `Why do plaque and tartar matter?`

### Emergencies

- `What should I do about a toothache?`
- `My tooth got knocked out — what do I do?`
- `Is facial swelling a dental emergency?`

### Cosmetic

- `How does professional teeth whitening work?`
- `What is the difference between veneers and bonding?`
- `Do clear aligners hurt?`

### Mixed demo questions

- `What dental services do you offer?`
- `What are your hours?`
- `How does insurance affect my visit estimate?`

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

- factual and grounded in public-domain sources (NIDCR/CDC)
- short to medium length
- clearly titled
- focused on one dental topic
- closed with a `Sources:` line

Avoid:

- ADA or MouthHealthy content (licensing)
- duplicate clinic policy statements
- long marketing copy
- vague general dental filler

Good next additions would be:

- root canal and crown explainers
- wisdom teeth guidance
- dry mouth and medication side effects
- pregnancy and oral health
- dental X-ray safety guidance
