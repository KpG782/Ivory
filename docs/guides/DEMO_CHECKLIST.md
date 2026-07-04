# Ivory — Pre-Demo Checklist

---

## 30 Minutes Before

### Backend
- [ ] `cd backend && .venv/Scripts/Activate.ps1` (Windows) or `source .venv/bin/activate` (Unix)
- [ ] `python -m uvicorn main:app --reload --port 8000`
- [ ] Wait for: `Knowledge base ready — backend=chroma chunks=54` in the terminal
- [ ] Hit `http://localhost:8000/health` — confirm `{"status": "ok"}`
- [ ] Hit `http://localhost:8000/debug` — confirm both `knowledge_base.ok: true` AND `llm.ok: true`
  - If `llm.ok: false`: check `OPENROUTER_API_KEY` in `.env` at repo root
  - If `knowledge_base.ok: false`: run `python rebuild_knowledge_base.py` from backend directory

### Frontend
- [ ] `cd frontend && npm run dev`
- [ ] Open `http://localhost:3000`
- [ ] Confirm login screen appears (not a blank page, not a 500)
- [ ] Log in with the credentials from `frontend/.env.local` (`AUTH_USERNAME` / `AUTH_PASSWORD`) — confirm chat screen loads
  - Use the eye icon button to toggle password visibility if needed
  - If `NEXT_PUBLIC_AUTH_DEMO_LOGIN=true` is set, the one-click "Enter demo workspace" button also works
  - Verify `GET /api/auth/check` returns `{"authenticated": true}` in DevTools → Network

### End-to-End Happy Path Test
- [ ] Send: "What does a routine cleaning include?" — confirm a grounded answer comes back
- [ ] Send: "I'd like to book a cleaning" — confirm bot asks "What's the patient's full name? (e.g. Maria Santos)"
- [ ] Interrupt: "What should I do about a toothache?" — confirm bot answers AND re-asks the name question
- [ ] Complete one full cleaning intake (Maria Santos, maria@example.com, 2024, insured, morning) — confirm the visit card appears
- [ ] Type "accept" — confirm the "Front desk actions:" dry-run block appears
- [ ] Type "restart" during a later intake — confirm bot resets to "Which type of visit would you like to set up"

### Environment Checks
- [ ] `.env` at repo root has `OPENROUTER_API_KEY=sk-or-...` (not empty)
- [ ] Integration keys (`AIRTABLE_API_KEY`, `CALCOM_API_KEY`, `RESEND_API_KEY`) unset unless you want live calls — unset means safe dry-run demo mode
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
"Ivory is an AI front desk for a dental clinic. It does two things in one session: answers dental questions using RAG over a curated knowledge base, and runs a structured multi-step visit intake workflow. The key design challenge — and what I want to show you — is that you can interrupt an intake, ask a side question, and the bot brings you back to exactly where you were."

**Credentials:** whatever is set in `frontend/.env.local` (`AUTH_USERNAME` / `AUTH_PASSWORD`). Use the eye icon to reveal the password if needed. Auth is a server-side httpOnly cookie — the password never reaches client-side JavaScript.

---

### Step 1: Knowledge Mode (60 seconds)
Type: `What does a routine cleaning include?`

**Say:** "The bot retrieves from 12 curated Markdown documents — grounded in public-domain NIDCR and CDC material — using ChromaDB and sentence-transformers. The answer is grounded — it cites sources and won't invent clinic details. I built a fallback: if the LLM is unavailable, it still answers using formatted text from the retrieved chunks."

**Point to sidebar:** "The status chip shows 'Knowledge mode'. The sidebar shows live backend state — this is purely rendering what the backend tells it."

---

### Step 2: Enter Intake Flow (30 seconds)
Type: `I'd like to book a cleaning`

**Say:** "The flow chip flips to 'cleaning intake · collect' and the status chip to 'Collecting details'. The backend is now running a state machine — a LangGraph StateGraph. It knows we're collecting cleaning intake fields, and it's tracking which field we're on."

**Point to:** The "What's the patient's full name? (e.g. Maria Santos)" response.

---

### Step 3: The Core Demo Moment — Interrupt and Resume (90 seconds)
Type: `What should I do about a toothache?` (with the `?`)

**Wait for response.**

**Say:** "This is the key behavior. The bot answered the dental question AND re-appended the field prompt at the end — 'Now, back to your cleaning visit intake — What's the patient's full name?' The intake state is completely preserved. The current field pointer, the mode, the collected data — all intact. Even a question that mentions a booking word, like 'How much does a whitening appointment cost?', is answered-then-resumed instead of hijacking the flow. The backend is the source of truth; the frontend just renders what it receives."

**Point to:** The two-part response (RAG answer + field re-prompt).

Type: `Maria Santos` — confirm it advances to "What email should we use for confirmations?"

---

### Step 4: Complete the Intake (2 minutes)
Answer remaining fields: `maria@example.com`, `2024`, `insured`, `morning`

**Say when the estimate appears:** "The estimate is deterministic — same inputs always produce the same output. The LLM never touches the number. I made this intentional: a patient-facing cost range has to be auditable and reproducible. There are multipliers for years since the last visit and insurance status — and for the other services, issue type, pain level, treatment, budget band, and timeline. Every estimate carries the disclaimer that it's educational, not a diagnosis or final price."

**Point to:** Visit card in sidebar.

---

### Step 5: Show Accept/Adjust/Restart (60 seconds)
Type: `accept`

**Say:** "Accept is the only place external integrations fire. Three front-desk actions run: an Airtable CRM lead, a Cal.com booking request, and a Resend confirmation email. With no API keys configured they run in dry-run mode — the deterministic 'Front desk actions' block you see — so the demo never touches the network. Each integration fails soft: an error becomes a line in this block, and the accept turn still succeeds. Adjust wipes collected data and sends you back to field 1, preserving the service type. Restart resets everything."

---

### Step 6: Architecture (if time allows — 90 seconds)
**Switch to ARCHITECTURE.md, Section 2 data flow diagram.**

"The request path is: browser → Next.js proxy → FastAPI → LangGraph → SSE stream back. The proxy exists so the backend URL never appears in client-side JavaScript, and it now requires the session cookie because intake carries PII. The graph has six nodes with explicit conditional edges — every possible transition is visible in `_build_graph()` in graph.py."

---

### Step 7: Honest Self-Assessment (30 seconds)
**Say:** "I originally built deliberate shortcuts to move fast — hand-rolled sessions, simulated streaming, localStorage auth, open CORS, and no rate limiting. Those are fixed: conversation state lives in the LangGraph checkpointer as the single source of truth, real OpenRouter token streaming via a thread-local callback into an asyncio queue, server-side httpOnly cookie auth with HMAC-SHA256, restricted CORS, and slowapi rate limiting. The genuine remaining items are a persistent checkpointer (state is in-memory today, lost on restart) and switching the LLM HTTP client from urllib.request to aiohttp for fully async concurrency."

---

## If Something Breaks

### Backend doesn't start
- Check: is port 8000 already in use? `netstat -ano | findstr :8000` (Windows)
- Check: is `OPENROUTER_API_KEY` set in `.env`?
- Check: is the venv activated?

### `/debug` shows `llm.ok: false`
- OpenRouter API key is wrong or missing
- **Say:** "The LLM connectivity check is failing — let me verify the API key. In the meantime, the bot will fall back to deterministic routing and formatted chunk answers, so I can still demo the intake flow."

### `/debug` shows `knowledge_base.ok: false`
- Run `python rebuild_knowledge_base.py` in the backend directory
- **Say:** "The vector index needs to be rebuilt — this happens on first run. Takes about 30 seconds."

### Frontend shows blank screen / 404
- Is `npm run dev` running?
- Is it on port 3000?
- Hard refresh: Ctrl+Shift+R

### Bot gives wrong response mid-demo
- Don't panic. Say: "Let me check what happened here."
- Check the backend terminal — the logs show exactly which route was chosen and which node ran.
- **This shows debugging skills — interviewers value how you respond to failures, not just whether they happen.**

### The interruption demo doesn't work (bot doesn't re-ask the field)
- Make sure the question has a `?` in it — the deterministic router looks for `?` to detect questions during an intake.
- If it still doesn't work, explain what *should* happen and point to `_rag_node` in `graph.py` (the resume append).

---

## During Demo — Mental Model

| If asked about... | Refer to... |
|-------------------|-------------|
| State machine design | `graph.py` — `_build_graph()` (six nodes, conditional edges) |
| Why LangGraph | "Explicit transitions, testable, auditable" |
| Mode switching | `graph.py` `_rag_node` (resume append) and the interrupt test |
| Routing decisions | `router.py` `decide()` — ordered rules P1–P7, no LLM |
| Visit estimation | `services/visit_estimator.py` (deterministic fee schedule) |
| RAG retrieval | `vectorstore.py`, `rag.py` |
| Session persistence | `graph.py` — LangGraph checkpointer keyed by `thread_id == session_id`; `main.py` SESSION_STORE is a read/write view over it |
| Front-desk integrations | `services/front_desk.py` + `airtable.py` / `calcom.py` / `resend_email.py` — accept-only, dry-run without keys |
| CORS | `main.py` (ALLOWED_ORIGINS env var) — fixed, no longer `allow_origins=["*"]` |
| Auth | `frontend/app/api/auth/` — httpOnly cookie, HMAC-SHA256, server-side env vars only; `/api/chat` and `/api/reset` require it |
| Rate limiting | `main.py` (slowapi) — 60/min chat, 20/min reset |
| Testing | `tests/` — 56 tests, all passing (45 integration + 7 contract scaffold) |
| Streaming | Real OpenRouter token streaming via `streaming_context.py` thread-local callback → asyncio queue |

---

## After Demo — Common Follow-Up Areas

- **"Can I see the test suite?"** — Open `tests/test_backend_integration.py`. Show `test_mid_flow_question_preserves_intake_progress` and one validation test. 56 tests across the suite, all passing.
- **"Walk me through the validation code"** — Open `nodes/collect_details.py`. Show `_coerce_value` and `_clean_text_value`.
- **"How would you scale this?"** — Rate limiting is in place and the checkpointer isolates session state. Next: a persistent checkpointer, an async LLM HTTP client (`aiohttp`), and horizontal Uvicorn workers behind a load balancer.
- **"What's the data model?"** — Open `state.py`. Show `ChatState` TypedDict. Explain each field.
- **"Show me the graph"** — Open `graph.py`. Walk through `_build_graph()`.
