# Real Open Data & APIs to Build an AI Front-Desk / Lead-Intake Agent for a Dental Clinic

> Deep-research output captured 2026-06-11. Decisions taken: **LangGraph deterministic engine = primary orchestrator; n8n = backup/alt only.** Tool stack: Airtable (CRM) + Cal.com (booking) + Resend (email). RAG corpus: NIDCR + CDC (public domain). **Never ingest ADA / MouthHealthy.org.**

## TL;DR
- **Build it dental.** Dental clinics are a genuinely hot 2026 vertical for AI front-desk/lead-intake agents. Cleanest, fastest STARTER SET: **NIDCR + CDC oral-health corpus** (public domain) → **Schema-Guided Dialogue "Services" domain** (dentist dialogues) → **Maven CRM Sales Opportunities CSV** (Public Domain) → **Airtable free CRM** → **Cal.com booking** → **Resend email**.
- The single biggest licensing trap is the ADA: **MouthHealthy.org / ADA.org content is fully copyrighted — "Reproduction or republication is strictly prohibited without prior written permission"** — do NOT ingest it. Use US-government public-domain sources (NIDCR/CDC) and UK NHS (Open Government Licence, attribution required) instead.
- All four integration APIs have working free tiers as of 2026 (Airtable free, Cal.com self-hostable AGPLv3 / free cloud, Resend 3,000 emails/month). This is a RETRIEVAL + slot-filling + tool-calling build, not model training.

## Key Findings
1. **Best RAG corpus:** US federal oral-health content (NIDCR + CDC) is explicitly public domain and clean enough to scrape in a weekend. NHS is reusable under OGL with attribution. **Avoid ADA/MouthHealthy** (all-rights-reserved).
2. **Best conversation dataset:** Google's **Schema-Guided Dialogue (SGD)** is the only mainstream open dataset whose "Services" domain explicitly includes **dentists**, with appointment-booking intents/slots — ideal for an eval set + demo intents. **Bitext** offers a Healthcare vertical and an Apache-2.0 generic customer-support set. MultiWOZ has no dental/medical-scheduling content.
3. **Best leads CSV:** **Maven Analytics CRM Sales Opportunities** (Public Domain) is the safest, cleanest seed; **Synthea** (Apache 2.0) is the best healthcare-flavored option.
4. **Integration APIs:** Airtable (free, PAT auth, `POST /v0/{baseId}/{table}`), Cal.com (free/self-host, `POST /v2/bookings`), Resend (free 3k/mo, `POST /emails`).

## 1. RAG CORPUS (ranked best-first)
- **#1 NIDCR — PUBLIC DOMAIN.** https://www.nidcr.nih.gov/health-info and /health-info/publications. "The materials are in the public domain." Dozens of patient-facing topic pages + PDFs. → Primary FAQ knowledge base; chunk + embed; cite source URL per chunk; pair with "educational, not medical advice."
- **#2 CDC Oral Health — PUBLIC DOMAIN.** https://www.cdc.gov/oral-health/index.html and /print-material/. Cavities, sealants, fluoridation, oral cancer, children's/adult oral health. → Supplements NIDCR.
- **#3 NHS dental content — OPEN GOVERNMENT LICENCE (attribution required).** https://www.nhs.uk. Attribution string: "Information from NHS Digital, licenced under the current version of the Open Government Licence." UK-specific charges — mark UK context. → "how booking/registration works," "what does a check-up cost."
- **#4 State/public dental-health agency pages** (e.g., Wisconsin DHS Oral Health, ODPHP). Mostly public domain; ingest only government-authored text (some pages embed ADA/AAP content). → Fills gaps.
- **DO NOT USE — ADA MouthHealthy.org / ADA.org (all rights reserved).** "Reproduction or republication is strictly prohibited without prior written permission." Use only as a human reference or with written permission.
- **Synthetic fallback (recommended layer):** generate a 30–60 entry **clinic-specific FAQ** with Claude (hours, services, new-patient process, insurance accepted, payment plans, parking, emergencies, cancellation policy) — the business-specific Q&As no open dataset contains. Ground medical claims in NIDCR/CDC with citations.

## 2. SUPPORT / CONVERSATION DATASETS (ranked best-first)
- **#1 Google Schema-Guided Dialogue (SGD / DSTC8) — best fit.** https://github.com/google-research-datasets/dstc8-schema-guided-dialogue. >20k task-oriented dialogues, 20 domains. The "Service" domain "includes salons, dentists, doctors etc." with appointment intents/slots. License: repo CC BY-SA 4.0 (confirm before redistribution). → Author 30–50 eval intents; model the booking slot schema on SGD's Services schema.
- **#2 Bitext Customer Support LLM dataset (+ Healthcare vertical).** https://huggingface.co/datasets/bitext/Bitext-customer-support-llm-chatbot-training-dataset. ~27k Q/A pairs, 27 intents. Generic set skews e-commerce; the **Healthcare/Insurance verticals** include `schedule_appointment`. License: generic set CDLA-Sharing-1.0 (attribution + share-alike). → Mine natural customer phrasings.
- **#3 MultiWOZ 2.2 — booking patterns, NOT dental.** ~10k dialogues, 7 domains; Apache 2.0. "hospital" domain is trivial; no dental. → Generic booking-style reference only.
- **#4 "Customer Support on Twitter" (Kaggle, thoughtvector).** 3M tweets/replies, 20 brands; noisy; verify license badge. → Lowest priority; general tone/escalation phrasing only.
- **Verdict:** SGD is the only one with explicit dentist + appointment-booking. RSiCS is relational/social, not scheduling — skip.

## 3. LEADS / CRM SAMPLE DATA (ranked best-first)
- **#1 Maven Analytics "CRM Sales Opportunities" — PUBLIC DOMAIN.** https://mavenanalytics.io/data-playground/crm-sales-opportunities. Four CSVs (accounts, products, sales_teams, sales_pipeline ~8,800 rows); columns include opportunity_id, account, deal_stage, engage_date, close_date, close_value. → Seed CRM + design scoring (deal_stage → lead status; close_value → budget band). Rename columns to patient-intake schema.
- **#2 Synthea synthetic patient data — APACHE 2.0.** https://github.com/synthetichealth/synthea. Synthetic, no PHI; configurable CSV. → Patient-flavored seed contacts.
- **#3 Kaggle "B2B SaaS using HubSpot" (sarahdaily) — synthetic, license unverified.** contacts/companies/deals/tickets CSVs map ~1:1 to CRM tables. Verify on-page.
- **#4 Kaggle "Sample Leads" / "sql-crm-example-data" — license unverified.**
- **Synthetic fallback (recommended):** generate 50–200 fake dental leads with Python `faker` (name, email, phone, reason_for_visit ∈ {cleaning, emergency, cosmetic, implant consult}, insurance, preferred_time, budget_band, source). Perfectly-fit columns, unambiguously license-free.

## 4. INTEGRATION APIs (best-first within each role)
- **CRM — #1 Airtable (free).** Docs: https://airtable.com/developers/web/api. Free: 1,000 records/base; 5 req/s per base (PAT up to 50 req/s). Auth: Personal Access Token (Bearer), scope `data.records:write`. Create: `POST https://api.airtable.com/v0/{baseId}/{tableIdOrName}`. Alt: HubSpot free (`POST /crm/v3/objects/contacts`) for "real CRM" feel; Google Sheets (append row) as simplest fallback.
- **Booking — #1 Cal.com.** Docs: https://cal.com/docs/api-reference/v2/bookings/create-a-booking. Free cloud / AGPLv3 self-host. Auth: `cal_`-prefixed API key (Bearer); `cal-api-version` header required. Book: `POST https://api.cal.com/v2/bookings` (eventTypeId, start UTC ISO-8601, attendee name/email/timeZone). Fires `BOOKING_CREATED` webhook. Alt: Google Calendar `events.insert` + `freebusy.query`.
- **Email — #1 Resend.** Docs: https://resend.com/docs. Free: 3,000/mo, 100/day, 1 domain, 30-day logs; 5 req/s. Auth: API key (Bearer). Send: `POST https://api.resend.com/emails`. Alt: Gmail API `users.messages.send`.

## Recommended STARTER SET
- **Corpus:** NIDCR + CDC (public domain) + a Claude-generated clinic FAQ (~50 entries).
- **Conversation dataset:** SGD "Services" (dentist) dialogues → eval set + slot schema.
- **Leads CSV:** Maven CRM Sales Opportunities (Public Domain) or `faker`-generated dental leads.
- **CRM:** Airtable free. **Booking:** Cal.com (self-host AGPLv3). **Email:** Resend free.
- **Demo flow:** FAQ answered from NIDCR/CDC *with citation* → slot-fill (name/email/need/budget/timeline) on an SGD-modeled schema → write lead to Airtable (visible live) → book via Cal.com → confirm via Resend. LLM only writes text; deterministic code controls flow + guardrails.

## Build cadence (suggested)
1. **Weekend 1:** scrape ~30–50 NIDCR+CDC pages (respect robots.txt), chunk, embed; add Claude clinic FAQ; retrieval with citations. *Benchmark:* ≥90% of eval questions return a correctly-cited chunk.
2. **Weekend 2:** deterministic slot-filling (validate each step) on an SGD-modeled schema; Airtable create-record tool-call. *Benchmark:* a test lead lands in Airtable with all slots validated.
3. **Weekend 3:** Cal.com booking + Resend confirmation behind deterministic guards; build the 30–50 item eval set. *Benchmark:* end-to-end demo passes ≥95% of scripted runs.

## Caveats
- **ADA/MouthHealthy off-limits** (all rights reserved). Most important licensing caveat.
- **NHS requires OGL attribution** and is UK-specific.
- **SGD** distributed "AS IS"; confirm CC BY-SA before redistribution.
- **Bitext generic = CDLA-Sharing-1.0**; use the Healthcare vertical for true fit.
- **Kaggle leads CSV licenses unverified** — prefer Maven (PD) or Synthea (Apache-2.0) or `faker`.
- **API free tiers change** — verify at signup.
- **Always** show "educational information, not medical advice" — health content involved.
- This architecture **retrieves, slot-fills, and calls tools** — none of these are "training data."
