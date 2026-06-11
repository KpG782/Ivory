# Research Prompt Pack — Find & Validate a Real-Data Problem to Rebrand ShieldBase Into

**Goal:** keep the ShieldBase *architecture* (deterministic state machine + RAG + stateful slot-filling + durable memory) and **rebrand it onto a real, validated, underserved problem with real open data** — so it becomes a standout portfolio project instead of a toy-data demo.

## How to use
1. Paste **Prompt 1** into a **web-enabled** model (ChatGPT Search/Deep Research, Claude with web search, Perplexity, or Gemini).
2. Edit every `[EDIT: …]` line first.
3. Read the 8–10 ranked candidates, pick **2–3** that excite you.
4. Run **Prompt 2** on each pick to validate the pain, find the datasets, and get a rebrand build-brief.
5. Bring the winner back to your engineer (me) to build on the existing skeleton.
6. If results feel generic, reply: *"too generic — only niche problems with quoted real complaints and named open datasets."*

---

## Prompt 1 — Discover & VALIDATE real problems (with evidence)

```
You are a senior product strategist + AI engineer. Use the web and cite sources throughout. Help me find a REAL, painful, underserved problem so I can rebrand an existing chatbot into a standout portfolio project. The problem MUST fit one specific architecture and MUST have real open data.

## The architecture I already built and will reuse (the problem must genuinely fit it)
A "controlled conversational assistant":
- DETERMINISTIC control flow: code/rules (a state machine) decide what happens next, NOT the LLM. Same input -> same path. Fully unit-testable.
- RAG knowledge layer: answers questions grounded in a real document corpus (no hallucination).
- STATEFUL slot-filling: collects structured inputs one at a time, validates each, then COMPUTES a result OR performs an action.
- Durable memory; the LLM ONLY writes natural-language text and never decides the flow.

## FIT TEST — only propose problems that pass ALL of these
1. KNOWLEDGE side: users ask questions a RAG corpus can answer.
2. TASK side: a structured, rule-driven job (collect inputs -> compute or act) with a VERIFIABLE/deterministic output.
3. Chat genuinely beats a plain web form or search bar here (mixed Q&A + task, branchy flow, or natural language is easier).
4. REAL or OPEN data exists for BOTH the knowledge corpus AND the task — you must be able to name an exact dataset/API with a URL.
5. Buildable by ONE developer in ~2–4 weeks.
6. The audience is real and underserved, and the PAIN IS VALIDATED — find evidence (Reddit, forums, app-store/G2 reviews, complaints, news) and QUOTE at least one real line with its source link per candidate.
7. NOT a saturated tutorial clone (avoid generic "customer support bot").
8. Avoid regulated ADVICE traps (medical/legal/financial advice) UNLESS framed as educational/non-advisory with explicit scope limits.

## Personalize to me
- Interests/domains: [EDIT: e.g., fintech, gov services, dev tools, local PH services, education]
- Audience/region I can reach for feedback: [EDIT: e.g., Philippines, students, small businesses]
- Roles I'm targeting: [EDIT: e.g., AI engineer / backend]
- Time budget: [EDIT: e.g., 3 weeks, evenings/weekends]

## Do this
1. Research real pain points that pass the FIT TEST. Work from actual complaints, not imagination.
2. Propose 8–10 candidates. RANK them by (pain severity × portfolio impressiveness × data availability × buildability).
3. For each candidate give a card:
   - Problem & who hurts (1–2 sentences)
   - PAIN EVIDENCE: 1 quoted real complaint + source link
   - Why chat beats a form/search here
   - RAG knowledge source (named corpus/docs + URL)
   - Deterministic task + the computed result or action, and how it is verified
   - Real task/reference dataset (named + URL) — easy / medium / hard to obtain
   - Optional tool/API integration + URL
   - The "wow" differentiator that makes it portfolio-worthy
   - Build difficulty (easy/med/hard) + the ONE hardest part
   - Top risk + how to de-risk
4. End with your TOP 3 picks, one line each on why, and what would turn each from "good demo" into "interview-winning."

Be specific and concrete. Prefer niche problems with real, accessible data over broad vague ones. Cite sources throughout.
```

---

## Prompt 2 — Deep-validate the pick, find the datasets, and produce a rebrand brief

```
I picked this problem: [PASTE the chosen candidate].

Act as a senior AI engineer + product owner. Use the web and cite sources. Pressure-test this problem and turn it into a buildable brief that REBRANDS an existing chatbot skeleton onto it.

## The skeleton I am reusing (keep the architecture, swap the domain)
- Deterministic state machine (rules drive flow; LLM only writes text)
- RAG over a real document corpus
- Stateful slot-filling: collect validated inputs -> compute/decide -> confirm
- Durable per-session memory (checkpointer)
What changes per project: the KNOWLEDGE corpus, the SLOTS collected, and the COMPUTE/ACTION step.

## 1. VALIDATE the pain
Find 3–5 real pieces of evidence (links + quotes) that people have this problem today and current solutions are weak. If the pain is weak, say so plainly and propose a sharper variant.

## 2. FIND THE DATA (do NOT call it "training data" — this architecture does not train a model)
Find the three data types, each with exact source name, URL, license, size, and whether it is clean or needs work; name a fallback for each if a source is unusable:
- RAG CORPUS: real documents the bot answers from (gov sites, official guides, open docs, Wikipedia). 3–5 sources, with rough page/word counts.
- TASK/REFERENCE DATA: the real numbers/rules/tables/catalog the deterministic compute needs (Kaggle / data.gov / official sources) — dataset name, columns, size, license, URL.
- EVAL SET: how to build 20–50 question->expected-answer pairs to test RAG quality (from which source), or an existing FAQ I can reuse.

## 3. SCOPE a v1 one dev can ship in [EDIT: 3 weeks]
- The 3–6 SLOTS to collect + a validation rule for each
- The deterministic COMPUTE/decision (exact logic, formula, or lookup) and how to TEST it
- The RAG questions it must answer + how to ground/cite answers
- One TOOL/action it performs (if any)
- An explicit OUT-of-scope list and a guardrail per state

## 4. REBRAND MAP
Map the new project onto the skeleton in a table: [skeleton piece] -> [keep as-is / what to swap]. Cover: state machine, slots, compute step, RAG corpus, memory, UI.

## 5. DIFFERENTIATION + RISKS + PITCH
- 2–3 features that make it stand out (evals, citations, interrupt-and-resume UX, real data)
- Top 3 risks (data, scope, accuracy) + how to de-risk each
- A README pitch: 3-sentence repo description + a 30-second demo script + a new product NAME idea

Be concrete and honest. Flag anything that would make this a weak portfolio piece.
```

---

## Quick tips
- Run Prompt 1 once, Prompt 2 on your top 2–3, then compare the briefs side by side.
- Favor a problem where the **task/reference dataset is real and clean** — that is what kills the "toy formula" criticism that a fake calculator invites.
- The strongest portfolio signal is **real data + evals + one genuine "wow"**, on top of the reliability the skeleton already gives you.
