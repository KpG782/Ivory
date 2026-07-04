# Ivory — Plain English Explanation

This is a simplified version of the three technical docs (ARCHITECTURE.md, QA_PREP.md, DEMO_CHECKLIST.md).
No jargon. Read this first if you want the big picture before diving into the technical docs.

---

## What is Ivory?

Ivory is a **chatbot that works as the front desk for a dental clinic**. It does two things:

1. **Answers questions** — "What does a routine cleaning include?" → it looks it up and gives you a grounded answer.
2. **Sets up your visit** — "I'd like to book a cleaning" → it asks you step-by-step questions (name, email, when you last visited, etc.) and gives you an estimated cost range for the visit.

The trick is it can do both **in the same conversation without losing your place**. You can be halfway through booking a cleaning, ask a random question about toothaches, get the answer, and the bot picks up exactly where it left off.

---

## How It's Built (The Big Picture)

Think of it like a **restaurant order system**:

- **The menu** = the knowledge base (12 documents about the clinic, its services, and dental health)
- **The waiter** = the chatbot frontend you see in the browser
- **The kitchen** = the FastAPI backend that processes everything
- **The chef's workflow** = LangGraph (a state machine that tracks where you are in the process)
- **The specialist cook** = the AI (via OpenRouter) that writes natural-language answers

When you type a message:
1. Your browser sends it to the Next.js server (a middleman)
2. The middleman passes it to the Python backend
3. The backend figures out what you want (question? starting a booking? answering a booking field?)
4. It runs the right logic and streams the response back word by word
5. Your screen updates in real time as words arrive

And when you finally say "accept", the bot does three front-desk chores: saves you as a lead in the clinic's CRM (Airtable), requests an appointment slot (Cal.com), and drafts a confirmation email (Resend). If those services aren't configured, it safely pretends — "demo mode" — and tells you so.

---

## The Five Big Problems That Were Fixed

The original version had five shortcuts that were fine for a demo but not good enough for real use. All five have been addressed:

### 1. Two Competing Notebooks for Conversations (FIXED)
**Before:** The app kept conversation state in its own hand-rolled dictionary *and* in the workflow engine, and the two could drift apart.

**After:** There is now exactly **one source of truth** — the workflow engine's built-in checkpointer stores each conversation, keyed by your session. Note: it's still in the server's memory, so a restart loses active chats; plugging in a database-backed checkpointer is the known next step for production.

**Layman version:** Before, two people took notes on the same meeting and sometimes disagreed. Now there's one official notebook.

---

### 2. Any Website Could Talk to the Backend (FIXED)
**Before:** CORS was set to `allow_origins=["*"]` — any website on the internet could send requests directly to the backend.

**After:** Only allowed origins can talk to the backend (set via the `ALLOWED_ORIGINS` environment variable, defaulting to localhost for development).

**Layman version:** Before, the back door was unlocked. Now it only opens for the right address.

---

### 3. Streaming Was Fake (FIXED)
**Before:** The AI generated the whole response at once, then the code split it into words and sent them one by one with a small delay — fake typing effect.

**After:** The AI now streams tokens (word pieces) **as they're generated**. Real-time. You see words appear as the AI produces them, not after it's done thinking.

**Layman version:** Before, it was like the AI wrote the whole answer, then someone typed it in for you. Now you're watching it write in real time.

---

### 4. The Password Was Visible in the Browser (FIXED)
**Before:** The login password was stored in a JavaScript variable that anyone could find by opening browser DevTools. It was literally in the client-side code.

**After:** Login now works like a proper website. You type your username and password, it gets sent to the server, the server checks it privately, and if it's correct it sets a secure cookie. The password never touches client-side JavaScript. And because booking a visit involves personal details, the chat itself now also requires that cookie.

**Layman version:** Before, the password was written on a sticky note on the front door. Now it's locked in a safe inside the building.

---

### 5. No Limits on Requests (FIXED)
**Before:** Anyone could spam the chatbot with thousands of messages per minute, overloading the server.

**After:** Rate limiting is enforced — 60 messages per minute per IP on the chat endpoint, 20 per minute on the reset endpoint.

**Layman version:** Before, anyone could walk in and order 10,000 things at once. Now there's a bouncer.

---

## How the Chatbot Decides What You Want

The bot uses a **fixed rulebook** — not the AI — to figure out what your message is. Think of a receptionist with a laminated checklist, read top to bottom:

1. Did you say "restart" mid-booking? Start over.
2. Are you mid-booking and asked a question (with a `?`)? Answer it, then return to the booking — even if the question mentions the word "appointment".
3. Did you use a booking word like "book" or "schedule"? Start (or switch) a booking.
4. Is the bot waiting on a specific answer from you? Treat your message as that answer and check it.
5. Otherwise, it's a question for the knowledge base.

The same message in the same situation always gets the same decision. This matters because AI models often misclassify short answers like "morning" or "2024" as questions. Here the AI is never asked to make that call — it only writes the wording of knowledge answers.

---

## How Visit Estimates Work

When you want to set up a visit:
- The bot knows which service you want (cleaning, emergency, or cosmetic)
- It asks you one field at a time (name → email → last visit year → insurance → preferred time, for a cleaning)
- Each answer is validated immediately: wrong type, out of range, or nonsense? It re-asks. ("i like dogs" does not pass as a name, and pain level -2 is rejected.)
- Once all fields are collected, a **deterministic calculator** computes a cost range using a fixed fee schedule

The key word is **deterministic** — same inputs always produce the same output. The AI never touches the price range. This is intentional: a cost estimate a patient will see has to be auditable and reproducible. Every estimate also says clearly: it's educational, not a diagnosis or a final price.

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
2. You type the username and password that were configured for the demo (they live in a private server file, `frontend/.env.local`) and click Login (use the eye icon to show the password)
3. The Next.js server checks your credentials against its private environment variables
4. If correct, it sets a **secure cookie** on your browser (invisible, tamper-proof, expires in 24 hours)
5. Every page load checks that cookie — if it's valid, you're in; if not, back to login
6. Logout clears the cookie

The password is only ever checked server-side. It never appears in browser code.

---

## Common Interview Questions — Plain English Answers

**"Walk me through what happens when I type a message."**
> You type → browser sends it to Next.js → Next.js checks your login cookie and passes it to FastAPI → FastAPI loads your conversation from the checkpointer, decides what your message is using the rulebook, runs the right logic → streams the response back word by word → your screen updates in real time.

**"Why LangGraph?"**
> The booking workflow is like a flowchart with many possible states (asking for your name, asking for a pain level, waiting for confirmation, etc.). LangGraph lets you define all those states and transitions explicitly in code — like a real flowchart — instead of a tangled pile of if/else statements. It also remembers each conversation for you.

**"How does mid-booking interruption work?"**
> When you ask a question during a booking, the bot answers it using the knowledge base, then automatically re-asks the field it was waiting on. Your booking progress is completely preserved because the backend tracks exactly which field you're on.

**"What corners did you cut?"**
> Originally: a hand-rolled session store, fake streaming, password in client code, open CORS, no rate limiting. All five have been addressed. The genuine remaining items are storing sessions in a real database (they're in memory today) and making the AI's HTTP calls async.

**"How would this scale?"**
> Rate limiting is in. The booking flow never calls the AI, so it's cheap. The two bottlenecks are: sessions live in memory (fix: a database-backed checkpointer), and each AI call holds a thread for 1-3 seconds (fix: async HTTP). Both are known, scoped next steps.

**"What happens if the AI goes down?"**
> Nothing breaks. The rulebook doesn't use the AI at all, so bookings work perfectly. For knowledge questions, the bot falls back to showing formatted text from the retrieved documents — no AI needed.

**"What happens when I accept a visit?"**
> Three front-desk actions run: a lead is saved to the clinic CRM, an appointment request goes to the scheduling system, and a confirmation email is drafted. If those services aren't set up, each one honestly reports "demo mode" instead — and if one fails, the bot tells you in the same list rather than crashing.

---

## Pre-Demo Checklist — Plain English

### 30 Minutes Before
- Start the backend Python server (`uvicorn main:app --reload --port 8000`)
- Wait for it to say the knowledge base is ready (12 documents, 54 chunks)
- Check `localhost:8000/debug` — both `knowledge_base: ok` and `llm: ok` should be green
- Start the frontend (`npm run dev` in the frontend folder)
- Open `localhost:3000`, log in with your configured demo credentials
- Do a quick end-to-end test: ask a dental question, start a booking, interrupt with a question, complete the booking, accept it

### During the Demo
- **Start with a knowledge question** — shows RAG working
- **Start a booking** — shows the state machine kicking in
- **Interrupt with a question mid-booking** — this is the key moment, the bot answers AND comes back to the booking
- **Complete the booking** — show the visit card with the estimate range
- **Accept it** — show the "Front desk actions" list running in demo mode
- **Closing script:** "I originally had 5 shortcuts — a hand-rolled session store, fake streaming, password in client code, open CORS, no rate limiting. All five are fixed. What remains is a database-backed session store and making the AI HTTP calls fully async."

### If Something Breaks
- Backend won't start → check if port 8000 is already in use
- `llm: false` on `/debug` → OpenRouter API key is wrong or missing
- `knowledge_base: false` → run `python rebuild_knowledge_base.py`
- Bot gives weird answer mid-demo → check the backend terminal logs, explain what *should* have happened

---

## Files to Read (Technical Versions)

| File | What it covers |
|------|----------------|
| `ARCHITECTURE.md` | Full system design, data flow diagram, every component, all the fixes with code references |
| `QA_PREP.md` | Every likely interview question with a strong answer, code references, and "gotcha to avoid" for each |
| `DEMO_CHECKLIST.md` | Step-by-step demo script, login flow, what to say at each step, what to do if things break |
