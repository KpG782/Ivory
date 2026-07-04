# Ivory Purpose And Flow

## What this project is

Ivory is a hybrid dental front-desk assistant.

It is not just a chatbot and it is not just an appointment form.

Its purpose is to combine:

- conversational dental Q&A
- structured visit intake collection
- clean switching between those two modes

That is the main point of the project (see `docs/specs/DENTAL_VERTICAL_SPEC.md`): prove that one assistant can answer dental questions and also run a guided transactional workflow without losing state.

## Why this exists

The use case is simple:

- a patient wants to learn about dental care and the clinic
- the same patient may decide to set up a visit
- while setting up that visit, the patient may interrupt with dental questions
- the assistant should answer the question and then continue the intake flow

So the product value is:

- fewer drop-offs than a rigid intake form
- better patient guidance than a static FAQ page
- one continuous experience instead of separate support and booking tools

## When someone would use this

Typical cases:

- `What dental services do you offer?`
- `What does a routine cleaning include?`
- `I'd like to book a cleaning.`
- `I started booking, but I need to ask something before I continue.`

The whole project is meant for a patient who is still deciding, still learning, or partially ready to book.

## Core product idea

This project has two modes.

### 1. Conversational mode

The assistant answers dental questions using the knowledge base.

Examples:

- what happens during a checkup
- emergency first steps (toothache, chipped tooth, swelling)
- cosmetic treatment options
- pricing, insurance, and payment questions
- clinic FAQs (hours, parking, cancellation policy)

### 2. Transactional mode

The assistant guides the user through visit intake.

Examples:

- identify the service (cleaning, emergency, cosmetic)
- collect required details
- validate inputs
- generate a visit estimate
- let the user confirm, adjust, or restart

## Why the state machine matters

This project uses a state-machine style backend because normal chat is not enough for intake.

An intake flow needs memory of:

- what service the patient chose
- what fields are already collected
- what field is missing next
- whether the patient is confirming or adjusting

Without state, the assistant would lose context too easily and the intake flow would feel unreliable.

## Frontend flow

The frontend is intentionally simple now.

### Main dashboard: `/`

This is the main working page.

The user can:

- ask dental questions
- start an intake
- continue answering intake questions
- reset the session
- see the current backend state
- see the current visit estimate

The dashboard is the primary workspace.

### What the user sees on the dashboard

There are three practical parts:

1. The main chat area
   This is where the conversation happens.

2. The state chips in the header
   These show:
   - the flow chip: service and step (e.g. `cleaning intake · collect`)
   - the status chip: `Knowledge mode`, `Collecting details`, or `Estimate ready`
   - a progress bar for the intake steps

3. The visit card
   This shows the generated estimate range and collected details when available.

### Confirmation page: `/visit-confirmation`

This page is only for the final confirmation stage.

It should only be used when the backend says the session is ready for confirmation.

That means:

- `mode = transactional`
- `intake_step = confirm`
- a real `visit_estimate` exists

On this page, the user can:

- accept and book the visit
- adjust the details
- call the clinic instead

## Backend flow

The backend is the source of truth.

It decides:

- whether the user is in conversational or transactional mode
- what the current intake step is
- what field is missing
- whether an estimate is ready
- whether the session is in confirmation state

The frontend should not invent this state on its own.

### Current backend endpoints

- `GET /health`
- `POST /chat`
- `POST /reset`

### Current backend session behavior

Each chat session tracks structured state, including:

- `mode`
- `intent`
- `intake_step`
- `service_type`
- `current_field`
- `visit_estimate`

That is what keeps the chat and intake flow consistent across the UI.

## Typical user journey

### Journey A: question only

1. User opens the dashboard.
2. User asks a dental question.
3. Backend routes to the knowledge path.
4. Assistant answers using retrieved knowledge base content.

### Journey B: intake flow

1. User says they want to book a visit.
2. Backend switches into transactional mode.
3. Assistant asks for required fields.
4. User answers step by step.
5. Backend validates the data.
6. Backend generates a visit estimate.
7. User reviews and accepts or adjusts.
8. On accept, the front-desk actions run (CRM lead, booking request, confirmation email — dry-run without keys).

### Journey C: mid-flow interruption

1. User starts an intake.
2. Assistant is collecting intake details.
3. User interrupts with a dental question.
4. Backend answers the question.
5. Backend preserves collected intake data.
6. Assistant resumes the intake flow.

That third journey is one of the most important reasons this project is worth using.

## Why use this instead of a normal form

A normal intake form is faster to build, but worse at handling uncertainty.

This assistant is useful because it can:

- educate while collecting intake data
- reduce friction when the patient is unsure
- recover cleanly from interruptions
- keep one conversation instead of forcing the user through separate pages and tools

So the value is not just “chat UI”.

The value is:

- guided decision support
- structured intake handling
- context preservation

## About adding more knowledge base content

Yes, adding more knowledge base content can help, but only if it is targeted.

### When more knowledge base content helps

It helps when you add information that improves real patient questions, such as:

- what specific treatments involve
- aftercare guidance
- emergency first steps
- insurance and payment rules
- clinic policies (cancellation, forms, parking)
- children's dentistry guidance
- prevention advice

This makes conversational mode more useful and makes the demo feel more complete.

### When more knowledge base content does not help much

It does not help much if you add a lot of repetitive or low-signal text.

Examples:

- multiple chunks saying the same thing
- marketing copy without factual value
- content unrelated to the actual user prompts
- large clinical text that the assistant never needs
- anything not grounded in public-domain sources (the corpus is NIDCR/CDC grounded — never ADA content)

Too much noisy content can weaken retrieval quality.

## Best knowledge base strategy for this project

The best approach is:

- keep the knowledge base compact
- cover the most likely patient questions well
- organize content by service and health topic
- avoid duplicate chunks
- prefer short, clear, factual documents over long vague ones
- end every document with a `Sources:` line

Good categories to expand next:

- root canals and crowns
- wisdom teeth
- dry mouth and medication side effects
- pregnancy and oral health
- dental X-ray safety

## Short version

This project is useful because it combines:

- dental Q&A
- guided visit estimation
- stateful interruption handling

The frontend gives the user one main dashboard to work through that flow.
The backend keeps the flow consistent.
The knowledge base supports grounded answers.

If you expand the knowledge base, do it to improve answer quality for likely patient questions, not just to make the repo look bigger.
