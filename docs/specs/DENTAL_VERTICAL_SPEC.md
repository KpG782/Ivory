# Ivory Dental Vertical — Conversion Spec (binding)

> Status: **authoritative implementation spec** for converting the insurance
> take-home vertical into the Ivory dental front-desk vertical, per the locked
> decisions in `docs/DATASET_RESEARCH_DENTAL.md` (NIDCR/CDC corpus, Airtable CRM,
> Cal.com booking, Resend email; never ADA content).
>
> Architecture is unchanged: **Deterministic Orchestrator + RAG + Stateful
> Slot-Filling.** The LLM only writes prose; deterministic Python owns control
> flow, validation, estimates, and integrations.

## 0. Invariants that must survive the conversion

- Backend state is the source of truth; the frontend renders it.
- Business results (visit estimates) are deterministic, never LLM-generated.
- Invalid field input never advances the flow step.
- Mid-flow knowledge questions never clear `collected_data`; the pending-field
  re-prompt is appended after the answer.
- Flow-start intents are never downgraded to generic RAG; bare field replies
  (e.g. `2024`) stay in the transactional branch.
- Compact multi-field replies fill several fields in one turn.
- `accept`, `adjust`, `restart` work after a result exists.
- Endpoints stay `/chat` (SSE), `/reset`, `/health`; SSE event names unchanged.

## 1. Vocabulary renames (global, all layers)

| Insurance term | Dental term |
|---|---|
| `insurance_type` | `service_type` |
| `quote_step` | `intake_step` |
| `quote_result` | `visit_estimate` |
| `has_quote_result` (snapshot) | `has_visit_estimate` |
| "quote" (copy) | "visit estimate" / "appointment request" |
| `QuoteCard` component | `VisitCard` component (file renamed) |
| products `auto` / `home` / `life` | services `cleaning` / `emergency` / `cosmetic` |

Steps keep their names: `identify → collect_details → validate → confirm`.
Modes keep their names: `conversational` / `transactional`.

## 2. Services and slot schemas (SGD "Services"-modeled)

### 2.1 `cleaning` — routine exam & cleaning
| Slot | Type | Validation |
|---|---|---|
| `patient_name` | free text | ≥2 alphabetic tokens; reject conversational fillers (`i like…`, `i want…`, `hello…`) — this also closes the old "i like dogs" location bug class |
| `contact_email` | free text | must match a pragmatic email regex (`x@y.z`) |
| `last_visit_year` | int | 1900 < year ≤ current year (future years rejected — mirrors old `vehicle_year` guard) |
| `insurance_status` | enum | `insured`, `self_pay` |
| `preferred_time` | enum | `morning`, `afternoon`, `evening` |

### 2.2 `emergency` — urgent visit
| Slot | Type | Validation |
|---|---|---|
| `patient_name` | free text | same rule as above |
| `contact_phone` | free text | ≥7 digits after stripping separators |
| `issue_type` | enum | `toothache`, `chipped_tooth`, `swelling`, `lost_filling` |
| `pain_level` | int | 0–10 inclusive (negative and >10 rejected — mirrors old `accidents_last_5yr` guard) |
| `insurance_status` | enum | `insured`, `self_pay` |

### 2.3 `cosmetic` — cosmetic consultation
| Slot | Type | Validation |
|---|---|---|
| `patient_name` | free text | same rule |
| `contact_email` | free text | email regex |
| `treatment` | enum | `whitening`, `veneers`, `aligners`, `bonding` |
| `budget_band` | enum | `basic`, `standard`, `premium` |
| `timeline` | enum | `asap`, `this_month`, `flexible` |

Compact input example that must fill multiple fields in order:
`Ken Garcia, ken@example.com, 2024, insured, morning` (cleaning).

## 3. Deterministic visit estimator (`services/visit_estimator.py`)

Replaces `services/quote_calculator.py` (file renamed; same public shape:
`validate_visit_inputs(service_type, data) -> ValidationResult` and
`estimate_visit(service_type, data) -> dict`).

Output object (rendered by `VisitCard`; exact keys):

```json
{
  "service_type": "cleaning",
  "estimate_low": 95.0,
  "estimate_high": 180.0,
  "currency": "USD",
  "summary": "Routine exam & cleaning for Ken Garcia",
  "...echoed validated slots per service..."
}
```

Fee schedule (deterministic factors, same style as the old premium math):

- **cleaning**: base 140 (exam + cleaning). Years since last visit `y = current_year - last_visit_year`; factor `1.0 + min(y, 10) * 0.06`. `insured` multiplies patient-responsibility estimate by `0.45`. Range = `round(base*factors*0.85, 2)` … `round(base*factors*1.25, 2)`.
- **emergency**: base 110 (urgent exam + X-ray). Issue factor: toothache 1.35, chipped_tooth 1.2, swelling 1.5, lost_filling 0.95. Pain factor `1.0 + pain_level * 0.02`. `insured` → 0.5 multiplier. Same ±range shape.
- **cosmetic**: treatment base: whitening 350, bonding 450, veneers 1400, aligners 3600. Budget factor basic 0.9 / standard 1.0 / premium 1.3; timeline asap 1.1 / this_month 1.0 / flexible 0.95. Insurance never applies (cosmetic = self-pay); range ±15%.

All estimates carry copy: educational estimate, not a diagnosis or final price.

## 4. Front-desk integrations (fire on `accept`)

New `backend/services/front_desk.py` orchestrating three thin clients (all
stdlib `urllib.request`, matching `services/llm.py` style; no new deps):

- `services/airtable.py` — `create_lead(fields) -> IntegrationResult`; `POST https://api.airtable.com/v0/{base}/{table}`, PAT bearer `AIRTABLE_API_KEY`, env `AIRTABLE_BASE_ID`, `AIRTABLE_TABLE_NAME` (default `Leads`).
- `services/calcom.py` — `create_booking(...) -> IntegrationResult`; `POST https://api.cal.com/v2/bookings` with `cal-api-version: 2024-08-13` header, env `CALCOM_API_KEY`, `CALCOM_EVENT_TYPE_ID`. Start time is computed deterministically: next business day at 09:00/13:00/17:00 UTC for morning/afternoon/evening (emergency/cosmetic default morning).
- `services/resend_email.py` — `send_confirmation(...) -> IntegrationResult`; `POST https://api.resend.com/emails`, env `RESEND_API_KEY`, `RESEND_FROM` (default `Ivory <onboarding@resend.dev>`). Emergency flow collects phone, not email → email is skipped with status `skipped`.

`IntegrationResult = {name, status, detail}` with `status ∈ {"created", "sent", "dry_run", "skipped", "error"}`.

**Dry-run rule (critical):** if an integration's env keys are missing, it never
touches the network; it returns `dry_run` with a human line like
`Airtable (demo mode): lead captured locally`. Errors are caught, logged, and
reported as `error` — the accept turn still succeeds. The confirm node appends
a deterministic "Front desk actions" block summarizing the three results.
No integration is ever called before explicit `accept`.

`env.example` and `docker-compose.backend.yml` gain the six new env vars,
commented out, with doc links.

## 5. State, snapshot, API contract

`ChatState`: `insurance_type` → `service_type`, `quote_step` → `intake_step`,
`quote_result` → `visit_estimate`; everything else unchanged. `main.py`
snapshot mirrors the renames (`service_type`, `intake_step`,
`has_visit_estimate`) and adds nothing else. SSE event names/payload keys
otherwise unchanged; the estimate payload key becomes `visit_estimate` wherever
`quote_result` appeared.

## 6. Knowledge base (public domain only)

Replace all 12 insurance docs in `backend/knowledge_base/` with dental docs.
Each doc ends with a `Sources:` line naming NIDCR/CDC page(s) (public domain).
**Never** ADA/MouthHealthy content.

1. `01_clinic_overview.md` — Ivory Dental Studio: hours, location, team, philosophy (synthetic clinic FAQ layer)
2. `02_routine_checkups_and_cleanings.md` — NIDCR/CDC grounded
3. `03_dental_emergencies.md` — toothache, chipped tooth, swelling, knocked-out tooth first steps
4. `04_cosmetic_dentistry.md` — whitening, veneers, aligners, bonding
5. `05_pricing_and_estimates.md` — fee schedule matching §3, insurance vs self-pay
6. `06_insurance_and_payment.md` — accepted plans, payment options, financing
7. `07_faq.md` — new-patient process, cancellation policy, parking, forms
8. `08_tooth_decay_and_cavities.md` — NIDCR/CDC grounded
9. `09_gum_disease.md` — gingivitis/periodontitis, NIDCR grounded
10. `10_children_and_family_dentistry.md` — sealants, fluoride, first visit (CDC grounded)
11. `11_oral_cancer_screening.md` — NIDCR grounded
12. `12_aftercare_scenarios.md` — post-extraction, post-whitening, sensitivity

RAG persona (rag node prompts): "Ivory, the AI front desk for Ivory Dental
Studio — warm, precise, educational; not medical advice; suggest booking when
relevant; cite the knowledge-base source."

## 7. Frontend

- Starter prompts: book a cleaning / "What should I do about a toothache?" /
  cosmetic consult / compare whitening options.
- `QuoteCard.tsx` → `VisitCard.tsx`: renders `estimate_low`–`estimate_high`
  range with the display-font figure, service badge, echoed slots; keeps ALL
  export logic (copy/download JSON, CSV) with dental field ordering.
- `App.tsx` flow chip: `"{service} intake · {step}"`; status chip
  "Collecting details" / "Estimate ready" / "Knowledge mode".
- Disclaimer: "Ivory is an AI assistant — estimates are educational, not a
  diagnosis or final price."
- `app/quote-confirmation/` route renamed/re-copied to match (visit
  confirmation).
- Layout/design system untouched (tokens, sidebar, pill composer stay).

## 8. Tests

`tests/test_backend_integration.py` converts every coverage class to dental:
health/reset; three happy paths (cleaning, emergency, cosmetic); interruption
+ exact resume; invalid numeric (`pain_level: -2`, `last_visit_year: 2031`);
invalid enum (`issue_type: laser`); invalid free text (`patient_name: "i like
dogs"` REJECTED — regression for the old location bug); adjust; restart;
service switching mid-flow; flow-start misclassification guards; bare-reply
guard (`2024`); compact multi-field input; **new:** accept → integrations
dry-run block appears; accept with monkeypatched urllib asserts Airtable/
Cal.com/Resend payloads and graceful `error` handling. Keep the LLM/vectorstore
fixture mocking pattern. Target: ≥ the current test count, all green offline.

## 9. Contract addendum (from the codebase inventory — binding)

### 9.1 Renames, exhaustively
- `insurance_type` → `service_type` (state, snapshot, SSE `session`, SESSION_STORE mirror, frontend types/readers, contract scaffold).
- `quote_step` → `intake_step` — **step VALUES stay** `identify|collect|validate|confirm`; update the three frontend literal sites together: `App.tsx` STEP_PROGRESS, `useChat.ts` synthetic snapshots, `QuoteConfirmationPage` `'confirm'` gate.
- `quote_result` → `visit_estimate`; snapshot boolean `has_quote_result` → `has_visit_estimate`; SSE `message_complete` wrapper key `quote_result` → `visit_estimate`.
- Intent value `quote` → `intake` (intents: `question|intake|response`).
- Router route `start_quote` → `start_intake`; other route names (`collect`, `answer_then_resume`, `confirm`, `identify`, `rag`) stay — tests assert them literally.
- `nodes/identify_product.py` → `nodes/identify_service.py` (`detect_product` → `detect_service`, `identify_product` → `identify_service`); `nodes/validate_quote.py` → `nodes/validate_visit.py` (note: `graph.py` lazy-imports it inside `_validate_quote_node` — update that inline import).
- Frontend: `QuoteResult` type → `VisitEstimate`; `QuoteCard.tsx` → `VisitCard.tsx`; route `app/quote-confirmation/` → `app/visit-confirmation/`; localStorage keys `ivory-latest-quote` → `ivory-latest-estimate`, `SavedChatSession.quoteResult` → `visitEstimate` (old stored history invalidates — deliberate, demo app).
- **`useChat.ts` result extraction (lines ~144–172) must change in lockstep:** wrapper keys `visit_estimate ?? visitEstimate ?? result`, top-level heuristic keys `estimate_low | estimate_high | service_type`.
- `main.py` app title → `"Ivory Dental Front Desk"`; `/debug` retrieval probe query → `"what dental services do you offer"`.

### 9.2 Must-preserve seams (tests monkeypatch these — keep names/signatures verbatim)
- `nodes.rag._build_client_or_none`, `nodes.rag.search_knowledge_base` (imported *by name* into the rag module namespace).
- `services.vectorstore.RetrievedChunk(id, score, source, title, content, metadata)`.
- LLM client: `.chat_text(system_prompt=, user_prompt=, history=, on_token=)` + `.model`.
- `main.SESSION_STORE` (dict keyed by session_id; mirror keys `mode, intake_step, current_field, service_type, collected_data, visit_estimate`).
- `graph.get_session_state`, `graph.COMPILED_GRAPH`, `graph._build_graph`, `graph._checkpointer` (state survives recompile against same checkpointer).
- `nodes.router.decide(state, message)` stays pure/deterministic, no LLM.
- `RATE_LIMIT_ENABLED` read at request time. Endpoints `/health`, `/reset`, `/chat` and SSE event names `token`/`message_complete`/`error`; first event `token`, last `message_complete`.
- Invalid-input contract: `"{error} {same field prompt}"`, `current_field` unchanged, field absent from `collected_data`, `intake_step` stays `collect`.
- Graph topology unchanged: START→router →(cond)→ {rag_answer, identify_service, collect_details, confirm}; identify_service→{collect_details|END}; collect_details→{validate_visit|END}; validate_visit→END; confirm→{collect_details|END}; rag_answer→END. `_reset_intake_progress` keeps `mode="transactional"`.

### 9.3 Load-bearing copy (single source of truth; graph.py duplicates the menu — keep both sites identical)
- Service menu (identify + interrupt-at-identify resume): `Which type of visit would you like to set up: a cleaning, an emergency visit, or a cosmetic consultation?`
- Resume template (interrupt mid-collect): `\n\nNow, back to your {service_label} intake — {field_prompt}` with labels cleaning→`cleaning visit`, emergency→`emergency visit`, cosmetic→`cosmetic consultation`.
- First-field prompts (asserted literally by tests):
  - all services, `patient_name`: `What's the patient's full name? (e.g. Maria Santos)`
  - cleaning `contact_email`: `What email should we use for confirmations? (e.g. maria@example.com)`
  - cleaning `last_visit_year`: `What year was your last dental visit? (e.g. 2024)`
  - cleaning `insurance_status`: `Do you have dental insurance, or are you paying out of pocket? (insured or self-pay)` (parser maps self-pay/self pay/cash/out of pocket → `self_pay`)
  - cleaning `preferred_time`: `What time of day works best: morning, afternoon, or evening?`
  - emergency `contact_phone`: `What phone number can we reach you at? (e.g. 555-201-7788)`
  - emergency `issue_type`: `What's the problem: a toothache, chipped tooth, swelling, or a lost filling?`
  - emergency `pain_level`: `On a scale of 0 to 10, how bad is the pain right now?`
  - cosmetic `treatment`: `Which treatment are you interested in: whitening, veneers, aligners, or bonding?`
  - cosmetic `budget_band`: `Which budget band fits best: basic, standard, or premium?`
  - cosmetic `timeline`: `When would you like to start: asap, this month, or flexible?`
- Estimate copy in the confirm message must contain `estimated` + the service label + a `$low–$high` range.
- Front-desk block on accept (deterministic, three lines, in this order): header `Front desk actions:` then `- Airtable CRM: …` / `- Cal.com booking: …` / `- Email confirmation: …` (each line's tail from `IntegrationResult.detail`).
- Service detection aliases: cleaning ⊇ {cleaning, checkup, check-up, check up, exam, hygiene}; emergency ⊇ {emergency, urgent, broken tooth, chipped}; cosmetic ⊇ {cosmetic, whitening, veneers, aligners, smile makeover}.
- Free-text guard (`_clean_text_value` dental redesign): keep filler-prefix (`i `, `my `, `we `, `they `), like/love, `?`-suffix, >6-token rejections; domain-keyword blocklist becomes dental (`appointment, booking, estimate, cleaning, whitening, dentist, dental, tooth, teeth, cost, price`); denylist (zoo/dog/dogs class) retained for names. `"i like dogs"` as `patient_name` must be rejected.

### 9.4 front_desk interface (fixed; backend-core creates placeholder, integrations agent finalizes)
```python
# backend/services/front_desk.py
@dataclass(frozen=True)
class IntegrationResult:
    name: str      # "Airtable CRM" | "Cal.com booking" | "Email confirmation"
    status: str    # created | booked | sent | dry_run | skipped | error
    detail: str    # one human sentence, shown verbatim in chat

def process_accept(service_type: str, collected: dict[str, Any], estimate: dict[str, Any]) -> list[IntegrationResult]
```
Called from `confirm.py` accept branch only. Placeholder returns three `dry_run` results so backend-core is self-contained before the integrations agent lands.

### 9.5 Frontend extras (from audit)
- Add the same session-cookie validation used by `/api/auth/check` to the `/api/chat` and `/api/reset` proxy routes (dental intake carries PII).
- Wire or remove the dead `Talk to an Agent` button on the confirmation page (becomes `Call the clinic`, `tel:` link, or removed).
- History-save gate (persist only when an estimate exists) keeps its semantics against `visitEstimate`.

## 10. Execution order (agent partition)

1. **backend-core** (one agent, owns): `state.py`, `graph.py`, `main.py`, `nodes/*`, `services/visit_estimator.py` (rename), deletes insurance calculator.
2. In parallel after core: **corpus** (owns `backend/knowledge_base/*`, `rebuild_knowledge_base.py` touchpoints), **integrations** (owns `services/airtable.py`, `calcom.py`, `resend_email.py`, `front_desk.py`, `env.example`, `docker-compose.backend.yml`, plus the confirm-node accept hook — coordinate: core leaves a clearly-marked hook point), **frontend** (owns `frontend/src/*`, `frontend/app/*`), **tests** (owns `tests/*`).
3. **docs** last, then full verification.
