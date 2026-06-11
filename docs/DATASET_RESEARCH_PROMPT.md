# Deep-Research Prompt — Find the Best Data for a RAG + Slot-Filling + Tool-Calling Agent

> Reusable. "Dataset" here means FOUR things — this architecture **retrieves, slot-fills, and calls tools**; it does not train a model.
> 1. RAG corpus (answer from) · 2. Support/conversation datasets (eval + realistic intents) · 3. Leads sample data (seed CRM + design scoring) · 4. Integration APIs (write to).

Paste into a web-enabled / deep-research model. Edit the `[EDIT: …]` lines first.

```
You are a senior AI engineer + data researcher. Use the web and cite every source with a URL. Find me the best REAL, OPEN datasets and APIs to build and demo a specific chatbot. Do NOT call anything "training data" — this architecture does not train a model; it RETRIEVES from a corpus, COLLECTS slots, and CALLS tools.

## What I'm building (match the data to THIS)
An "AI Front-Desk / Lead-Intake Agent" for a [EDIT: service vertical — e.g., dental clinic / home-services contractor / digital marketing agency / B2B SaaS]:
- RAG: answers FAQs from the business's documents, WITH citations.
- Slot-filling: qualifies a visitor (name, email, need, budget, timeline), validated each step.
- Tool-calling: writes the qualified lead to a CRM, and optionally books a call + sends a confirmation email.
- Deterministic control flow + guardrails; the LLM only writes text, never decides the flow.
Region/language: [EDIT: e.g., English; or English + Taglish for PH].
Time budget: ~2–3 weeks, solo. Prefer data that's clean enough to use in a weekend.

## Find me FOUR things. For EACH item give: exact name, URL, license, size/coverage, format, and HOW I'd use it. Flag a fallback if a source is gated or scraping-restricted.
1. RAG CORPUS — real help-center / FAQ / knowledge-base / docs content for the chosen vertical that I can ingest as the agent's knowledge base (open, or public + scrapable with permission). 3–5 options, with rough page/word counts and license.
2. SUPPORT / CONVERSATION DATASETS — real customer-support or task-oriented dialogue/intent datasets to (a) build a 30–50 item EVAL set and (b) make my demo intents realistic. Give dataset name, #examples, intents/domains covered, and license. Consider and verify: Bitext customer-support datasets, MultiWOZ, Google Schema-Guided Dialogue (SGD), "Customer Support on Twitter" (Kaggle), Relational Strategies in Customer Service (RSiCS) — tell me which actually fit my vertical.
3. LEADS / CRM SAMPLE DATA — a realistic sample leads/contacts dataset (CSV) to seed the CRM and to design the qualification scoring rules. Source + columns + license.
4. INTEGRATION APIs — the best FREE-tier tools to write to, plus their docs: a CRM (Airtable / Google Sheets / HubSpot free), a booking API (Google Calendar / Cal.com), and an email API (Resend / Gmail). For each: free-tier limits, auth method, and the ONE endpoint I need to create a record / book a slot / send a mail.

## Rank everything by
- Truly open/free license (state it) and realistic for my vertical.
- Small/clean enough to ingest in a weekend.
- Recent / maintained; in my language.
- Easy to DEMO live (reviewer sees real content, a real lead landing in the CRM, a real booking).

## Output
- A ranked shortlist per category (best first), with the fields above.
- ONE recommended "STARTER SET": exactly one corpus + one conversation dataset + one leads CSV + one CRM + one booking API + one email API that work well together for a 2–3 week build — and why.
- Any licensing/scraping caveats I must respect.
Cite every source with a URL. If a category has weak options, say so honestly and suggest a synthetic fallback.
```

## Known-good starter datasets (head start)
- **Google Schema-Guided Dialogue (SGD)** — task-oriented dialogues incl. a "Services/dentist" domain with booking intents. Best for eval set + slot schema.
- **MultiWOZ 2.2** (Apache-2.0) — generic booking-style dialogues (no dental).
- **Bitext customer-support dataset** (CDLA-Sharing-1.0; Healthcare vertical available).
- **Maven Analytics "CRM Sales Opportunities"** (Public Domain) / **Synthea** (Apache-2.0) — seed leads.
- Corpus: pick one real public help center for the vertical (a clinic FAQ, a SaaS's docs) = your RAG corpus.
