# Ivory — Pre-Demo Checklist

---

## 30 Minutes Before

### Backend
- [ ] `cd backend && .venv/Scripts/Activate.ps1` (Windows) or `source .venv/bin/activate` (Unix)
- [ ] `python -m uvicorn main:app --reload --port 8000`
- [ ] Wait for: `Knowledge base ready — backend=chroma chunks=N` in the terminal
- [ ] Hit `http://localhost:8000/health` — confirm `{"status": "ok"}`
- [ ] Hit `http://localhost:8000/debug` — confirm both `knowledge_base.ok: true` AND `llm.ok: true`
  - If `llm.ok: false`: check `OPENROUTER_API_KEY` in `.env` at repo root
  - If `knowledge_base.ok: false`: run `python rebuild_knowledge_base.py` from backend directory

### Frontend
- [ ] `cd frontend && npm run dev`
- [ ] Open `http://localhost:3000`
- [ ] Confirm login screen appears (not a blank page, not a 500)
- [ ] Log in: username `admin`, password `ivory123` — confirm chat screen loads
  - Use the eye icon button to toggle password visibility if needed
  - Verify `GET /api/auth/check` returns `{"authenticated": true}` in DevTools → Network

### End-to-End Happy Path Test
- [ ] Send: "What does comprehensive coverage include?" — confirm a grounded answer comes back
- [ ] Send: "I want a quote for auto insurance" — confirm bot asks "What year is the vehicle?"
- [ ] Interrupt: "What does liability mean?" — confirm bot answers AND re-asks the year question
- [ ] Complete one full auto quote (2019, Toyota, Camry, 35, 0, standard) — confirm quote card appears
- [ ] Type "restart" — confirm bot resets to "which insurance type would you like"

### Environment Checks
- [ ] `.env` at repo root has `OPENROUTER_API_KEY=sk-or-...` (not empty)
- [ ] No hardcoded `localhost` in any browser network calls (check DevTools → Network if unsure)
- [ ] If demoing on a different machine: update `BACKEND_API_BASE_URL` in `frontend/.env.local`

### Presentation Setup
- [ ] Browser dev tools closed (no red console errors visible to interviewer)
- [ ] Terminal showing backend logs — clean, no red errors
- [ ] Browser tabs: localhost:3000 (chat), localhost:8000/debug (diagnostic)
- [ ] ARCHITECTURE.md open in a text editor for reference
- [ ] QA_PREP.md open in a second tab for quick lookup
- [ ] Screen share confirmed on correct monitor

---

## Demo Script (8-10 minutes)

### Opening (30 seconds)
"Ivory is a hybrid insurance assistant. It does two things in one session: answers knowledge-base questions using RAG, and runs a structured multi-step quote workflow. The key design challenge — and what I want to show you — is that you can interrupt a quote, ask a side question, and the bot brings you back to exactly where you were."

**Credentials:** Username `admin`, password `ivory123`. Use the eye icon to reveal the password if needed. Auth is server-side httpOnly cookie — there's no "Use saved access" button anymore.

---

### Step 1: Knowledge Mode (60 seconds)
Type: `What does comprehensive coverage include?`

**Say:** "The bot retrieves from 12 curated Markdown documents using ChromaDB and sentence-transformers. The answer is grounded — it can cite sources and won't invent policy details. I built a fallback: if the LLM is unavailable, it still answers using formatted text from the retrieved chunks."

**Point to sidebar:** "Mode shows 'Knowledge Mode'. The sidebar shows live backend state — this is purely rendering what the backend tells it."

---

### Step 2: Enter Quote Flow (30 seconds)
Type: `I want a quote for auto insurance`

**Say:** "Sidebar flips to 'Quote Flow', Step → 'Collect'. The backend is now running a state machine — a LangGraph StateGraph. It knows we're collecting auto insurance fields, and it's tracking which field we're on."

**Point to:** The "What year is the vehicle?" response.

---

### Step 3: The Core Demo Moment — Interrupt and Resume (90 seconds)
Type: `What does liability coverage mean?` (with the `?`)

**Wait for response.**

**Say:** "This is the key behavior. The bot answered the knowledge question AND re-appended the field prompt at the end — 'Now, back to your auto quote — What year is the vehicle?' The quote state is completely preserved. The current field pointer, the mode, the collected data — all intact. The backend is the source of truth; the frontend just renders what it receives."

**Point to:** The two-part response (RAG answer + field re-prompt).

Type: `2019` — confirm it advances to "What is the vehicle make?"

---

### Step 4: Complete the Quote (2 minutes)
Answer remaining fields: `Toyota`, `Camry`, `35`, `0`, `standard`

**Say when quote appears:** "The premium is deterministic — same inputs always produce the same output. The LLM never touches the number. I made this intentional: insurance pricing has to be auditable and reproducible. There are multipliers for driver age, accident history, vehicle age, and coverage level."

**Point to:** Quote card in sidebar.

---

### Step 5: Show Adjust/Restart (30 seconds)
Type: `adjust`

**Say:** "Three confirmation actions: accept, adjust, restart. Adjust wipes collected data and sends you back to field 1, preserving the insurance type. Restart resets everything."

---

### Step 6: Architecture (if time allows — 90 seconds)
**Switch to ARCHITECTURE.md, Section 2 data flow diagram.**

"The request path is: browser → Next.js proxy → FastAPI → LangGraph → SSE stream back. The proxy exists so the backend URL never appears in client-side JavaScript. The graph has six nodes with explicit conditional edges — every possible transition is visible in about 50 lines of graph.py."

---

### Step 7: Honest Self-Assessment (30 seconds)
**Say:** "I originally built five deliberate shortcuts to move fast — in-memory sessions, simulated streaming, localStorage auth, open CORS, and no rate limiting. Before this demo I fixed all five: Redis-backed session store, real OpenRouter token streaming via thread-local callback into an asyncio queue, server-side httpOnly cookie auth with HMAC-SHA256, restricted CORS, and slowapi rate limiting. The one genuine remaining item is switching the LLM HTTP client from urllib.request to aiohttp for fully async concurrency."

---

## If Something Breaks

### Backend doesn't start
- Check: is port 8000 already in use? `netstat -ano | findstr :8000` (Windows)
- Check: is `OPENROUTER_API_KEY` set in `.env`?
- Check: is the venv activated?

### `/debug` shows `llm.ok: false`
- OpenRouter API key is wrong or missing
- **Say:** "The LLM connectivity check is failing — let me verify the API key. In the meantime, the bot will fall back to rule-based classification and formatted chunk answers, so I can still demo the quote flow."

### `/debug` shows `knowledge_base.ok: false`
- Run `python rebuild_knowledge_base.py` in the backend directory
- **Say:** "The vector index needs to be rebuilt — this happens on first run. Takes about 30 seconds."

### Frontend shows blank screen / 404
- Is `npm run dev` running?
- Is it on port 3000?
- Hard refresh: Ctrl+Shift+R

### Bot gives wrong response mid-demo
- Don't panic. Say: "Let me check what happened here."
- Check the backend terminal — the logs show exactly what intent was classified and which node ran.
- **This shows debugging skills — interviewers value how you respond to failures, not just whether they happen.**

### The interruption demo doesn't work (bot doesn't re-ask the field)
- Make sure the question has a `?` in it — the deterministic classifier looks for `?` to detect questions during quote flow.
- If it still doesn't work, explain what *should* happen and point to `graph.py:52-55`.

---

## During Demo — Mental Model

| If asked about... | Refer to... |
|-------------------|-------------|
| State machine design | `graph.py:109-157` |
| Why LangGraph | "Explicit transitions, testable, auditable" |
| Mode switching | `graph.py:35-63` and the interrupt test |
| Intent classification | `router.py:39-90` (three layers) |
| Quote calculation | `quote_calculator.py` (deterministic formulas) |
| RAG retrieval | `vectorstore.py`, `rag.py` |
| Session persistence | `main.py` (_SessionStore) — Redis with in-memory fallback, TTL-backed |
| CORS | `main.py` (ALLOWED_ORIGINS env var) — fixed, no longer `allow_origins=["*"]` |
| Auth | `frontend/app/api/auth/` — httpOnly cookie, HMAC-SHA256, server-side env vars only |
| Rate limiting | `main.py` (slowapi) — 60/min chat, 20/min reset |
| Testing | `tests/test_backend_integration.py` — 34 tests, all passing |
| Streaming | Real OpenRouter token streaming via `streaming_context.py` thread-local callback → asyncio queue |

---

## After Demo — Common Follow-Up Areas

- **"Can I see the test suite?"** — Open `tests/test_backend_integration.py`. Show `test_mid_flow_question_preserves_quote_progress` and one validation test. 34 tests, all passing.
- **"Walk me through the validation code"** — Open `nodes/collect_details.py:243-339`. Show `_coerce_value` and `_clean_text_value`.
- **"How would you scale this?"** — Sessions already on Redis, rate limiting in place. Next: async LLM HTTP client (`aiohttp`) + horizontal Uvicorn workers behind a load balancer.
- **"What's the data model?"** — Open `state.py`. Show `ChatState` TypedDict. Explain each field.
- **"Show me the graph"** — Open `graph.py:109-157`. Walk through `_build_graph()`.
