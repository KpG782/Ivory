# Ivory — Plain English Explanation

This is a simplified version of the three technical docs (ARCHITECTURE.md, QA_PREP.md, DEMO_CHECKLIST.md).
No jargon. Read this first if you want the big picture before diving into the technical docs.

---

## What is Ivory?

Ivory is a **chatbot for an insurance company**. It does two things:

1. **Answers questions** — "What does comprehensive coverage include?" → it looks it up and gives you a grounded answer.
2. **Gets you a quote** — "I want auto insurance" → it asks you step-by-step questions (car year, make, age, etc.) and spits out a price.

The trick is it can do both **in the same conversation without losing your place**. You can be halfway through getting a car insurance quote, ask a random question about what "liability" means, get the answer, and the bot picks up exactly where it left off.

---

## How It's Built (The Big Picture)

Think of it like a **restaurant order system**:

- **The menu** = the knowledge base (12 documents about insurance products, claims, FAQs)
- **The waiter** = the chatbot frontend you see in the browser
- **The kitchen** = the FastAPI backend that processes everything
- **The chef's workflow** = LangGraph (a state machine that tracks where you are in the process)
- **The specialist cook** = the AI (OpenRouter / Llama 3.1 8B) that generates natural language answers

When you type a message:
1. Your browser sends it to the Next.js server (a middleman)
2. The middleman passes it to the Python backend
3. The backend figures out what you want (question? starting a quote? answering a quote field?)
4. It runs the right logic and streams the response back word by word
5. Your screen updates in real time as words arrive

---

## The Five Big Problems That Were Fixed

The original version had five shortcuts that were fine for a demo but not good enough for real use. All five have been fixed:

### 1. Sessions Lost on Restart (FIXED)
**Before:** All active chat sessions were stored in RAM. If the server restarted, every conversation vanished.

**After:** Sessions are now stored in **Redis** (a fast external database). Restart the server — sessions survive. No Redis available? It falls back to memory automatically.

**Layman version:** Before, it was like writing notes on a whiteboard — erase it and they're gone. Now it's like writing in a notebook — restart doesn't lose anything.

---

### 2. Any Website Could Talk to the Backend (FIXED)
**Before:** CORS was set to `allow_origins=["*"]` — any website on the internet could send requests directly to the backend.

**After:** Only allowed origins can talk to the backend (set via the `ALLOWED_ORIGINS` environment variable, defaulting to `http://localhost:3000`).

**Layman version:** Before, the back door was unlocked. Now it only opens for the right address.

---

### 3. Streaming Was Fake (FIXED)
**Before:** The AI generated the whole response at once, then the code split it into words and sent them one by one with a small delay — fake typing effect.

**After:** The AI now streams tokens (word pieces) **as they're generated**. Real-time. You see words appear as the AI produces them, not after it's done thinking.

**Layman version:** Before, it was like the AI wrote the whole answer, then someone typed it in for you. Now you're watching it write in real time.

---

### 4. The Password Was Visible in the Browser (FIXED)
**Before:** The login password was stored in a JavaScript variable that anyone could find by opening browser DevTools. It was literally in the client-side code.

**After:** Login now works like a proper website. You type your username and password, it gets sent to the server, the server checks it privately, and if it's correct it sets a secure cookie. The password never touches client-side JavaScript.

**Layman version:** Before, the password was written on a sticky note on the front door. Now it's locked in a safe inside the building.

---

### 5. No Limits on Requests (FIXED)
**Before:** Anyone could spam the chatbot with thousands of messages per minute, overloading the server.

**After:** Rate limiting is enforced — 60 messages per minute per IP on the chat endpoint, 20 per minute on the reset endpoint.

**Layman version:** Before, anyone could walk in and order 10,000 things at once. Now there's a bouncer.

---

## How the Chatbot Decides What You Want

The bot uses a **3-layer system** to figure out your intent. Think of it as three people in a room:

1. **The rules person** — checks obvious cases first. "Are you mid-quote and gave a short answer with no question mark? That's a field answer, done." No AI needed.
2. **The AI** — if the rules person isn't sure, they ask the AI to classify: is this a question, a quote request, or a field answer?
3. **The backup rules person** — if the AI fails or gives a bad answer, falls back to keyword matching.

This matters because small AI models often misclassify short answers like "home" or "2019" as questions. The rules person on layer 1 catches those before the AI even sees them.

---

## How Quoting Works

When you want a quote:
- The bot knows which insurance type you want (auto, home, life)
- It asks you one field at a time (year → make → model → driver age → etc.)
- Each answer is validated immediately: wrong type, out of range, or nonsense? It re-asks.
- Once all fields are collected, a **deterministic calculator** computes the premium using fixed formulas

The key word is **deterministic** — same inputs always produce the same output. The AI never touches the price number. This is intentional: insurance prices have to be auditable and reproducible.

---

## How Real Streaming Works

This is the most technically interesting fix. Here's the simplified version:

- The AI generates text on a separate thread (think: a back-room worker)
- The web server needs to receive those tokens and immediately send them to your browser
- Problem: Python threads and async web servers don't naturally talk to each other

The solution: a "pass-it-through" mechanism using a thread-local callback and an async queue:
1. Back-room worker generates a token → drops it into a queue
2. Web server picks it up from the queue → immediately streams it to your browser
3. A special signal at the end says "I'm done"

The browser gets words as they arrive. No waiting for the full response.

---

## How Login / Auth Works

1. You go to `localhost:3000` — if you're not logged in, you see a login screen
2. You type `admin` / `ivory123` and click Login (use the eye icon to show the password)
3. The Next.js server checks your credentials against its private environment variables
4. If correct, it sets a **secure cookie** on your browser (invisible, tamper-proof, expires in 24 hours)
5. Every page load checks that cookie — if it's valid, you're in; if not, back to login
6. Logout clears the cookie

The password is only ever checked server-side. It never appears in browser code.

---

## Common Interview Questions — Plain English Answers

**"Walk me through what happens when I type a message."**
> You type → browser sends it to Next.js → Next.js passes it to FastAPI → FastAPI looks up your conversation history, figures out your intent, runs the right logic → streams the response back word by word → your screen updates in real time.

**"Why LangGraph?"**
> The quote workflow is like a flowchart with many possible states (asking for car year, asking for driver age, waiting for confirmation, etc.). LangGraph lets you define all those states and transitions explicitly in code — like a real flowchart — instead of a tangled pile of if/else statements.

**"How does mid-quote interruption work?"**
> When you ask a question during a quote, the bot answers it using the knowledge base, then automatically re-asks the field it was waiting on. Your quote progress is completely preserved because the backend tracks exactly which field you're on.

**"What corners did you cut?"**
> Originally: in-memory sessions, fake streaming, password in client code, open CORS, no rate limiting. All five have been fixed. The one genuine remaining item is switching the AI's HTTP calls from synchronous to async — that's the next performance improvement.

**"How would this scale?"**
> Sessions are already in Redis (horizontal scaling unlocked). Rate limiting is in. The next bottleneck is the AI HTTP client — it's synchronous, meaning each AI call holds a thread for 1-3 seconds. Switching to async HTTP would let many more users be served simultaneously.

**"What happens if the AI goes down?"**
> The bot falls back to rule-based intent classification (it still routes correctly, just less nuanced). For knowledge questions, it falls back to showing formatted text from retrieved documents — no AI needed. Quote flows work perfectly since the calculator doesn't use the AI at all.

---

## Pre-Demo Checklist — Plain English

### 30 Minutes Before
- Start the backend Python server (`uvicorn main:app --reload --port 8000`)
- Wait for it to say the knowledge base is ready
- Check `localhost:8000/debug` — both `knowledge_base: ok` and `llm: ok` should be green
- Start the frontend (`npm run dev` in the frontend folder)
- Open `localhost:3000`, log in with `admin` / `ivory123`
- Do a quick end-to-end test: ask a knowledge question, start a quote, interrupt with a question, complete the quote

### During the Demo
- **Start with a knowledge question** — shows RAG working
- **Start a quote** — shows the state machine kicking in
- **Interrupt with a question mid-quote** — this is the key moment, the bot answers AND comes back to the quote
- **Complete the quote** — show the quote card
- **Step 7 script:** "I originally had 5 shortcuts — in-memory sessions, fake streaming, password in client code, open CORS, no rate limiting. All five are fixed. What remains is making the AI HTTP calls fully async."

### If Something Breaks
- Backend won't start → check if port 8000 is already in use
- `llm: false` on `/debug` → OpenRouter API key is wrong or missing
- `knowledge_base: false` → run `python rebuild_knowledge_base.py`
- Bot gives weird answer mid-demo → check the backend terminal logs, explain what *should* have happened

---

## Files to Read (Technical Versions)

| File | What it covers |
|------|----------------|
| `ARCHITECTURE.md` | Full system design, data flow diagram, every component, all 5 fixes with code references |
| `QA_PREP.md` | Every likely interview question with a strong answer, code line references, and "gotcha to avoid" for each |
| `DEMO_CHECKLIST.md` | Step-by-step demo script, login flow, what to say at each step, what to do if things break |
